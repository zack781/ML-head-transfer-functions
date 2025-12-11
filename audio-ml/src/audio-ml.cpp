#include <stdio.h>
#include "pico/stdlib.h"

#include "tflite_model.h"

#include "dsp_pipeline.h"
#include "ml_model.h"

#include "pico/multicore.h"

#include "hardware/spi.h"
#include "hardware/adc.h"
#include "hardware/sync.h"
#include "hardware/clocks.h"

#include "sd_card.h"
#include "ff.h"

#define SAMPLE_RATE       44100
#define FFT_SIZE          256
#define SPECTRUM_SHIFT    4
#define INPUT_BUFFER_SIZE ((FFT_SIZE / 2) * SPECTRUM_SHIFT)
#define INPUT_SHIFT       0

DSPPipeline dsp_pipeline(FFT_SIZE);
MLModel ml_model(tflite_model, 128 * 1024);

int8_t* scaled_spectrum = nullptr;
int32_t spectogram_divider;
float spectrogram_zero_point;

FRESULT fr;
FATFS fs;        // File system object

FRESULT pb_fr;
FIL fil_pb;
UINT pb_bw;
// bool file_read = false;
char pb_filename[1000];

#define BYTES_TO_READ 50000
#define BUFFER_SIZE 50000
volatile int16_t sample_buffer[BUFFER_SIZE];
volatile int pb_write = 0;

q15_t input_q15[INPUT_BUFFER_SIZE + (FFT_SIZE / 2)];
volatile bool data_ready = false; 
volatile int current_read_index = 0;
q15_t capture_buffer_q15[INPUT_BUFFER_SIZE];


#define ALARM_NUM 0
#define ALARM_IRQ TIMER_IRQ_0
#define DELAY 22.68 // 1/Fs (in microseconds)
volatile uint16_t buffer_index = 0;


static void alarm_irq(void)
{
    hw_clear_bits(&timer_hw->intr, 1u << ALARM_NUM);

    // Reset the alarm register
    timer_hw->alarm[ALARM_NUM] = timer_hw->timerawl + DELAY ;

    // sample = adc_read();
    // sample_buffer[buffer_index] = sample;
    // if (recording && buffer_index < ) {
    //     adc_select_input(0);
    //     ring_push(adc_read(), ring, &w_idx, &r_idx);
    //     adc_select_input(1);
    //     ring_push(adc_read(), ring1, &w_idx1, &r_idx1);
    // }
}

void core1_entry() {
    
    printf("Core 1 started.\n");

    if (!sd_init_driver()) {
        printf("ERROR: Could not initialize SD card\r\n");
        while (true);
    } else {
        printf("SD card initialized.\r\n");
    }

    fr = f_mount(&fs, "0:", 1);
    if (fr != FR_OK) {
        printf("ERROR: Could not mount filesystem (%d)\r\n", fr);
        while (true);
    } else {
        printf("Filesystem mounted.\r\n");
    }

    strcpy(pb_filename, "pluck_5_7.wav");

    pb_fr = f_open(&fil_pb, pb_filename, FA_READ);

    f_lseek(&fil_pb, 44);

    if (pb_fr != FR_OK) {
        printf("ERROR: Could not open file\n");
        while (true);
    } else {
        f_read(&fil_pb, (void*)&sample_buffer[pb_write], BYTES_TO_READ, &pb_bw);
        pb_write = (pb_write + pb_bw/2) % BUFFER_SIZE;
        data_ready = true;
        // printf("File opened\n");
    }

    pb_fr = f_close(&fil_pb);
    if (pb_fr != FR_OK) {
        printf("ERROR: Could not close file (%d)\r\n", pb_fr);
        while (true);
    } else {
        // printf("File closed: %s\r\n", pb_filename);
    }


    f_unmount("0:");

    while (true) {
        tight_loop_contents();
    }
}

int main()
{
    stdio_init_all();   

    sleep_ms(2000); 
    
    printf("--- RP2040 Multicore Demo ---\n");
    printf("Core 0: Starting main loop.\n");

    multicore_launch_core1(core1_entry);
    
    // --- Core 0 Main Loop ---

    while (!data_ready) {
        printf("waiting for data\n");
        // tight_loop_contents();
    }

    if (!ml_model.init()) {
        printf("Failed to initialize ML model!\n");
        while (1) { tight_loop_contents(); }
    } else {
        printf("ML model initialized.\n");
    }

    if (!dsp_pipeline.init()) {
        printf("Failed to initialize DSP Pipeline!\n");
        while (1) { tight_loop_contents(); }
    } else {
        printf("DSP Pipeline initialized.\n");
    }

    // while (true) { tight_loop_contents(); }


    scaled_spectrum = (int8_t*)ml_model.input_data();
    spectogram_divider = 64 * ml_model.input_scale(); 
    spectrogram_zero_point = ml_model.input_zero_point();

    int samples_to_process = INPUT_BUFFER_SIZE;

    int counter = 0;
    while (true) {
        // Core 0 executes its task here.
        if (current_read_index + samples_to_process >= pb_write) {
            printf("Finished file. Looping back.\n");
            current_read_index = 0;
        }

        memmove(
            capture_buffer_q15, 
            (q15_t*)&sample_buffer[current_read_index], 
            samples_to_process * sizeof(q15_t)
        );
        current_read_index += samples_to_process;
        
        memmove(input_q15, 
                &input_q15[INPUT_BUFFER_SIZE], 
                (FFT_SIZE / 2) * sizeof(q15_t));
                
        arm_shift_q15(capture_buffer_q15, INPUT_SHIFT, 
                input_q15 + (FFT_SIZE / 2), INPUT_BUFFER_SIZE);
        
        // Example task: Slow process / Communication

        for (int i = 0; i < SPECTRUM_SHIFT; i++) {
            dsp_pipeline.calculate_spectrum(
                input_q15 + i * ((FFT_SIZE / 2)),
                scaled_spectrum + (129 * (124 - SPECTRUM_SHIFT + i)),
                spectogram_divider, spectrogram_zero_point
            );
        }

        float prediction = ml_model.predict();

        printf("Prediction %d: %f\n", counter++, prediction);

        sleep_ms(1000); 
    }

    return 0;
}
