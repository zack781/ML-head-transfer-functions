# Generated Cmake Pico project file

cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

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

project(audio-ml C CXX ASM)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

# Define ARM_CPU, CMSIS ROOT and DSP to use CMSIS-DSP
set(ARM_CPU "cortex-m0plus")
set(ROOT ${CMAKE_CURRENT_LIST_DIR}/lib/CMSIS_5)
set(DSP ${ROOT}/CMSIS/DSP)

set(CONFIGTABLE ON)
set(RFFT_Q15_256 ON)
set(ALLFAST ON)

# include CMSIS-DSP .cmake for GCC Toolchain
include(${DSP}/Toolchain/GCC.cmake)

add_subdirectory(${DSP}/Source EXCLUDE_FROM_ALL)
# add_subdirectory(FatFs_SPI build)

add_subdirectory(FatFs_SPI EXCLUDE_FROM_ALL)

# Add executable. Default name is the project name, version 0.1

# add_executable(audio-ml audio-ml.cpp )

add_executable(audio-ml
    ${CMAKE_CURRENT_LIST_DIR}/src/audio-ml.cpp
    ${CMAKE_CURRENT_LIST_DIR}/src/dsp_pipeline.cpp
    ${CMAKE_CURRENT_LIST_DIR}/src/ml_model.cpp
    ${CMAKE_CURRENT_LIST_DIR}/hw_config.c
)

pico_set_program_name(audio-ml "audio-ml")
pico_set_program_version(audio-ml "0.1")

# Modify the below lines to enable/disable output over UART/USB
pico_enable_stdio_uart(audio-ml 1)
pico_enable_stdio_usb(audio-ml 1)

# Add the standard library to the build
target_link_libraries(audio-ml
    hardware_pwm
    pico-tflmicro
    pico_multicore
    pico_stdlib
    pico_bootsel_via_double_reset
    pico_stdio 
    pico_stdio_uart
    hardware_spi
    hardware_sync
    hardware_adc
    hardware_timer
    no-OS-FatFS-SD-SDIO-SPI-RPi-Pico 
    CMSISDSPTransform CMSISDSPSupport CMSISDSPCommon CMSISDSPComplexMath CMSISDSPFastMath CMSISDSPBasicMath
)

# Add the standard include files to the build
target_include_directories(audio-ml PUBLIC
        ${CMAKE_CURRENT_LIST_DIR}
        ${CMAKE_CURRENT_LIST_DIR}/FatFs_SPI/include
        ${CMAKE_CURRENT_LIST_DIR}/FatFs_SPI/sd_driver
        ${CMAKE_CURRENT_LIST_DIR}/FatFs_SPI/ff15/source
)

pico_add_extra_outputs(audio-ml)

# add_subdirectory("lib/microphone-library-for-pico" EXCLUDE_FROM_ALL)
add_subdirectory("lib/pico-tflmicro" EXCLUDE_FROM_ALL)