/*
    3V (pin 36) --> ADC VDD
    - GPIO 13 (pin 17) CS -> ADC CS
    GND (pin 38) -> ADC VSS
    - GPIO 10 (pin 14) SCK -> ADC SCK
    - GPIO 11 (pin 15) MOSI/spi1_tx -> ADC SDI
    GPIO 9 (pin 12) -> LDAC
*/

// SPI Config for DAC
// #define PIN_MISO 4
#define PIN_MISO 12
#define PIN_CS   13
#define PIN_SCK  10
#define PIN_MOSI 11
#define SPI_PORT spi1
#define LDAC     9

#include <stdio.h>
#include <math.h>
#include <string.h>

#include "pico/stdlib.h"
// #include "hardware/dma.h"
#include "pico/multicore.h"
#include "hardware/spi.h"
#include "hardware/adc.h"
#include "hardware/sync.h"
#include "hardware/clocks.h"

// Include protothreads
#include "pt_cornell_rp2040_v1_4.h"

#include "sd_card.h"
#include "ff.h"

#define ALARM_NUM 0
#define ALARM_IRQ TIMER_IRQ_0
#define DELAY 22.68 // 1/Fs (in microseconds)

#define AUDIO_PB_IRQ TIMER_IRQ_1
#define PB_DELAY 23 // 1/Fs (in microseconds)


#define LED      25

#define ISR_GPIO 2
#define ISR_GPIO_PLAYBACK 17
#define BUFFER_SIZE 100000
volatile int16_t sample;
volatile int16_t sample_buffer[BUFFER_SIZE];
volatile uint16_t buffer_index = 0;
volatile int pb_read = 0;
volatile int pb_write = 0;

#define NUM_BUFFERS 2
#define BUFFER_SIZE_SAMPLES 2048

#define BYTES_TO_READ 100000

// volatile int16_t audio_buffers[NUM_BUFFERS][BUFFER_SIZE_SAMPLES];
// volatile uint8_t current_play_buffer = 0;
// volatile bool buffer_ready[NUM_BUFFERS] = { false, false };

// DMA Sound Playback ------------------------------------------------

// Audio Primitives
// Sample Rate = 44.1 kHz
// Bits per sample = 16
// Number of channels = 1
// Duration = 10 seconds

#define AUDIO_SAMPLE_COUNT 2000

// use unsigned short or uint16_t for 16-bit samples ??
int16_t audio_samples[AUDIO_SAMPLE_COUNT] ;


#define DAC_config_chan_A 0b0001000000000000// DAC channel A, unbuffered, gain = 1x, active


// max number of samples per DMA transfer??

int data_chan;;
int ctrl_chan;;

// -------------------------------------------------------------------


static int timestamp;

#define RING_SIZE 9000
volatile uint16_t ring[RING_SIZE];
volatile uint16_t ring1[RING_SIZE];
volatile uint32_t w_idx = 0;
volatile uint32_t r_idx = 0;
volatile uint32_t w_idx1 = 0;
volatile uint32_t r_idx1 = 0;
// -----------------------------Things alex added 12/9--------------------------------------
#define WRITE_BLOCK_SIZE_BYTES 4096
#define WRITE_BLOCK_SIZE_SAMPLES (WRITE_BLOCK_SIZE_BYTES / 4)// 4 bytes per stereo sample samples (2x int16_t)
// flag used by serial thread to signal to core 1 to flush leftover data on file close
volatile bool flush_on_close = false;
// -----------------------------Things alex added 12/9--------------------------------------



static inline bool ring_push(uint16_t s, volatile uint16_t* ring_, volatile uint32_t* w_idx_, volatile uint32_t* r_idx_) {
    uint32_t next = (*w_idx_ + 1) & (RING_SIZE - 1);
    if (next == *r_idx_) {
        gpio_put(LED, 1);
        return false;
    }
    ring_[*w_idx_] = s;
    *w_idx_ = next;
    return true;
}

static inline bool ring_pop(uint16_t *out, volatile uint16_t* ring_, volatile uint32_t* w_idx_, volatile uint32_t* r_idx_) {
    if (*r_idx_ == *w_idx_) {
        gpio_put(LED, 1);
        return false;
    }
    *out = ring_[*r_idx_];
    *r_idx_ = (*r_idx_ + 1) & (RING_SIZE - 1);
    return true;
}

