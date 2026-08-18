cmake_minimum_required(VERSION 3.20)

# Set the plugin name
set(PLUGIN_NAME "4DArchive" CACHE STRING "Plugin name")

project(${PLUGIN_NAME} LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_C_STANDARD 17)

# --- SDK paths ---
set(SDK_DIR "${CMAKE_SOURCE_DIR}/../4D-Plugin-SDK/4D Plugin API")

# --- libarchive paths ---
set(LIBARCHIVE_DIR "${CMAKE_SOURCE_DIR}/../deps/libarchive")

# --- Static CRT on Windows (MUST be set before add_subdirectory) ---
if(WIN32)
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>" CACHE STRING "" FORCE)
endif()

# --- libarchive build options ---
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(ENABLE_TAR OFF CACHE BOOL "" FORCE)
set(ENABLE_CPIO OFF CACHE BOOL "" FORCE)
set(ENABLE_CAT OFF CACHE BOOL "" FORCE)
set(ENABLE_UNZIP OFF CACHE BOOL "" FORCE)
set(ENABLE_TEST OFF CACHE BOOL "" FORCE)
set(ENABLE_INSTALL OFF CACHE BOOL "" FORCE)

set(ENABLE_OPENSSL OFF CACHE BOOL "" FORCE)
set(ENABLE_LZMA OFF CACHE BOOL "" FORCE)
set(ENABLE_LZ4 OFF CACHE BOOL "" FORCE)
set(ENABLE_ZSTD OFF CACHE BOOL "" FORCE)
set(ENABLE_LIBB2 OFF CACHE BOOL "" FORCE)
set(ENABLE_LIBXML2 OFF CACHE BOOL "" FORCE)
set(ENABLE_EXPAT OFF CACHE BOOL "" FORCE)
set(ENABLE_LZO OFF CACHE BOOL "" FORCE)
set(ENABLE_ICONV OFF CACHE BOOL "" FORCE)
set(ENABLE_ACL OFF CACHE BOOL "" FORCE)
set(ENABLE_XATTR OFF CACHE BOOL "" FORCE)

set(ENABLE_ZLIB ON CACHE BOOL "" FORCE)
set(ENABLE_BZip2 ON CACHE BOOL "" FORCE)
set(ENABLE_CNG ON CACHE BOOL "" FORCE)

add_subdirectory("${LIBARCHIVE_DIR}" "${CMAKE_BINARY_DIR}/libarchive")

# --- Source files ---
set(PLUGIN_SOURCES
    ${PLUGIN_NAME}-4dplugin.cpp
    archive_commands.cpp
    "${SDK_DIR}/4DPluginAPI.c"
)

set(PLUGIN_HEADERS
    ${PLUGIN_NAME}-4dplugin.h
    archive_commands.h
    "${SDK_DIR}/4DPluginAPI.h"
    "${SDK_DIR}/EntryPoints.h"
    "${SDK_DIR}/PublicTypes.h"
    "${SDK_DIR}/PrivateTypes.h"
    "${SDK_DIR}/Flags.h"
)

set(PLUGIN_RESOURCES
    manifest.json
    constants.xlf
)

# --- Platform-specific target setup ---
if(APPLE)
    add_library(${PLUGIN_NAME} MODULE ${PLUGIN_SOURCES} ${PLUGIN_HEADERS} ${PLUGIN_RESOURCES})

    set_target_properties(${PLUGIN_NAME} PROPERTIES
        BUNDLE TRUE
        BUNDLE_EXTENSION "bundle"
        MACOSX_BUNDLE_INFO_PLIST "${CMAKE_SOURCE_DIR}/Info.plist.in"
        MACOSX_BUNDLE_GUI_IDENTIFIER "com.4d.${PLUGIN_NAME}"
        MACOSX_BUNDLE_BUNDLE_VERSION "1.0"
        MACOSX_BUNDLE_SHORT_VERSION_STRING "1.0"
    )

    set_source_files_properties(${PLUGIN_RESOURCES} PROPERTIES
        MACOSX_PACKAGE_LOCATION Resources
    )

    find_library(COREGRAPHICS_FRAMEWORK CoreGraphics REQUIRED)
    target_link_libraries(${PLUGIN_NAME} PRIVATE ${COREGRAPHICS_FRAMEWORK})

    set_target_properties(${PLUGIN_NAME} PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/${PLUGIN_NAME}-test/Plugins"
        LIBRARY_OUTPUT_DIRECTORY_DEBUG "${CMAKE_SOURCE_DIR}/${PLUGIN_NAME}-test/Plugins"
        LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/${PLUGIN_NAME}-test/Plugins"
    )

elseif(WIN32)
    add_library(${PLUGIN_NAME} SHARED ${PLUGIN_SOURCES} ${PLUGIN_HEADERS})

    set_target_properties(${PLUGIN_NAME} PROPERTIES
        SUFFIX ".4DX"
        LINK_FLAGS "/DEF:\"${SDK_DIR}/4DPluginAPI.def\""
    )

    set_property(TARGET ${PLUGIN_NAME} PROPERTY
        MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>"
    )

    target_compile_definitions(${PLUGIN_NAME} PRIVATE LIBARCHIVE_STATIC)

    set(PLUGIN_OUT_DIR "${CMAKE_SOURCE_DIR}/${PLUGIN_NAME}-test/Plugins/${PLUGIN_NAME}/Contents/Windows64")
    set(RESOURCE_OUT_DIR "${CMAKE_SOURCE_DIR}/${PLUGIN_NAME}-test/Plugins/${PLUGIN_NAME}/Contents/Resources")

    set_target_properties(${PLUGIN_NAME} PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${PLUGIN_OUT_DIR}"
        RUNTIME_OUTPUT_DIRECTORY_DEBUG "${PLUGIN_OUT_DIR}"
        RUNTIME_OUTPUT_DIRECTORY_RELEASE "${PLUGIN_OUT_DIR}"
    )

    add_custom_command(TARGET ${PLUGIN_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory "${RESOURCE_OUT_DIR}"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${CMAKE_SOURCE_DIR}/manifest.json"
            "${CMAKE_SOURCE_DIR}/constants.xlf"
            "${RESOURCE_OUT_DIR}"
        COMMENT "Copying manifest.json and constants.xlf to Resources"
    )
endif()

# --- Common settings ---
target_include_directories(${PLUGIN_NAME} PRIVATE
    "${SDK_DIR}"
    "${LIBARCHIVE_DIR}/libarchive"
    "${CMAKE_BINARY_DIR}/libarchive/libarchive"
)

# Compile 4DPluginAPI.c as C++
set_source_files_properties("${SDK_DIR}/4DPluginAPI.c" PROPERTIES LANGUAGE CXX)

# Unicode charset
target_compile_definitions(${PLUGIN_NAME} PRIVATE UNICODE _UNICODE)

# Link libarchive static
target_link_libraries(${PLUGIN_NAME} PRIVATE archive_static)
