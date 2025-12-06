## Data preprocessing code 
import numpy as np 
import pandas as pd
from scipy.io import wavfile
import os
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
    sample_rate, data = wavfile.read(data_path)
    left = data[:,0]
    right = data[:,1]
    ## generate 2 element list for angle: (planary, vertical)
    filename = os.path.basename(data_path)
    if "from_KEMAR" in data_path:
        elev_angle = re.search(r'H([+-]?\d+)',filename)
        horiz_angle = re.search(r'e([+-]?\d+)',filename)
    if elev_angle is None or horiz_angle is None:
        raise ValueError(f"Could not parse elevation/angle from {filename}")
    elev_angle = int(elev_angle.group(1))
    horiz_angle = int(horiz_angle.group(1))
    label = [elev_angle, horiz_angle]
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