typedef struct {
    uint32_t sample_rate;
    uint16_t bits_per_sample;
    uint16_t num_channels;
} wav_format_t;

FRESULT fr;
FATFS fs;
FIL fil;
bool file_open = false;
char filename[1000];
UINT bw;
uint32_t data_bytes = 0;

FRESULT pb_fr;
FIL fil_pb;
UINT pb_bw;
bool file_read = false;
char pb_filename[1000];

FRESULT test_fr;
FIL fil_test;
UINT test_bw;
char txt_res;


static struct pt_sem file_sem;

void write_wav_header(FIL *fil, uint32_t data_size, wav_format_t fmt) { // wave file header is 44 bytes
    uint32_t byte_rate = fmt.sample_rate * fmt.num_channels * (fmt.bits_per_sample / 8);
    uint16_t block_align = fmt.num_channels * (fmt.bits_per_sample / 8);

    uint8_t header[44] = {
        'R', 'I', 'F', 'F',
        0, 0, 0, 0,
        'W', 'A', 'V', 'E',
        'f', 'm', 't', ' ',
        16, 0, 0, 0,
        1, 0,
        fmt.num_channels, 0,
        fmt.sample_rate & 0xFF, (fmt.sample_rate>>8)&0xFF,
        (fmt.sample_rate>>16)&0xFF, (fmt.sample_rate>>24)&0xFF,
        byte_rate & 0xFF, (byte_rate>>8)&0xFF, (byte_rate>>16)&0xFF, (byte_rate>>24)&0xFF,
        block_align & 0xFF, (block_align >> 8) & 0xFF,
        fmt.bits_per_sample & 0xFF, (fmt.bits_per_sample >> 8) & 0xFF,
        'd','a','t','a',
        data_size & 0xFF, (data_size>>8)&0xFF,
        (data_size>>16)&0xFF, (data_size>>24)&0xFF
    };

    // RIFF chunk size = 36 + data_size
    uint32_t chunk_size = 36 + data_size;
    header[4] = chunk_size & 0xFF;
    header[5] = (chunk_size >> 8) & 0xFF;
    header[6] = (chunk_size >> 16) & 0xFF;
    header[7] = (chunk_size >> 24) & 0xFF;

    UINT bw;
    f_lseek(fil, 0);
    fr = f_write(fil, header, 44, &bw);

    if (fr != FR_OK || bw != 44) {
        printf("WAV header write failed: %d, bw=%u\n", fr, bw);
    }

    printf("WAV: %lu Hz, %u ch, %u bits, data = %lu bytes\n",
       fmt.sample_rate, fmt.num_channels,
       fmt.bits_per_sample, data_size);
}

wav_format_t fmt = {
    .sample_rate = 44100,
    .bits_per_sample = 16,
    .num_channels = 2
};

static void alarm_irq(void)
{
    // printf("IRQ\n");
    gpio_put(ISR_GPIO, 1);
    timestamp = time_us_32();
    // Clear the interrupt
    hw_clear_bits(&timer_hw->intr, 1u << ALARM_NUM);

    // Reset the alarm register
    timer_hw->alarm[ALARM_NUM] = timer_hw->timerawl + DELAY ;

    // sample = adc_read();
    // sample_buffer[buffer_index] = sample;
    if (file_open) {
        adc_select_input(0);
        ring_push(adc_read(), ring, &w_idx, &r_idx);
        adc_select_input(1);
        ring_push(adc_read(), ring1, &w_idx1, &r_idx1);
    }
    // buffer_index++;
    // printf("ADC Sample: %f\n", (float)sample);

    // if (time_us_32() - timestamp <= DELAY) {
    //     timestamp = time_us_32();
    //     gpio_put(LED, 1);
    // }

    PT_SEM_SIGNAL(pt, &file_sem);

    gpio_put(ISR_GPIO, 0);
}

static inline int16_t adc_to_pcm16(uint16_t raw) {
    return ((int32_t)raw - 2048) << 4;
}

