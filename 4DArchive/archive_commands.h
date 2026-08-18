#ifndef ARCHIVE_COMMANDS_H
#define ARCHIVE_COMMANDS_H

#include <string>
#include <vector>
#include "4DPluginAPI.h"

int archive_create(const char* source, const char* dest, int format, int filter);
int archive_extract(const char* archivePath, const char* destPath);
std::string archive_list(const char* archivePath);
void archive_set_passphrase(const std::string& passphrase);

std::string u16_to_utf8(const PA_Unichar* src, PA_long32 len);
std::vector<PA_Unichar> utf8_to_u16(const std::string& src);

#endif
