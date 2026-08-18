#include "archive_commands.h"
#include <archive.h>
#include <archive_entry.h>
#include <cstring>
#include <cstdio>
#include <sstream>
#include <sys/stat.h>

#ifndef _WIN32
#include <dirent.h>
#include <unistd.h>
#else
#include <windows.h>
#include <io.h>
#endif

static std::string g_passphrase;

void archive_set_passphrase(const std::string& passphrase) {
    g_passphrase = passphrase;
}

std::string u16_to_utf8(const PA_Unichar* src, PA_long32 len) {
    std::string result;
    result.reserve(len);
    for (PA_long32 i = 0; i < len; i++) {
        unsigned int c = (unsigned int)src[i];
        if (c >= 0xD800 && c <= 0xDBFF && i + 1 < len) {
            unsigned int lo = (unsigned int)src[i + 1];
            if (lo >= 0xDC00 && lo <= 0xDFFF) {
                c = 0x10000 + ((c - 0xD800) << 10) + (lo - 0xDC00);
                i++;
            }
        }
        if (c < 0x80) {
            result += (char)c;
        } else if (c < 0x800) {
            result += (char)(0xC0 | (c >> 6));
            result += (char)(0x80 | (c & 0x3F));
        } else if (c < 0x10000) {
            result += (char)(0xE0 | (c >> 12));
            result += (char)(0x80 | ((c >> 6) & 0x3F));
            result += (char)(0x80 | (c & 0x3F));
        } else {
            result += (char)(0xF0 | (c >> 18));
            result += (char)(0x80 | ((c >> 12) & 0x3F));
            result += (char)(0x80 | ((c >> 6) & 0x3F));
            result += (char)(0x80 | (c & 0x3F));
        }
    }
    return result;
}

std::vector<PA_Unichar> utf8_to_u16(const std::string& src) {
    std::vector<PA_Unichar> result;
    result.reserve(src.size());
    const unsigned char* p = (const unsigned char*)src.c_str();
    const unsigned char* end = p + src.size();
    while (p < end) {
        unsigned int c;
        if (*p < 0x80) { c = *p++; }
        else if ((*p & 0xE0) == 0xC0) { c = (*p++ & 0x1F) << 6; c |= (*p++ & 0x3F); }
        else if ((*p & 0xF0) == 0xE0) { c = (*p++ & 0x0F) << 12; c |= (*p++ & 0x3F) << 6; c |= (*p++ & 0x3F); }
        else { c = (*p++ & 0x07) << 18; c |= (*p++ & 0x3F) << 12; c |= (*p++ & 0x3F) << 6; c |= (*p++ & 0x3F); }
        if (c < 0x10000) {
            result.push_back((PA_Unichar)c);
        } else {
            c -= 0x10000;
            result.push_back((PA_Unichar)(0xD800 + (c >> 10)));
            result.push_back((PA_Unichar)(0xDC00 + (c & 0x3FF)));
        }
    }
    result.push_back(0);
    return result;
}

static std::string escape_json_string(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 2);
    out += '"';
    for (char c : s) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default: out += c;
        }
    }
    out += '"';
    return out;
}

int archive_create(const char* source, const char* dest, int format, int filter) {
    struct archive *a = archive_write_new();
    if (!a) return -1;

    switch (format) {
        case 1: archive_write_set_format_pax_restricted(a); break;
        case 2: archive_write_set_format_zip(a); break;
        case 3: archive_write_set_format_7zip(a); break;
        case 4: archive_write_set_format_cpio_newc(a); break;
        default: archive_write_set_format_pax_restricted(a); break;
    }

    switch (filter) {
        case 0: archive_write_add_filter_none(a); break;
        case 1: archive_write_add_filter_gzip(a); break;
        case 2: archive_write_add_filter_bzip2(a); break;
        case 3: archive_write_add_filter_xz(a); break;
        case 4: archive_write_add_filter_zstd(a); break;
        case 5: archive_write_add_filter_lz4(a); break;
        default: archive_write_add_filter_none(a); break;
    }

    if (!g_passphrase.empty()) {
        archive_write_set_passphrase(a, g_passphrase.c_str());
        g_passphrase.clear();
    }

    int r = archive_write_open_filename(a, dest);
    if (r != ARCHIVE_OK) {
        archive_write_free(a);
        return -1;
    }

    struct archive *disk = archive_read_disk_new();
    archive_read_disk_set_standard_lookup(disk);
    r = archive_read_disk_open(disk, source);
    if (r != ARCHIVE_OK) {
        archive_read_free(disk);
        archive_write_free(a);
        return -1;
    }

    // Compute base path for relative entries
    std::string basePath(source);
    // Find parent directory
    size_t lastSlash = basePath.rfind('/');
    std::string parentDir;
    if (lastSlash != std::string::npos) {
        parentDir = basePath.substr(0, lastSlash + 1);
    }

    struct archive_entry *entry = archive_entry_new();
    while (archive_read_next_header2(disk, entry) == ARCHIVE_OK) {
        archive_read_disk_descend(disk);

        const char* currentPath = archive_entry_pathname(entry);
        std::string relPath(currentPath);
        if (!parentDir.empty() && relPath.find(parentDir) == 0) {
            relPath = relPath.substr(parentDir.size());
        }
        archive_entry_set_pathname(entry, relPath.c_str());

        archive_write_header(a, entry);

        if (archive_entry_size(entry) > 0 && archive_entry_filetype(entry) == AE_IFREG) {
            FILE* f = fopen(currentPath, "rb");
            if (f) {
                char buf[8192];
                size_t bytesRead;
                while ((bytesRead = fread(buf, 1, sizeof(buf), f)) > 0) {
                    archive_write_data(a, buf, bytesRead);
                }
                fclose(f);
            }
        }
        archive_entry_clear(entry);
    }

    archive_entry_free(entry);
    archive_read_free(disk);
    archive_write_close(a);
    archive_write_free(a);
    return 0;
}

