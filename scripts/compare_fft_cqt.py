"""
Compare FFT (STFT) and Constant-Q Transform (CQT) spectrograms.

This script loads an audio file, computes both FFT-based and CQT spectrograms,
and displays them side-by-side to visualize the differences between linear
and logarithmic frequency representations.
"""

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np

# Configuration
AUDIO_FILE = '/Users/mclem/Desktop/MusicGeneration/audio/jandl.wav'
DURATION = 5.0  # seconds
SR = 22050  # sample rate

def main():
    print(f"Loading audio file: {AUDIO_FILE}")
    print(f"Duration: {DURATION} seconds")

    # Load audio file (first 10 seconds)
    y, sr = librosa.load(AUDIO_FILE, duration=DURATION, sr=SR)
    print(f"Loaded {len(y)} samples at {sr} Hz")

    # Compute FFT-based spectrogram (STFT)
    print("\nComputing STFT (FFT-based spectrogram)...")
    D_stft = librosa.stft(y)
    S_stft_db = librosa.amplitude_to_db(np.abs(D_stft), ref=np.max)

    # Compute Constant-Q Transform spectrogram
    print("Computing CQT (Constant-Q Transform spectrogram)...")
    C_cqt = librosa.cqt(y, sr=sr, hop_length=512)
    S_cqt_db = librosa.amplitude_to_db(np.abs(C_cqt), ref=np.max)

    # Create side-by-side visualization
    print("\nCreating visualization...")
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # Plot STFT
    img1 = librosa.display.specshow(
        S_stft_db,
        sr=sr,
        x_axis='time',
        y_axis='hz',
        ax=axes[0],
        cmap='viridis'
    )
    axes[0].set_title('FFT-Based Spectrogram (STFT) - Linear Frequency Scale',
                      fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Frequency (Hz)', fontsize=12)
    fig.colorbar(img1, ax=axes[0], format='%+2.0f dB')

    # Plot CQT
    img2 = librosa.display.specshow(
        S_cqt_db,
        sr=sr,
        x_axis='time',
        y_axis='cqt_hz',
        ax=axes[1],
        cmap='viridis'
    )
    axes[1].set_title('Constant-Q Transform (CQT) - Logarithmic Frequency Scale',
                      fontsize=14, fontweight='bold')
    axes[1].set_ylabel('Frequency (Hz)', fontsize=12)
    axes[1].set_xlabel('Time (seconds)', fontsize=12)
    fig.colorbar(img2, ax=axes[1], format='%+2.0f dB')

    # Add explanation text
    fig.text(0.5, 0.02,
             'Key Difference: STFT uses linear frequency spacing (equal Hz between bins), '
             'while CQT uses logarithmic spacing (aligned with musical notes/octaves)',
             ha='center', fontsize=10, style='italic', wrap=True)

    plt.tight_layout(rect=[0, 0.03, 1, 1])

    # Save and show
    output_file = '/Users/mclem/Desktop/MusicGeneration/scripts/fft_vs_cqt_comparison.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nVisualization saved to: {output_file}")

    plt.show()
    print("\nDone!")

if __name__ == "__main__":
    main()
