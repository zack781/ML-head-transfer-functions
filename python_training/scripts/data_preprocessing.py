import os
from pathlib import Path
import pdb
import glob
import re
import numpy as np
import librosa
from scipy.io import wavfile

# --- CONFIGURATION DEFAULTS ---
SAMPLE_RATE = 44100
CHUNK_DURATION_MS = 1100  
N_MELS = 32               
SILENCE_THRESHOLD = 0.01  
AZIMUTH_STEPS = 10        
ELEVATION_STEPS = 10      

class AudioSlicer:
    def __init__(self, sample_rate=SAMPLE_RATE, chunk_ms=CHUNK_DURATION_MS, n_mels=N_MELS, silence_thresh=SILENCE_THRESHOLD):
        self.sr = sample_rate
        self.chunk_len = int(sample_rate * (chunk_ms / 1000))
        self.n_mels = n_mels
        self.n_fft = 4096
        self.hop_length = 512 
        self.silence_thresh = silence_thresh

    def process_and_split(self, filepath, label):
        """
        Processes an audio file and splits it into training and testing sets.

        Args:
            filepath (str): Path to the audio file.
            label (int): Label associated with the audio file.

        Returns:
            X_train (list): List of training spectograms.
            y_train (list): List of training labels.
            X_test (list): List of testing spectograms.
            y_test (list): List of testing labels.
        """
        try:
            audio, _ = librosa.load(filepath, sr=self.sr, mono=False)
        except Exception:
            return [], [], [], []
            
        if audio.ndim != 2 or audio.shape[0] != 2: 
            return [], [], [], []
        
        audio = audio.T 
        
        # DC Bias Fix
        audio -= np.mean(audio, axis=0)
        
        total_samples = len(audio)
        num_chunks = total_samples // self.chunk_len
        
        X_train, y_train = [], []
        X_test, y_test = [], []

        for i in range(num_chunks):
            start = i * self.chunk_len
            end = start + self.chunk_len
            segment = audio[start:end, :]
            
            rms = np.sqrt(np.mean(segment**2))
            if rms < self.silence_thresh: continue 

            specs = []
            for ch in range(2): 
                S = librosa.feature.melspectrogram(
                    y=segment[:, ch], sr=self.sr, n_fft=self.n_fft, 
                    hop_length=self.hop_length, n_mels=self.n_mels
                )
                S_db = librosa.power_to_db(S, ref=np.max)
                S_norm = (np.maximum(S_db, -80) + 80) / 80
                specs.append(S_norm.T) 
            
            # Difference Channel (Spatial Cue)
            spec_diff = specs[0] - specs[1]
            spec_diff = np.clip(spec_diff, -1.0, 1.0)
            
            spec_final = np.stack([specs[0], specs[1], spec_diff], axis=-1)
            
            # 80/20 Train/Test Split
            if (i % 5) == 4: 
                X_test.append(spec_final)
                y_test.append(label)
            else:
                X_train.append(spec_final)
                y_train.append(label)
                
        return X_train, y_train, X_test, y_test
    def get_inference_tensor(self, filepath):
        """
        Loads a file and converts it specifically for the TFLite quantized model.
        Returns: (input_tensor, valid_bool)
        """
        # 1. Run standard processing
        # Note: We pass a dummy label because we only need the data
        X_data, _, _, _ = self.process_and_split(filepath, label=0)
        
        if not X_data:
            return None, False

        # 2. Pick the first chunk (or loop through them in your script)
        # Using the first chunk as the representative example
        spec = X_data[0] # Shape is (95, 64, 3)

        # 3. Handle Quantization (Float -> Int8)
        # These values come from your Model Inspection log:
        input_scale = 0.005507847294211388
        input_zero_point = -55
        
        # Formula: q = (real_value / scale) + zero_point
        q_spec = (spec / input_scale) + input_zero_point
        q_spec = np.clip(q_spec, -128, 127) # Ensure it stays within int8 range
        q_spec = q_spec.astype(np.int8)

        # 4. Add Batch Dimension (95,64,3) -> (1,95,64,3)
        input_tensor = np.expand_dims(q_spec, axis=0)
        
        return input_tensor, True
# def load_and_split_dataset(data_dir):
#     slicer = AudioSlicer()
#     files = glob.glob(os.path.join(data_dir, "*.wav"))
    
#     X_train_all, y_train_all = [], []
#     X_test_all, y_test_all = [], []
    
#     # Matches: "_0_0.wav", "_0_0 copy.wav", etc.
#     pattern = re.compile(r'_(\d+)_(\d+)(?:.*)?\.wav$')
    
#     print(f"Found {len(files)} files. Parsing...")
    