static PT_THREAD (protothread_core_1(struct pt *pt))
{
    // Indicate thread beginning
    PT_BEGIN(pt) ;
    printf ("Core 0 thread running...\n");
    // static buffer and idex for core 1 bulk write to SD card 
    static int16_t  write_buffer[WRITE_BLOCK_SIZE_SAMPLES*2];
    static uint16_t buffer_pcm_idx = 0; //current index: units of samples 
    static UINT bw_local;
    static int begin_time ;
    static int spare_time ;
    int ret;
    // Initialize SD card
    if (!sd_init_driver()) {
        printf("ERROR: Could not initialize SD card\r\n");
        while (true);
    } else {
        printf("SD card initialized.\r\n");
    }

    // Mount drive
    fr = f_mount(&fs, "0:", 1);
    if (fr != FR_OK) {
        printf("ERROR: Could not mount filesystem (%d)\r\n", fr);
        while (true);
    } else {
        printf("Filesystem mounted.\r\n");
    }
    // printf("Core 0 thread still running...\n");
    while(1){
        //wait for semaphore signal from timer irq
        PT_SEM_WAIT(pt, &file_sem);
        // data accumulation and bulk write loop
        if (file_open){
            uint16_t raw_l, raw_r;
            int16_t pcm_l, pcm_r;
            // check if a stereo sample pair is ready
            while ((ring_pop(&raw_l,ring,&w_idx,&r_idx) && 
            ring_pop(&raw_r,ring1,&w_idx1,&r_idx1)))
            {
                // convert ADC raw to 16-bit PCM 
                pcm_l = adc_to_pcm16(raw_l);
                pcm_r = adc_to_pcm16(raw_r);
                // store interleaved samples in write buffer
                write_buffer[buffer_pcm_idx++] = pcm_l;
                write_buffer[buffer_pcm_idx++] = pcm_r; 
                // check if RAM buffer is full and needs a bulk write to SD 
                if (buffer_pcm_idx >= WRITE_BLOCK_SIZE_SAMPLES*2){
                    fr = f_write(&fil, write_buffer, WRITE_BLOCK_SIZE_BYTES, &bw_local);
                    if (fr != FR_OK ){
                        printf("ERROR: Write failed (%d)\r\n", fr);
                    }
                    data_bytes += WRITE_BLOCK_SIZE_BYTES;
                    buffer_pcm_idx = 0; // reset buffer index
                }
            } 
        }
        // flush logic check on close signal 
        if (flush_on_close && !file_open){
            UINT bytes_to_flush = buffer_pcm_idx * 2; // bytes to flush
            
            if (bytes_to_flush>0){
                fr = f_write(&fil, write_buffer, bytes_to_flush, &bw_local);
                if (fr != FR_OK ){
                    printf("ERROR: Write failed (%d)\r\n", fr);
                }
                data_bytes += bytes_to_flush;
            }
            buffer_pcm_idx = 0; // reset buffer index
            flush_on_close = false; // reset flush flag
        }
    }
    PT_END(pt) ;
    // while(1) {
    //     PT_SEM_WAIT(pt, &file_sem);
    //     // printf("Core 0 thread running...\n");
    //     begin_time = time_us_32();

    //     // Samples processing goes here!
    //     while (file_open) {
    //         uint16_t raw;
    //         if (ring_pop(&raw, ring, &w_idx, &r_idx)) {
    //             int16_t pcm = adc_to_pcm16(raw);
    //             f_write(&fil, &pcm, 2, &bw);
    //             data_bytes += 2;
    //         }
    //         if (ring_pop(&raw, ring1, &w_idx1, &r_idx1)) {
    //             int16_t pcm = adc_to_pcm16(raw);
    //             f_write(&fil, &pcm, 2, &bw);
    //             data_bytes += 2;
    //         }
    //     }
    //     PT_YIELD_usec(spare_time);
    // }
    // Indicate thread end

}

