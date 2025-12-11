import matplotlib.pyplot as plt
import numpy as np
ELEVATION_STEPS = 10        
AZIMUTH_STEPS = 10 
def plot_ild(ILD_f_t, ILD_t, t_idx, fs):
    """
    ILD_f_t : 2D array ILD(f, t)
    ILD_t   : 1D array ILD(t)
    t_idx   : sample index of frame centers
    fs      : sampling rate
    """
    # Time axis in seconds
    t_sec = t_idx / fs

    # --- FIGURE 1: ILD(f, t) heatmap ---
    plt.figure(figsize=(10, 4))
    plt.imshow(
        ILD_f_t,
        origin="lower",
        aspect="auto",
        cmap="bwr",
        vmin=-20,
        vmax=20,
    )
    plt.colorbar(label="ILD (dB)")
    plt.xlabel("Frame index")
    plt.ylabel("Frequency bin")
    plt.title("ILD(f, t)")

    # --- FIGURE 2: Broadband ILD(t) ---
    plt.figure(figsize=(10, 3))
    plt.plot(t_sec, ILD_t)
    plt.axhline(0, color='k', linewidth=0.8)
    plt.xlabel("Time (s)")
    plt.ylabel("ILD (dB)")
    plt.title("Broadband ILD over time")
    plt.grid(True, alpha=0.3)
    plt.show()



def decode_predictions(preds):
    decoded = []
    for p in preds:
        e_sin, e_cos, az_sin, az_cos = p
        e_angle = np.arctan2(e_sin, e_cos)
        az_angle = np.arctan2(az_sin, az_cos)
        if e_angle < 0: e_angle += 2 * np.pi
        if az_angle < 0: az_angle += 2 * np.pi
        
        e_idx = (e_angle / (2 * np.pi)) * ELEVATION_STEPS
        az_idx = (az_angle / (2 * np.pi)) * AZIMUTH_STEPS
        decoded.append([e_idx, az_idx])
    return np.array(decoded)

def plot_results(model, X_test, y_test):
    print("\n--- Generating Predictions ---")
    preds = model.predict(X_test)
    dec_preds = decode_predictions(preds)
    dec_truth = decode_predictions(y_test)
    
    # Azimuth
    plt.figure(figsize=(10, 5))
    plt.scatter(dec_truth[:, 1], dec_preds[:, 1], alpha=0.5, c='darkgreen')
    plt.plot([0, AZIMUTH_STEPS], [0, AZIMUTH_STEPS], 'r--', label='Ideal')
    plt.title('Azimuth Validation')
    plt.xlabel('True Index'); plt.ylabel('Predicted Index')
    plt.show()

    # Elevation
    plt.figure(figsize=(10, 5))
    plt.scatter(dec_truth[:, 0], dec_preds[:, 0], alpha=0.5, c='darkgreen')
    plt.plot([0, ELEVATION_STEPS], [0, ELEVATION_STEPS], 'r--', label='Ideal')
    plt.title('Elevation Validation')
    plt.xlabel('True Index'); plt.ylabel('Predicted Index')
    plt.show()

def plot_stereo_spectrogram(audio_data, fs, nperseg=1024, noverlap=512):
    """
    Generates and plots spectrograms for an Nx2 audio array.
    
    Parameters:
    - audio_data: Nx2 numpy array (stereo audio)
    - fs: Sampling frequency in Hz
    - nperseg: Length of each segment (window size)
    - noverlap: Number of points to overlap between segments
    """
    
    # Check input shape
    if audio_data.ndim != 2 or audio_data.shape[1] != 2:
        raise ValueError("Input must be an Nx2 numpy array.")

    # Separation of channels
    left_channel = audio_data[:, 0]
    right_channel = audio_data[:, 1]
    
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # --- Process Left Channel ---
    f_l, t_l, Sxx_l = signal.spectrogram(left_channel, fs, nperseg=nperseg, noverlap=noverlap)
    # Convert to dB scale for better visualization
    Sxx_l_db = 10 * np.log10(Sxx_l + 1e-10) # 1e-10 added to avoid log(0)
    
    im1 = ax1.pcolormesh(t_l, f_l, Sxx_l_db, shading='gouraud', cmap='inferno')
    ax1.set_ylabel('Frequency [Hz]')
    ax1.set_title('Left Channel Spectrogram')
    fig.colorbar(im1, ax=ax1, format='%+2.0f dB')

    # --- Process Right Channel ---
    f_r, t_r, Sxx_r = signal.spectrogram(right_channel, fs, nperseg=nperseg, noverlap=noverlap)
    Sxx_r_db = 10 * np.log10(Sxx_r + 1e-10)
    
    im2 = ax2.pcolormesh(t_r, f_r, Sxx_r_db, shading='gouraud', cmap='inferno')
    ax2.set_ylabel('Frequency [Hz]')
    ax2.set_xlabel('Time [sec]')
    ax2.set_title('Right Channel Spectrogram')
    fig.colorbar(im2, ax=ax2, format='%+2.0f dB')

    plt.tight_layout()
    plt.show()