int archive_extract(const char* archivePath, const char* destPath) {
    struct archive *a = archive_read_new();
    archive_read_support_format_all(a);
    archive_read_support_filter_all(a);

    if (!g_passphrase.empty()) {
        archive_read_add_passphrase(a, g_passphrase.c_str());
        g_passphrase.clear();
    }

    int r = archive_read_open_filename(a, archivePath, 10240);
    if (r != ARCHIVE_OK) {
        archive_read_free(a);
        return -1;
    }

    struct archive *ext = archive_write_disk_new();
    archive_write_disk_set_options(ext, ARCHIVE_EXTRACT_TIME | ARCHIVE_EXTRACT_PERM);
    archive_write_disk_set_standard_lookup(ext);

    struct archive_entry *entry;
    while (archive_read_next_header(a, &entry) == ARCHIVE_OK) {
        std::string fullPath = std::string(destPath) + "/" + archive_entry_pathname(entry);
        archive_entry_set_pathname(entry, fullPath.c_str());

        r = archive_write_header(ext, entry);
        if (r == ARCHIVE_OK) {
            const void *buff;
            size_t size;
            la_int64_t offset;
            while (archive_read_data_block(a, &buff, &size, &offset) == ARCHIVE_OK) {
                archive_write_data_block(ext, buff, size, offset);
            }
        }
        archive_write_finish_entry(ext);
    }

    archive_read_free(a);
    archive_write_free(ext);
    return 0;
}

std::string archive_list(const char* archivePath) {
    struct archive *a = archive_read_new();
    archive_read_support_format_all(a);
    archive_read_support_filter_all(a);

    if (!g_passphrase.empty()) {
        archive_read_add_passphrase(a, g_passphrase.c_str());
        g_passphrase.clear();
    }

    int r = archive_read_open_filename(a, archivePath, 10240);
    if (r != ARCHIVE_OK) {
        archive_read_free(a);
        return "[]";
    }

    std::string json = "[";
    bool first = true;
    struct archive_entry *entry;

    while (archive_read_next_header(a, &entry) == ARCHIVE_OK) {
        if (!first) json += ",";
        first = false;

        json += "{";
        json += "\"path\":" + escape_json_string(archive_entry_pathname(entry));

        json += ",\"size\":";
        char sizeBuf[32];
        snprintf(sizeBuf, sizeof(sizeBuf), "%lld", (long long)archive_entry_size(entry));
        json += sizeBuf;

        json += ",\"type\":";
        int ft = archive_entry_filetype(entry);
        if (ft == AE_IFDIR) json += "\"directory\"";
        else if (ft == AE_IFLNK) json += "\"symlink\"";
        else json += "\"file\"";

        json += ",\"mtime\":";
        time_t mtime = archive_entry_mtime(entry);
        struct tm tm_buf;
#ifdef _WIN32
        gmtime_s(&tm_buf, &mtime);
#else
        gmtime_r(&mtime, &tm_buf);
#endif
        char timeBuf[64];
        strftime(timeBuf, sizeof(timeBuf), "%Y-%m-%dT%H:%M:%SZ", &tm_buf);
        json += "\"";
        json += timeBuf;
        json += "\"";

        json += "}";

        archive_read_data_skip(a);
    }

    json += "]";
    archive_read_free(a);
    return json;
}
