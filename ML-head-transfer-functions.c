#include <stdio.h>
#include <math.h>
#include <string.h>

#include "pico/stdlib.h"
// #include "hardware/dma.h"
#include "pico/multicore.h"
#include "hardware/spi.h"
#include "hardware/adc.h"
#include "hardware/sync.h"

// Include protothreads
#include "pt_cornell_rp2040_v1_4.h"

// #include "hardware/clocks.h"

#include "./sd_card_fat_serial/sd_card.h"
#include "./sd_card_fat_serial/ff.h"

#define ALARM_NUM 0
#define ALARM_IRQ TIMER_IRQ_0
#define DELAY 125 // 1/Fs (in microeconds)

#define LED      25

#define ISR_GPIO 2
volatile uint16_t sample;
volatile uint16_t sample_buffer[1024];
volatile uint16_t buffer_index = 0;

static int timestamp;

#define RING_SIZE 4096
volatile uint16_t ring[RING_SIZE];
volatile uint32_t w_idx = 0;
volatile uint32_t r_idx = 0;

static inline bool ring_push(uint16_t s) {
    uint32_t next = (w_idx + 1) & (RING_SIZE - 1);
    if (next == r_idx) return false;
    ring[w_idx] = s;
    w_idx = next;
    return true;
}

static inline ring_pop(uint16_t *out) {
    if (r_idx == w_idx) return false;
    *out = ring[r_idx];
    r_idx = (r_idx + 1) & (RING_SIZE - 1);
    return true;
}

RESULT fr;
FATFS fs;
FIL fil;
char filename[] = "test.wav";

static void alarm_irq(void)
{
    gpio_put(ISR_GPIO, 1);
    timestamp = time_us_32();
    // Clear the interrupt
    hw_clear_bits(&timer_hw->intr, 1u << ALARM_NUM);

    // Reset the alarm register
    timer_hw->alarm[ALARM_NUM] = timer_hw->timerawl + DELAY ;

    // sample = adc_read();
    // sample_buffer[buffer_index] = sample;
    ring_push(adc_read());
    // buffer_index++;
    // printf("ADC Sample: %f\n", (float)sample);

    if (time_us_32() - timestamp <= DELAY) {
        timestamp = time_us_32();
        gpio_put(LED, 1);
    }

    gpio_put(ISR_GPIO, 0);
}

static PT_THREAD (protothread_core_0(struct pt *pt))
{
    // Indicate thread beginning
    PT_BEGIN(pt) ;

    static int begin_time ;
    static int spare_time ;

    int ret;
    // char buf[100];

    // Initialize SD card
    if (!sd_init_driver()) {
        printf("ERROR: Could not initialize SD card\r\n");
        while (true);
    }

    // Mount drive
    fr = f_mount(&fs, "0:", 1);
    if (fr != FR_OK) {
        printf("ERROR: Could not mount filesystem (%d)\r\n", fr);
        while (true);
    }

    while(1) {
        begin_time = time_us_32();
        spare_time = DELAY - (time_us_32() - begin_time);

        // Samples processing goes here!

        PT_YIELD_usec(spare_time);
    }

    // Indicate thread end
    PT_END(pt) ;
}

static PT_THREAD (protothread_serial(struct pt *pt))
{
    PT_BEGIN(pt);
    static char classifier;
    static int test_in;
    static float float_in;
    while (1) {
        sprintf(pt_serial_out_buffer, "input a command: ");
        serial_write;
        serial_read;
        sscanf(pt_serial_in_buffer, "%c", &classifier);


    }
}

int main()
{
    stdio_init_all();
    printf("Starting ADC with Timer IRQ example\n");
    adc_init();
    adc_gpio_init(26);
    adc_select_input(0);

    gpio_init(ISR_GPIO) ;
    gpio_set_dir(ISR_GPIO, GPIO_OUT);
    gpio_put(ISR_GPIO, 0) ;

    gpio_init(LED) ;
    gpio_set_dir(LED, GPIO_OUT) ;
    gpio_put(LED, 0) ;

    hw_set_bits(&timer_hw->inte, 1u << ALARM_NUM);
    irq_set_exclusive_handler(ALARM_IRQ, alarm_irq);
    irq_set_enabled(ALARM_IRQ, true);
    timer_hw->alarm[ALARM_NUM] = timer_hw->timerawl + DELAY;

    // Add core 0 threads
    pt_add_thread(protothread_core_0) ;

    // Start scheduling core 0 threads
    pt_schedule_start ;
}
