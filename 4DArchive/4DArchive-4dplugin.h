#ifndef FOURDA_ARCHIVE_4DPLUGIN_H
#define FOURDA_ARCHIVE_4DPLUGIN_H

#include "4DPluginAPI.h"
#include <string>

void PluginMain(PA_long32 selector, PA_PluginParameters params);

static void cmd_archive_create(PA_PluginParameters params);
static void cmd_archive_extract(PA_PluginParameters params);
static void cmd_archive_list(PA_PluginParameters params);
static void cmd_archive_set_passphrase(PA_PluginParameters params);

#endif
