import os
import glob
import numpy as np
from scipy.io import wavfile
import noisereduce as nr

INPUT_FOLDER = "/Users/zack/ECE5730/microcontrollers/wav-fixed"
OUTPUT_FOLDER = "/Users/zack/ECE5730/microcontrollers/post-noise-reduction"

# Your desired noise segment times
NOISE_SAMPLE_START = 1.150
NOISE_SAMPLE_END = 2.090


def process_wav_file(file_path):
    """Reads, processes, and writes a single WAV file with noise reduction."""
    
    try:
        rate, data = wavfile.read(file_path)
        original_dtype = data.dtype
        
        # --- 1. Handle Stereo/Mono and Convert to Float (CRITICAL STEP) ---
        
        # Check if the audio is stereo (2D array) or mono (1D array)
        if data.ndim > 1:
            # For simplicity, convert stereo to mono by taking the average of the two channels
            audio_data = np.mean(data, axis=1)
        else:
            audio_data = data
            
        # Convert integer data to float (-1.0 to 1.0) for processing
        # This prevents precision errors and compatibility issues in noisereduce
        max_amplitude = np.iinfo(original_dtype).max
        audio_float = audio_data.astype(np.float64) / max_amplitude
        
        
        # --- 2. Extract Noise Segment ---
        
        start_idx = int(NOISE_SAMPLE_START * rate)
        end_idx = int(NOISE_SAMPLE_END * rate)
        noise_segment = audio_float[start_idx:end_idx]

        
        # --- 3. Perform Noise Reduction ---
        
        print("  -> Performing noise reduction...")
        # Use the specific noise segment and pass a specific time_constant_s for better results
        reduced_noise_float = nr.reduce_noise(
            y=audio_float, 
            sr=rate, 
            y_noise=noise_segment,
            prop_decrease=0.95, # Aggressiveness of reduction (0.0 to 1.0)
            time_constant_s=2.0
        )
        
        
        # --- 4. Convert Back to Original Integer Type (CRITICAL STEP) ---
        
        # Scale the float data back to the original amplitude range
        reduced_noise_int = (reduced_noise_float * max_amplitude).astype(original_dtype)
        
        
        # --- 5. Write Output ---
        
        output_filename = os.path.basename(file_path).replace(".wav", "_clean.wav")
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        # Note: If the input was stereo, we are only writing mono output here.
        wavfile.write(output_path, rate, reduced_noise_int)
        
        print(f"  -> Successfully processed and saved {output_filename}")

    except Exception as e:
        print(f"  !!! ERROR processing {os.path.basename(file_path)}: {e}")


def main():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    search_path = os.path.join(INPUT_FOLDER, "*.wav")
    files_to_process = glob.glob(search_path)

    if not files_to_process:
        print(f"No .wav files found in {INPUT_FOLDER}. Exiting.")
        return

    print(f"Found {len(files_to_process)} files to process. Starting batch job.")
    
    for i, file_path in enumerate(files_to_process):
        print(f"\nProcessing File {i+1}/{len(files_to_process)}: {os.path.basename(file_path)}")
        process_wav_file(file_path)

if __name__ == "__main__":
    main()