#     for f in files:
#         match = pattern.search(f)
#         if match:
#             elev_idx = float(match.group(1))
#             az_idx = float(match.group(2))
            
#             elev_theta = (elev_idx / ELEVATION_STEPS) * (2 * np.pi)
#             az_theta = (az_idx / AZIMUTH_STEPS) * (2 * np.pi)
            
#             label_vector = [
#                 np.sin(elev_theta), np.cos(elev_theta), 
#                 np.sin(az_theta), np.cos(az_theta)
#             ] 
            
#             Xt, yt, Xv, yv = slicer.process_and_split(f, label_vector)
#             X_train_all.extend(Xt); y_train_all.extend(yt)
#             X_test_all.extend(Xv); y_test_all.extend(yv)
            
#     return (np.array(X_train_all), np.array(y_train_all), 
#             np.array(X_test_all), np.array(y_test_all))


def load_and_split_dataset(data_dir):
    slicer = AudioSlicer(SAMPLE_RATE, CHUNK_DURATION_MS, N_MELS, SILENCE_THRESHOLD)
    files = glob.glob(os.path.join(data_dir, "*.wav"))
    
    # 1. Group files by Label (Elev, Az)
    # Dictionary: {(elev, az): [list_of_filenames]}
    files_by_label = {}
    pattern = re.compile(r'_(\d+)_(\d+)(?:.*)?\.wav$')
    
    print(f"Indexing {len(files)} files...")
    for f in files:
        match = pattern.search(f)
        if match:
            elev_idx = int(match.group(1))
            az_idx = int(match.group(2))
            key = (elev_idx, az_idx)
            if key not in files_by_label:
                files_by_label[key] = []
            files_by_label[key].append(f)

    X_train_all, y_train_all = [], []
    X_test_all, y_test_all = [], []
    
    print("Processing with Hybrid Split Strategy...")
    
    for (elev_idx, az_idx), file_list in files_by_label.items():
        # Create the label vector
        elev_theta = (elev_idx / ELEVATION_STEPS) * (2 * np.pi)
        az_theta = (az_idx / AZIMUTH_STEPS) * (2 * np.pi)
        label_vector = [
            np.sin(elev_theta), np.cos(elev_theta), 
            np.sin(az_theta), np.cos(az_theta)
        ]

        # --- STRATEGY: CHECK FILE COUNT ---
        if len(file_list) >= 2:
            # SAFE MODE: Split by File
            # Pick one file randomly for testing, use the rest for training
            test_file = np.random.choice(file_list)
            train_files = [x for x in file_list if x != test_file]
            
            # Process Train Files
            for tf in train_files:
                Xt, yt, _, _ = slicer.process_and_split(tf, label_vector)
                # Force ALL chunks to train (since we reserved a whole file for test)
                X_train_all.extend(Xt); y_train_all.extend(yt)
                
            # Process Test File
            Xt, yt, _, _ = slicer.process_and_split(test_file, label_vector)
            # Force ALL chunks to test
            X_test_all.extend(Xt); y_test_all.extend(yt)
            
        else:
            # FALLBACK MODE: Split by Chunk (Single file available)
            # We MUST split this single file to have representation in both sets
            single_file = file_list[0]
            Xt, yt, Xv, yv = slicer.process_and_split(single_file, label_vector)
            
            # Standard chunk split output
            X_train_all.extend(Xt); y_train_all.extend(yt)
            X_test_all.extend(Xv); y_test_all.extend(yv)

    return (np.array(X_train_all), np.array(y_train_all), 
            np.array(X_test_all), np.array(y_test_all))
def augment_data(X_data):
    """
    Applies a random gain factor to each sample in X_data between 0.7 and 1.3.

    Parameters
    ----------
    X_data : numpy.ndarray
        The input data to be augmented.

    Returns
    -------
    X_aug : numpy.ndarray
        The augmented data.
    """
    X_aug = X_data.copy()
    gain_factor = np.random.uniform(0.7, 1.3, size=(X_aug.shape[0], 1, 1, 1))
    X_aug *= gain_factor
    X_aug = np.clip(X_aug, 0.0, 1.0) 
    return X_aug

