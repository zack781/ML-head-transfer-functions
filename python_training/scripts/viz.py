import matplotlib.pyplot as plt
import numpy as np

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
