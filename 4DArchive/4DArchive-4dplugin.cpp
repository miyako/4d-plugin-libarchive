#include "4DArchive-4dplugin.h"
#include "archive_commands.h"

void PluginMain(PA_long32 selector, PA_PluginParameters params) {
    switch (selector) {
        case 1:
            cmd_archive_create(params);
            break;
        case 2:
            cmd_archive_extract(params);
            break;
        case 3:
            cmd_archive_list(params);
            break;
        case 4:
            cmd_archive_set_passphrase(params);
            break;
    }
}

static void cmd_archive_create(PA_PluginParameters params) {
    PA_Unistring *uSource = PA_GetStringParameter(params, 1);
    PA_Unistring *uArchive = PA_GetStringParameter(params, 2);
    PA_long32 format = PA_GetLongParameter(params, 3);
    PA_long32 filter = PA_GetLongParameter(params, 4);

    std::string source = u16_to_utf8(PA_GetUnistring(uSource), PA_GetUnistringLength(uSource));
    std::string archive = u16_to_utf8(PA_GetUnistring(uArchive), PA_GetUnistringLength(uArchive));

    int result = archive_create(source.c_str(), archive.c_str(), (int)format, (int)filter);
    PA_ReturnLong(params, (PA_long32)result);
}

static void cmd_archive_extract(PA_PluginParameters params) {
    PA_Unistring *uArchive = PA_GetStringParameter(params, 1);
    PA_Unistring *uDest = PA_GetStringParameter(params, 2);

    std::string archive = u16_to_utf8(PA_GetUnistring(uArchive), PA_GetUnistringLength(uArchive));
    std::string dest = u16_to_utf8(PA_GetUnistring(uDest), PA_GetUnistringLength(uDest));

    int result = archive_extract(archive.c_str(), dest.c_str());
    PA_ReturnLong(params, (PA_long32)result);
}

static void cmd_archive_list(PA_PluginParameters params) {
    PA_Unistring *uArchive = PA_GetStringParameter(params, 1);

    std::string archive = u16_to_utf8(PA_GetUnistring(uArchive), PA_GetUnistringLength(uArchive));

    std::string json = archive_list(archive.c_str());

    std::vector<PA_Unichar> u16 = utf8_to_u16(json);
    PA_ReturnString(params, u16.data());
}

static void cmd_archive_set_passphrase(PA_PluginParameters params) {
    PA_Unistring *uPass = PA_GetStringParameter(params, 1);

    std::string pass = u16_to_utf8(PA_GetUnistring(uPass), PA_GetUnistringLength(uPass));
    archive_set_passphrase(pass);
}