static PT_THREAD (protothread_serial(struct pt *pt))
{
    // printf("Serial thread running...\n");
    PT_BEGIN(pt);
    static char classifier;
    static int test_in;
    static float float_in;

    static int file_index = 0;
    static int angle1;
    static int angle2;
    while(1) {
        sprintf(pt_serial_out_buffer, "input a command: ");
        serial_write;
        serial_read;
        sscanf(pt_serial_in_buffer, "%c", &classifier);

        if (classifier=='o') {
            fr = f_open(&fil, filename, FA_WRITE | FA_CREATE_ALWAYS);
            if (fr != FR_OK) {
                printf("ERROR: Could not open file (%d)\r\n", fr);
                while (true);
            } else {
                printf("File opened: %s\r\n", filename);
            }

            // 2. Open file for reading
            // test_fr = f_open(&fil_test, "helloworld.txt", FA_READ);
            // if (test_fr != FR_OK) {
            //     printf("Open failed: %d\n", test_fr);
            // } else {
            //     printf("Txt file opened\n");
            // }

            // sample_buffer[buffer_index] = sample;
            pb_fr = f_open(&fil_pb, ".txt", FA_READ);
            if (pb_fr != FR_OK) {
                printf("ERROR: Could not open file\n");
                while (true);
            } else {
                // f_lseek(&fil_pb, 40000); 

                f_read(&fil_pb, &sample_buffer[pb_write], 100000, &pb_bw);
                pb_write = (pb_write + pb_bw/2) % BUFFER_SIZE;
                // f_lseek(&fil_pb, pb_write * 2 + 1); 
                // int16_t sample_pb;
                // f_lseek(&fil_pb, 2); 
                // f_read(&fil_pb, &sample_pb, 1, &pb_bw);
                // printf("char = %d \n", sample_pb);
                // f_lseek(&fil_pb, 44); 
                printf("File opened\n");
            }

            file_open = true;
        }
        if (classifier == 'd') {
            printf("Closing file...\r\n");
            file_open = false;
            //--signal core 1 to flush any leftover data
            flush_on_close = true;
            PT_YIELD(pt);
            //---------signal core 1 to flush any leftover data---------
            write_wav_header(&fil, data_bytes, fmt);
            fr = f_close(&fil);
            if (fr != FR_OK) {
                printf("ERROR: Could not close file (%d)\r\n", fr);
                while (true);
            } else {
                printf("File closed: %s\r\n", filename);
            }
            pb_fr = f_close(&fil_pb);
            if (pb_fr != FR_OK) {
                printf("ERROR: Could not close file (%d)\r\n", pb_fr);
                while (true);
            } else {
                printf("File closed: %s\r\n", pb_filename);
            }
            memset(filename, '\0', 1000);
            memset(pb_filename, '\0', 1000);

            w_idx = 0;
            r_idx = 0;
            w_idx1 = 0;
            r_idx1 = 0;

            pb_read = 0;
            pb_write = 0;
        }
        if (classifier == 'u') {
            f_unmount("0:");
        }
        if (classifier == 'p') {
            // start a test
            // information needed:
            // -> sound primitive chosen (1-10)
            // -> orientation (degrees) 
        
            // open the choen file
            // decode the audio data
            // send to DAC via SPI

            sprintf(pt_serial_out_buffer, "choose audio file to play [1 to 6]: \r\n");
            serial_write ;
            serial_read ;
            sscanf(pt_serial_in_buffer,"%d", &file_index) ;

            switch(file_index) {
                case 1:
                    strcpy(pb_filename, "sine_16.txt");
                    break;
                case 2:
                    strcpy(pb_filename, "pluck.txt");
                    break;
                case 3:
                    strcpy(pb_filename, "linear_p5_200_p1_1400_sine_chirp.txt");
                    break;
                case 4: 
                    strcpy(pb_filename, "sweep.txt");
                    break;
                case 5:
                    strcpy(pb_filename, "sharp-sweep.txt");
                    break;
                case 6:
                    strcpy(pb_filename, "207bpm_8bpb_ping_short.txt");
                    break;
                default:
                    strcpy(pb_filename, "sine_16.txt");
                    break;
            }

            sprintf(pt_serial_out_buffer, "angle 1: \r\n");
            serial_write ;
            serial_read ;
            sscanf(pt_serial_in_buffer,"%d", &angle1) ;

            sprintf(pt_serial_out_buffer, "angle 2: \r\n");
            serial_write ;
            serial_read ;
            sscanf(pt_serial_in_buffer,"%d", &angle2) ;

            printf("pb_filename: %s\n", pb_filename);
            strcpy(filename, pb_filename);

            printf("filename: %s\n", filename);

            char *ext = strrchr(filename, '.');  // find ".txt"
            printf("Filename generation...\r\n");

            if (ext != NULL) {
                char temp[128];

                // Copy base name without extension

                size_t base_len = ext - filename;
                memcpy(temp, filename, base_len);
                temp[base_len] = '\0';

                // Build new filename
                snprintf(filename, sizeof(filename),
                        "%s_%d_%d.wav",
                        temp, angle1, angle2);
            }
            printf("Output filename: %s\r\n", filename);

            fr = f_open(&fil, filename, FA_WRITE | FA_CREATE_ALWAYS);
            if (fr != FR_OK) {
                printf("ERROR: Could not open file (%d)\r\n", fr);
                while (true);
            } else {
                printf("File opened: %s\r\n", filename);
            }

            pb_fr = f_open(&fil_pb, pb_filename, FA_READ);
            if (pb_fr != FR_OK) {
                printf("ERROR: Could not open file\n");
                while (true);
            } else {
                f_read(&fil_pb, &sample_buffer[pb_write], BYTES_TO_READ, &pb_bw);
                pb_write = (pb_write + pb_bw/2) % BUFFER_SIZE;
                printf("File opened\n");
            }

            file_open = true;
        }
    }
    PT_END(pt);
}

