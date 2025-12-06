## extracts relevant features for training net


## Import statements
import numpy as np 
from scipy.io import wavfile
from scipy.signal import stft
import pdb

def compute_ILD(left, right, fs,  n_fft=None):
    """
    Compute Inter-aural Level Difference (ILD) from two channels of audio data.

    Parameters
    ----------
    left : numpy array
        Left channel of audio data
    right : numpy array
        Right channel of audio data
    fs : int
        Sampling rate of audio data
    nfft : int, optional
        Number of samples to take for STFT, defaults to len(left)

    Returns
    -------
    f : numpy array
        Frequency axis
    ILD_f : numpy array
        ILD(f) values (Left over Right)
    """
    left = np.asarray(left, dtype=np.float32)
    right = np.asarray(right, dtype=np.float32)

    # Shared normalization to preserve ILD
    # (or comment this out entirely if you want raw levels)
    max_val = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-12)
    left = left / max_val
    right = right / max_val

    #window to reuce leakage from start/end 
    window = np.hanning(len(left)).astype(np.float32)


    # STFT
    if n_fft is None:
        n_fft = len(left)
    L_fft = np.fft.rfft(left*window,n =n_fft)
    R_fft = np.fft.rfft(right*window,n =n_fft)

    L_mag = np.abs(L_fft)
    R_mag = np.abs(R_fft)
    eps = 1e-12

    # ILD(f, t)
    ILD_f = 20.0 * np.log10((L_mag + eps) / (R_mag + eps))

    # frequency axis
    f = np.fft.rfftfreq(n_fft, d=1.0/fs)

    return f, ILD_f


def compute_ITD(left, right, fs, max_ITD_spec=0.001):
    """
    Compute Interaural Time Difference (ITD) from two channels of audio data.

    Parameters
    ----------
    left : numpy array
        Left channel of audio data
    right : numpy array
        Right channel of audio data
    fs : int
        Sampling rate of audio data
    max_ITD_spec : float, optional
        Maximum ITD (in seconds) to consider

    Returns
    -------
    itd_sec : float
        Interaural time difference (in seconds)
    itd_samples : int
        Interaural time difference (in samples)
    """
    left = np.asarray(left, dtype=np.float32)
    right = np.asarray(right, dtype=np.float32)
    assert left.shape == right.shape

    # normalize signals (shared)
    max_val = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-12)
    left = left / max_val
    right = right / max_val

    N = len(left)
    n_fft = 1
    while n_fft < 2 * N:
        n_fft *= 2

    L = np.zeros(n_fft, dtype=np.float32)
    R = np.zeros(n_fft, dtype=np.float32)
    L[:N] = left
    R[:N] = right

    # FFT
    X_L = np.fft.fft(L)
    X_R = np.fft.fft(R)

    # cross-power spectrum and PHAT
    cross = X_L * np.conj(X_R)
    cross /= (np.abs(cross) + 1e-12)

    # GCC-PHAT correlation
    corr = np.fft.ifft(cross).real
    corr = np.fft.fftshift(corr)

    lags = np.arange(-n_fft // 2, n_fft // 2)
    max_lag = int(max_ITD_spec * fs)

    valid = np.where((lags >= -max_lag) & (lags <= max_lag))[0]
    corr_valid = corr[valid]
    lags_valid = lags[valid]

    best_idx = np.argmax(corr_valid)  # peak
    itd_samples = int(lags_valid[best_idx])
    itd_sec = itd_samples / fs

    return itd_sec, itd_samples
    # compute IT
def compute_IPD(left,right): 
    """ Computes inter-aural phase difference for a pair of audio channels

    Args:
        left: left channel audio signal
        right: right channel audio signal

    Returns:
        ipd: inter-aural phase difference
    """
    pass
def compute_spectral_features(left,right,fs,n_fft=None,bands_hz = None):
    left = np.asarray(left, dtype=np.float32)
    right = np.asarray(right, dtype=np.float32)
    assert left.shape == right.shape
    N = len(left)
    # Shared normalization
    max_val = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-12)
    left = left / max_val
    right = right / max_val

    # Choose FFT size
    if n_fft is None:
        n_fft = 1
        while n_fft < N:
            n_fft *= 2
    window = np.hanning(N).astype(np.float32)
        # Zero-pad and window
    L = np.zeros(n_fft, dtype=np.float32)
    R = np.zeros(n_fft, dtype=np.float32)
    L[:N] = left * window
    R[:N] = right * window

    L_fft = np.fft.rfft(L)
    R_fft = np.fft.rfft(R)
    # Frequency axis
    f = np.fft.rfftfreq(n_fft, d=1.0/fs)

    # Power spectra
    P_L = (L_fft.real**2 + L_fft.imag**2)
    P_R = (R_fft.real**2 + R_fft.imag**2)

    eps = 1e-12
    # Normalize total power to 1 (per ear)
    P_L /= (P_L.sum() + eps)
    P_R /= (P_R.sum() + eps)

    # Default bands (tweak later as needed)
    if bands_hz is None:
        bands_hz = []
        band_low = 250
        band_hi = 20000
        num_bands = 10
        # Create linearly spaced boundaries
        edges = np.logspace(np.log10(band_low), np.log10(band_hi), num_bands+1)

        # Convert edges into interval tuples
        bands_hz = [(edges[i], edges[i+1]) for i in range(num_bands)] 
    band_energies_L = []
    band_energies_R = []

    for (f_lo, f_hi) in bands_hz:
        idx = np.where((f >= f_lo) & (f < f_hi))[0]
        if idx.size == 0:
            band_energies_L.append(0.0)
            band_energies_R.append(0.0)
        else:
            # Sum normalized power in this band
            eL = P_L[idx].sum()
            eR = P_R[idx].sum()
            band_energies_L.append(eL)
            band_energies_R.append(eR)

    band_energies_L = np.array(band_energies_L, dtype=np.float32)
    band_energies_R = np.array(band_energies_R, dtype=np.float32)

    # Optional: log-compress; uncomment if you prefer log scale
    # band_energies_L = np.log10(band_energies_L + eps)
    # band_energies_R = np.log10(band_energies_R + eps)

    # Spectral centroids
    # c = sum(f * P) / sum(P); but sum(P) = 1 due to normalization
    centroid_L = float((f * P_L).sum())
    centroid_R = float((f * P_R).sum())

    spec_feat = np.concatenate([
        band_energies_L,
        band_energies_R,
        np.array([centroid_L, centroid_R], dtype=np.float32)
    ])
    # spec_feat = np.concatenate([
    #     np.array([centroid_L, centroid_R], dtype=np.float32)
    # ])
    meta = {
        "bands_hz": bands_hz,
        "order": {
            "band_energies_left": (0, len(band_energies_L)),
            "band_energies_right": (len(band_energies_L),
                                    2 * len(band_energies_L)),
            "centroid_left_idx": 2 * len(band_energies_L),
            "centroid_right_idx": 2 * len(band_energies_L) + 1,
        }
    }

    return spec_feat, meta
