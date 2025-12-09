## extracts relevant features for training net


## Import statements
import numpy as np 
from scipy.io import wavfile
from scipy.signal import stft,butter, filtfilt,correlate 
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

    # zero-mean
    left = left - left.mean()
    right = right - right.mean()

    # normalized cross-correlation (so amplitude differences don't matter)
    corr = correlate(right, left, mode="full")
    denom = (np.linalg.norm(left) * np.linalg.norm(right) + 1e-12)
    corr = corr / denom

    # lag axis: negative = right leads left, positive = right lags left
    N = len(left)
    lags = np.arange(-N + 1, N)

    # restrict to plausible ITD window
    max_lag = int(max_ITD_spec * fs)
    mask = (lags >= -max_lag) & (lags <= max_lag)
    corr_valid = corr[mask]
    lags_valid = lags[mask]

    # best lag = argmax correlation
    best_idx = np.argmax(corr_valid)
    itd_samples = int(lags_valid[best_idx])
    itd_sec = itd_samples / float(fs)

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
import numpy as np

def extract_beep_window(x, fs, win_len_sec=0.01, margin_sec=0.003):
    x = np.asarray(x, dtype=np.float32)
    env = np.abs(x)
    thresh = 0.3 * np.max(env)
    idx = np.where(env > thresh)[0]
    if len(idx) == 0:
        return x  # fallback
    first = idx[0]
    win_len = int(win_len_sec * fs)
    margin = int(margin_sec * fs)
    start = max(first - margin, 0)
    end = min(start + win_len, len(x))
    return x[start:end]

def itd_corr(left, right, fs, max_ITD_spec=0.001):
    """
    ITD in seconds and samples, using plain time-domain correlation
    over a ±max_ITD_spec window.
    """
    left = np.asarray(left, dtype=np.float32)
    right = np.asarray(right, dtype=np.float32)
    assert left.shape == right.shape

    # normalize to common scale
    max_val = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-12)
    left /= max_val
    right /= max_val

    N = len(left)
    max_lag = int(max_ITD_spec * fs)   # e.g. 44 samples for 1 ms @ 44.1k
    best_lag = 0
    best_val = -np.inf

    # precompute energies if you later want normalized correlation;
    # for now simple dot product is fine
    for k in range(-max_lag, max_lag + 1):
        if k < 0:
            x = left[-k:N]      # left shifted right
            y = right[0:N+k]
        else:
            x = left[0:N-k]
            y = right[k:N]
        if len(x) == 0:
            continue
        c = np.dot(x, y)
        if c > best_val:
            best_val = c
            best_lag = k

    itd_samples = best_lag
    itd_sec = itd_samples / fs
    return itd_sec, itd_samples
