## Data preprocessing code 
import numpy as np 
import pandas as pd
from scipy.io import wavfile
import os
from pathlib import Path
import pdb
import re
## Function to take .wav file name and data and reformat to convenient format
def reformat_wav(data_path): 
    """
    Reformat a .wav file name and data to a convenient format.

    Parameters
    ----------
    data_raw : .wav file
        Tuple containing .wav file name and data.

    Returns
    -------
    data_processed :
        ____ containing .wav file name and data in a convenient format.
    """
    elev_angle = None
    horiz_angle = None

    sample_rate, data = wavfile.read(data_path)
    left = data[:,0]
    right = data[:,1]
    ## generate 2 element list for angle: (planary, vertical)
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

# fix_stereo_wav(
#     "/Users/alexdhawan/Desktop/ECE5730/ML-head-transfer-functions/python_training/data-collected/pluck_9_0.wav",
#     "pluck_9_0_fixed.wav",
#     fs=44100,
# )
