import scipy.io.wavfile as wavfile
output_filename = 'snap.txt'
import numpy as np



def get_raw_samples_numpy(filename):
    """Reads a WAV file and returns the sample data as a NumPy array."""
    try:
        # rate is the sampling frequency (e.g., 44100)
        # data is the NumPy array containing the samples
        rate, data = wavfile.read(filename)
        original_dtype = data.dtype
        print("original_dtype = ", original_dtype)
        print("original size = ", len(data))
        print(data.flatten())
        data = np.array(data)
        with open(output_filename, 'wb') as f:
            f.write(data.flatten().tobytes())

        return data


    except Exception as e:
        print(f"Error reading WAV file: {e}")
        return None

samples = get_raw_samples_numpy("sound_primitives/snap.wav")

