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

set(ARM_CPU "cortex-m0plus")
set(ROOT ${CMAKE_CURRENT_LIST_DIR}/lib/CMSIS_5)
set(DSP ${ROOT}/CMSIS/DSP)

set(CONFIGTABLE ON)
set(RFFT_Q15_256 ON)
set(ALLFAST ON)

# # include CMSIS-DSP .cmake for GCC Toolchain
# include(${DSP}/Toolchain/GCC.cmake)
# # add CMSIS-DSP Source directory as subdirectory
# add_subdirectory(${DSP}/Source EXCLUDE_FROM_ALL)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

add_subdirectory(FatFs_SPI build)

# Add executable. Default name is the project name, version 0.1
add_executable(ML-head-transfer-functions
    hw_config.c
)

target_sources(ML-head-transfer-functions PRIVATE ML-head-transfer-functions.c)

# Add the standard library to the build
target_link_libraries(ML-head-transfer-functions
    pico_stdlib
    pico_bootsel_via_double_reset
    pico_stdio
    pico_stdio_uart
    pico_multicore
    hardware_spi
    hardware_sync
    hardware_adc
    hardware_timer
    hardware_pio
    no-OS-FatFS-SD-SDIO-SPI-RPi-Pico
)

# # Add the standard include files to the build
# target_include_directories(ML-head-transfer-functions PRIVATE
#         ${CMAKE_CURRENT_LIST_DIR}
# )

pico_enable_stdio_usb(ML-head-transfer-functions 1)
pico_enable_stdio_uart(ML-head-transfer-functions 0)

pico_add_extra_outputs(ML-head-transfer-functions)

