import os
import glob
import wave
import struct # Not strictly needed here, but useful for low-level audio work

# --- Configuration ---
INPUT_FOLDER = "/Users/zack/ECE5730/microcontrollers/raw"
OUTPUT_FOLDER = "/Users/zack/ECE5730/microcontrollers/wav-fixed"
HEADER_SIZE = 44 # The size to skip at the start of every file

# --- Known Raw Audio Parameters (CRITICAL: Set these correctly!) ---
# Example for standard 16-bit mono audio:
SAMPLE_RATE = 44100   # e.g., 44100 Hz
N_CHANNELS = 2        # 1 for mono, 2 for stereo
SAMPLE_WIDTH = 2      # 2 bytes = 16-bit PCM (signed)
# ---------------------

def trim_and_create_wav(input_path, output_path):
    """
    1. Reads raw audio data, skipping the first 44 bytes (the invalid header).
    2. Writes the raw data back with a new, valid 44-byte WAV header.
    """
    try:
        # Step 1: Read raw audio data (skipping the first 44 bytes)
        with open(input_path, 'rb') as in_file:
            # Skip the first 44 bytes using seek()
            in_file.seek(HEADER_SIZE)
            raw_data = in_file.read()

        # Check if the file was too small after trimming
        if not raw_data:
            print("!!! File is empty after header trim. Skipping.")
            return False

        # Step 2: Write the raw data back with a valid WAV header
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(N_CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(raw_data)

        print(f"  -> Successfully created valid WAV file: {os.path.basename(output_path)}")
        return True

    except Exception as e:
        print(f"!!! Error processing {os.path.basename(input_path)}: {e}")
        return False

def main():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    # Search for all files (you may want to restrict to .wav or .dat if needed)
    search_path = os.path.join(INPUT_FOLDER, "*")
    files_to_process = glob.glob(search_path)

    if not files_to_process:
        print(f"No files found in {INPUT_FOLDER}. Exiting.")
        return

    print(f"Found {len(files_to_process)} files. Starting WAV header correction batch job.")
    print(f"  -- Format: {N_CHANNELS} channel(s), {SAMPLE_WIDTH*8}-bit PCM, {SAMPLE_RATE} Hz --")

    for i, file_path in enumerate(files_to_process):
        original_filename = os.path.basename(file_path)
        base_name, ext = os.path.splitext(original_filename)

        # Define output path for the new, corrected WAV file
        # Ensure the output file always has the .wav extension
        output_path = os.path.join(OUTPUT_FOLDER, f"{base_name}_corrected.wav")

        print(f"\nProcessing File {i+1}/{len(files_to_process)}: {original_filename}")

        # Execute the trim and create operation
        trim_and_create_wav(file_path, output_path)

    print("\nBatch WAV header correction complete.")

if __name__ == "__main__":
    main()
