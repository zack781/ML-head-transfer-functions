import os
import glob
import re
import numpy as np
import librosa
from scipy.io import wavfile

# --- CONFIGURATION DEFAULTS ---
SAMPLE_RATE = 44100
CHUNK_DURATION_MS = 1100  
N_MELS = 96               
SILENCE_THRESHOLD = 0.01  
AZIMUTH_STEPS = 10        
ELEVATION_STEPS = 10      

class AudioSlicer:
    def __init__(self, sample_rate=SAMPLE_RATE, chunk_ms=CHUNK_DURATION_MS, n_mels=N_MELS, silence_thresh=SILENCE_THRESHOLD):
        self.sr = sample_rate
        self.chunk_len = int(sample_rate * (chunk_ms / 1000))
        self.n_mels = n_mels
        self.n_fft = 4096
        self.hop_length = 256 
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

def load_and_split_dataset(data_dir):
    slicer = AudioSlicer()
    files = glob.glob(os.path.join(data_dir, "*.wav"))
    
    X_train_all, y_train_all = [], []
    X_test_all, y_test_all = [], []
    
    # Matches: "_0_0.wav", "_0_0 copy.wav", etc.
    pattern = re.compile(r'_(\d+)_(\d+)(?:.*)?\.wav$')
    
    print(f"Found {len(files)} files. Parsing...")
    
    for f in files:
        match = pattern.search(f)
        if match:
            elev_idx = float(match.group(1))
            az_idx = float(match.group(2))
            
            elev_theta = (elev_idx / ELEVATION_STEPS) * (2 * np.pi)
            az_theta = (az_idx / AZIMUTH_STEPS) * (2 * np.pi)
            
            label_vector = [
                np.sin(elev_theta), np.cos(elev_theta), 
                np.sin(az_theta), np.cos(az_theta)
            ] 
            
            Xt, yt, Xv, yv = slicer.process_and_split(f, label_vector)
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
    sample_rate, data = wavfile.read(data_path)
    left = data[:,0]
    right = data[:,1]
    filename = os.path.basename(data_path)
    
    m = re.search(r'_(\d+)_(\d+)\.wav$', filename)
    if m:
        horiz_angle = int(m.group(2))
        elev_angle = int(m.group(1))
        label = [elev_angle, horiz_angle]
        return left, right, sample_rate, label
    return left, right, sample_rate, None