void core1_entry() {
    pt_add_thread(protothread_core_1);
    pt_schedule_start;
}

void playback_callback() {
    static int begin_time ;
    static int spare_time ;

    begin_time = time_us_32();

    // get data from the sd card wav files somehow
    // Clear the interrupt
    hw_clear_bits(&timer_hw->intr, 1u << 1);

    // Reset the alarm register
    timer_hw->alarm[1] = timer_hw->timerawl + PB_DELAY ;

    if (!file_read && file_open) {
    // if (file_open) {
        // uint8_t sample_pb;
        // f_write(&fil, &pcm, 2, &bw);
        // gpio_put(ISR_GPIO_PLAYBACK, 1);

        // f_read(&fil_pb, &sample_pb, 1, &pb_bw);
        // gpio_put(ISR_GPIO_PLAYBACK, 0);

        // sample_pb = sample_buffer[pb_read];
        // printf("%d\n", sample_pb);
        uint16_t DAC_data; 
        uint16_t sample_pb = sample_buffer[pb_read];
        // int32_t sample_pb = (int32_t)sample_buffer[pb_read] + 32768;
        int original_sample =  sample_buffer[pb_read];
        // printf("%d\n", original_sample);
        DAC_data = (uint16_t)(DAC_config_chan_A | (((sample_pb >> 4)) & 0xfff));
        
        // DAC_data = (DAC_config_chan_A | (sample_pb & 0xffff))  ;
        spi_write16_blocking(SPI_PORT, &DAC_data, 1);
        pb_read = (pb_read + 1) % BUFFER_SIZE;
        // buffer_index = buffer_index + 2;
        // if (buffer_index >= BYTES_TO_READ) {
        //     file_read = true;
        //     file_open = false;
            
        //     printf("Closing file...\r\n");
        //     write_wav_header(&fil, data_bytes, fmt);
        //     fr = f_close(&fil);
        //     if (fr != FR_OK) {
        //         printf("ERROR: Could not close file (%d)\r\n", fr);
        //         while (true);
        //     } else {
        //         printf("File closed: %s\r\n", filename);
        //     }

        //     pb_fr = f_close(&fil_pb);
        //     if (pb_fr != FR_OK) {
        //         printf("ERROR: Could not close file (%d)\r\n", pb_fr);
        //         while (true);
        //     } else {
        //         printf("File closed: %s\r\n", pb_filename);
        //     }

        //     printf("playback ended\n");
        // }
        // f_read(&fil_test, &txt_res, 1, &pb_bw);
       
        // printf("char = %c \n", txt_res);
        // if (pb_bw < 1) {
        //     // printf("file ended \n");
        //     f_lseek(&fil_pb, 44); 
        // }
    }
    // spare_time = PB_DELAY - (time_us_32() - begin_time);
    // if (spare_time <= 0) {
    //     gpio_put(LED, 1);
    // } else {
    //     gpio_put(LED, 0);
    // }
}

