## extracts relevant features for training net


## Import statements
import numpy as np 
from scipy.io import wavfile
from scipy.signal import stft
import pdb
def compute_ILD(left,right):
    """ computes inter-aural level difference for a pair of audio channels 

    Args:
        left: left channel audio signal
        right: right channel audio signal

    Returns:
        ild: inter-aural level difference
    """ 
    left = left.astype(np.float32)
    right = right.astype(np.float32)
    # normalize signals
    left /= np.max(np.abs(left))
    right /= np.max(np.abs(right))
    #compute STFT for each channel
    #TODO need to make fs adjustable and think harder about how to set nperseg
    f,t,L_stft = stft(left, fs=44100,nperseg=88)
    _,_,R_stft = stft(right, fs=44100,nperseg=88)
    # pdb.set_trace()
    #3. compute ILD
    L_mag = np.abs(L_stft)
    R_mag = np.abs(R_stft)
    eps = 1e-12
    # pdb.set_trace()
    ILD = 20* np.log10((L_mag+eps)/ (R_mag+eps))
    ILD_time = ILD.mean(axis=0)
    t_samples = (t*44100).astype(int)
    t_samples = np.clip(t_samples,0,len(left)-1)
    return ILD, ILD_time, t_samples

def compute_ITD(left,right):
    """ Computes inter-aural time difference for a pair of audio channels

    Args:
        left: left channel audio signal
        right: right channel audio signal

    Returns:
        itd: inter-aural time difference
    """
    pass
def compute_IPD(left,right): 
    """ Computes inter-aural phase difference for a pair of audio channels

    Args:
        left: left channel audio signal
        right: right channel audio signal

    Returns:
        ipd: inter-aural phase difference
    """
    pass
