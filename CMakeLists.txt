# Generated Cmake Pico project file

cmake_minimum_required(VERSION 3.13)

# set(CMAKE_C_STANDARD 11)
# set(CMAKE_CXX_STANDARD 17)
# set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Initialise pico_sdk from installed location
# (note this can come from environment, CMake cache etc)

# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.2.0-a4)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================
set(PICO_BOARD pico CACHE STRING "Board type")

# Pull in Raspberry Pi Pico SDK (must be before project)
include(pico_sdk_import.cmake)

project(ML-head-transfer-functions C CXX ASM)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

# Add executable. Default name is the project name, version 0.1

add_executable(ML-head-transfer-functions)
target_sources(ML-head-transfer-functions PRIVATE ML-head-transfer-functions.c)

# Add the standard library to the build
target_link_libraries(ML-head-transfer-functions pico_stdlib pico_bootsel_via_double_reset hardware_spi hardware_sync hardware_adc hardware_timer)

# # Add the standard include files to the build
# target_include_directories(ML-head-transfer-functions PRIVATE
#         ${CMAKE_CURRENT_LIST_DIR}
# )

pico_add_extra_outputs(ML-head-transfer-functions)

