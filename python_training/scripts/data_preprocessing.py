## Data preprocessing code 
import numpy as np 
import pandas as pd


## Function to take .wav file name and data and reformat to convenient format
def reformat_wav(data_raw): 
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
    data_processed = data_raw
    
    return data_processed
## function to perform any data augmentation. ideally we can do this through some .yaml config file
def data_augmentation(data,config):
    """ augments/modifies data as per config file
    """
    data_augmented = data
    return data_augmented