int main()
{
    set_sys_clock_khz(250000, true);
    stdio_init_all();
    printf("Starting ADC with Timer IRQ example\n");
    adc_init();
    adc_gpio_init(26);
    adc_gpio_init(27);
    adc_select_input(0);

    gpio_init(ISR_GPIO) ;
    gpio_set_dir(ISR_GPIO, GPIO_OUT);
    gpio_put(ISR_GPIO, 0) ;

    gpio_init(ISR_GPIO_PLAYBACK) ;
    gpio_set_dir(ISR_GPIO_PLAYBACK, GPIO_OUT);
    gpio_put(ISR_GPIO_PLAYBACK, 0) ;

    gpio_init(LED) ;
    gpio_set_dir(LED, GPIO_OUT) ;
    gpio_put(LED, 0) ;

    hw_set_bits(&timer_hw->inte, 1u << ALARM_NUM);
    irq_set_exclusive_handler(ALARM_IRQ, alarm_irq);
    irq_set_enabled(ALARM_IRQ, true);
    timer_hw->alarm[ALARM_NUM] = timer_hw->timerawl + DELAY; // ~44.1 kHz

    hw_set_bits(&timer_hw->inte, 1u << 1);
    irq_set_exclusive_handler(AUDIO_PB_IRQ, playback_callback);
    irq_set_enabled(AUDIO_PB_IRQ, true);
    timer_hw->alarm[1] = timer_hw->timerawl + PB_DELAY; // ~44.1 kHz

    // Begin - SPI Init for DAC
    spi_init(SPI_PORT, 20000 * 1000); // 20 MHz
    spi_set_format(SPI_PORT, 16, 0, 0, 0); // 16 bits per transfer
    gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_CS, GPIO_FUNC_SPI);

    gpio_init(LDAC);
    gpio_set_dir(LDAC, GPIO_OUT);
    gpio_put(LDAC, 0);
    // End - SPI Init for DAC

    /////////////////////////////////////////////////////////////////////////////////////////////////////
    // ============================== PIO & DMA Channels ================================================
    /////////////////////////////////////////////////////////////////////////////////////////////////////

    // PIO pio = pio0;
    // uint offset = pio_add_program(pio, &audio_program);
    // pio_sm_claim (pio, 0);

    // pio_set_irq0_source_enabled(pio0, pis_interrupt0, true);
    // irq_add_shared_handler(PIO1_IRQ_0, playback_callback, 0);
    // irq_set_enabled(PIO1_IRQ_0, true);

    // audio_program_init(pio, 0, offset, AUDIO_PB_PIN);
 
    // data_chan = dma_claim_unused_channel(true);;
    // ctrl_chan = dma_claim_unused_channel(true);;
    // // Setup Control DMA Channel
    // dma_channel_config c = dma_channel_get_default_config(ctrl_chan);   // default configs
    // channel_config_set_transfer_data_size(&c, DMA_SIZE_32);             // 32-bit txfers
    // channel_config_set_read_increment(&c, false);                       // no read incrementing
    // channel_config_set_write_increment(&c, false);                      // no write incrementing
    // channel_config_set_chain_to(&c, data_chan);                         // chain to data channel

    // dma_channel_configure(
    //     ctrl_chan,                          // Channel to be configured
    //     &c,                                 // The configuration we just created
    //     &dma_hw->ch[data_chan].read_addr,   // Write address (data channel read address)
    //     &dma_pointer,                   // Read address (POINTER TO AN ADDRESS)
    //     1,                                  // Number of transfers
    //     false                               // Don't start immediately
    // );

    // // Setup Data DMA Channel
    // dma_channel_config c2 = dma_channel_get_default_config(data_chan);
    // channel_config_set_transfer_data_size(&c2, DMA_SIZE_16);  
    // channel_config_set_read_increment(&c2, true);                       // yes read incrementing
    // channel_config_set_write_increment(&c2, false);                     // no write incrementing
    // // sys_clk is 125 MHz unless changed in code. Configured to ~44 kHz
    // dma_timer_set_fraction(0, 0x0017, 0xffff) ;

    // 0x3b means timer0 (see SDK manual)
    // Is timer 0 being used by anything else???
    // channel_config_set_dreq(&c2, DREQ_PIO0_IRQ_0);                                 // DREQ paced by timer 0

    // dma_channel_configure(
    //     data_chan,                  // Channel to be configured
    //     &c2,                        // The configuration we just created
    //     &spi_get_hw(SPI_PORT)->dr,  // write address (SPI data register)
    //     DAC_data,                   // The initial read address
    //     AUDIO_SAMPLE_COUNT,            // Number of transfers
    //     false                       // Don't start immediately.
    // );


    // start the control channel
    // dma_start_channel_mask(1u << ctrl_chan) ;

    /////////////////////////////////////////////////////////////////////////////////////////////////////
    // ============================== PIO & DMA Channels END ============================================
    /////////////////////////////////////////////////////////////////////////////////////////////////////

    multicore_reset_core1();
    multicore_launch_core1(core1_entry);

    // // Add core 0 threads
    pt_add_thread(protothread_serial) ;
    // // Start scheduling core 0 threads
    pt_schedule_start ;
}