# Legacy helper (from your notebook)
def reformat_wav(data_path): 
    """
    Reads a WAV file from the given data path and returns the left and right channels, the sample rate, and a label (if the filename matches the expected format).

    The filename is expected to be in the format "H10_E10.wav", where H10 is the elevation angle and E10 is the horizontal angle.

    Parameters
    ----------
    data_path : str
        The path to the WAV file to be read.

    Returns
    -------
    left : numpy.ndarray
        The left audio channel.
    right : numpy.ndarray
        The right audio channel.
    sample_rate : int
        The sample rate of the audio file.
    label : list of int
        A list containing the elevation angle and horizontal angle, if the filename matches the expected format. Otherwise, None.
    """
    elev_angle = None
    horiz_angle = None

    sample_rate, data = wavfile.read(data_path)
    left = data[:,0]
    right = data[:,1]
    filename = os.path.basename(data_path)
    primitive_name = None
    if "from_KEMAR" in data_path:
        elev_angle = re.search(r'H([+-]?\d+)',filename)
        horiz_angle = re.search(r'e([+-]?\d+)',filename)
        elev_angle = int(elev_angle.group(1))
        horiz_angle = int(horiz_angle.group(1))
        label = [elev_angle, horiz_angle]
    elif "collected" in data_path: 
        match data_path: 
            case _ if "dtmf" in data_path:
                primitive_name = "dtmf"
            case _ if "sine_16" in data_path:
                primitive_name = "sine"
            case _ if "pluck" in data_path: 
                primitive_name = "pluck"
            case _ if "linear_p5_200_p1_1400" in data_path:
                primitive_name = "linear"
            case _:
                raise ValueError(f"Could not parse primitive name from {filename}")
        m = re.search(r'_(\d+)_(\d+)\.wav$', filename)
        if m is None:
            raise ValueError(f"Could not parse angles from {filename}")
        horiz_angle = int(m.group(2))
        elev_angle = int(m.group(1))
  
        # elev_angle = re.search(...)
        # elev_angle = int(elev_angle.group(1))
        # horiz_angle = re.search(...)
        # horiz_angle = int(horiz_angle.group(1))
        # [elev_angle, horiz_angle] = fxn_transformation(elev_angle,horiz_angle)
        label = [elev_angle, horiz_angle, primitive_name]
    else:
        raise ValueError(f"Unexpected data source for {filename}")
    if elev_angle is None or horiz_angle is None:
        raise ValueError(f"Could not parse elevation/angle from {filename}")
    return left, right, sample_rate, label
## function to perform any data augmentation. ideally we can do this through some .yaml config file
def data_augmentaion(data,config):
    """ augments/modifies data as per config file
    """
    data_augmented = data
    return data_augmented
def horiz_vert_to_axis_angle(horiz_angle,vert_angle):
    angle2y = np.arccos(np.sin(horiz_angle)*np.cos(vert_angle))
    angle_around_y = np.arctan2(np.sin(horiz_angle),np.cos(horiz_angle)*np.cos(vert_angle))
    return angle2y, angle_around_y
def axis_angle_to_horiz_vert(angle2y, angle_around_y): 
    vert_angle = np.arcsin(np.sin(angle2y)*np.sin(angle_around_y))
    horiz_angle = np.arctan2(np.sin(angle2y),np.sin(angle2y)*np.cos(angle_around_y))
    return horiz_angle, vert_angle




def fix_stereo_wav(path_in: str, path_out: str, fs: int = 44100) -> None:
    with open(path_in, "rb") as f:
        blob = f.read()

    # find first 'data' chunk
    idx = blob.find(b"data")
    if idx == -1:
        raise RuntimeError("Couldn't find 'data' chunk")

    data_start = idx + 8  # 4 bytes 'data' + 4 bytes size
    header = blob[:64]    # enough to include data size

    # header's idea of data size (bytes)
    data_chunk_size = int.from_bytes(header[40:44], "little")
    print("data_start:", data_start,
          "file_len:", len(blob),
          "header data_size:", data_chunk_size)

    # if header is at least self-consistent, trust it
    if data_chunk_size > 0 and data_start + data_chunk_size <= len(blob):
        raw_audio = blob[data_start : data_start + data_chunk_size]
    else:
        # fall back to "use everything after data marker"
        raw_audio = blob[data_start:]
        data_chunk_size = len(raw_audio)

    print("raw_audio_len:", len(raw_audio),
          "mod2:", len(raw_audio) % 2,
          "mod4:", len(raw_audio) % 4)

    # interpret as 16-bit signed little-endian
    samples = np.frombuffer(raw_audio, dtype="<i2")

    # if odd number of samples, drop the trailing one
    if samples.size % 2 != 0:
        print("dropping one trailing sample to make stereo frames align")
        samples = samples[:-1]

    stereo = samples.reshape(-1, 2)

    print("stereo shape:", stereo.shape)

    wavfile.write(path_out, fs, stereo)

fix_stereo_wav(
    "/Users/alexdhawan/Desktop/ECE5730/ML-head-transfer-functions/python_training/data-collected/pluck_9_0.wav",
    "pluck_9_0_fixed.wav",
    fs=44100,
)
