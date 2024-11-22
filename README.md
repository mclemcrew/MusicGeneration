# Music Data Tagging Setup Guide

This guide will help you set up your environment for music data tagging on macOS (windows will work, but some of the automation might not be fully there). The system helps analyze audio files, segment them, and create labels that can be edited in Audacity.

## Prerequisites

This guide assumes you have a working knowledge of the command line. If you're not comfortable with the command line, you can use the GUI tools to do the same things. But we'll walk through the full setup here regardless so you'll just need to open the terminal application to follow along.

### 1. Install Homebrew

Homebrew is a package manager for macOS that simplifies the installation of software. We can use this to install the other dependencies.
Let's install Homebrew by running this command in Terminal:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Python via Anaconda

1. Download Anaconda from: https://www.anaconda.com/download
2. Install for macOS (Apple Silicon/Intel depending on your machine)
3. Verify installation by opening Terminal and running:

```
conda --version
```

You may need to close out this terminal session and open a new one to see the changes.

### 3. Install Audacity

1. Install via Homebrew:

```bash
brew install --cask audacity
```

You can also find the download on the [Audacity website](https://www.audacityteam.org/download/).

### 4. Enable Keyboard Accessibility (Required for macOS)

1. Open System Preferences
2. Go to Security & Privacy
3. Select Privacy tab
4. Select Accessibility from the left sidebar
5. Click the lock icon to make changes
6. Ensure Audacity and Terminal are checked
7. Also enable "Control your computer with accessibility features"

You will also need to add for the keyboard itself:

1. Open System Preferences
2. Go to Keyboard
3. Find Keyboard Navigation and make sure it's checked
   ![Keyboard Navigation](keyboard-navigation.png)

## Project Setup

### 1. Clone and Setup Project Structure

Clone the repository to your local machine:

```bash
git clone https://github.com/mclemcrew/MusicGeneration.git
```

### 2. Create and Activate Conda Environment

We'll need to create a conda environment from the yml file. This will install all the dependencies we need for both the labeling and the data tagging portions.

```bash
# Create environment from yml file
conda env create -f ./envs/data-tagging-environment.yml
conda env create -f ./envs/segmenter-environment.yml
```

You will probably need to restart your window after installing the environments for the changes to take effect.

## Usage

### 1. Prepare Audio Files

1. Place all your audio files (MP3 or WAV) in the `./audio` directory. Ravi will provide you the link to the full corpus. I recommend downloading the files to your local machine first and then adding them to the `./audio` directory. Please make sure to note which ones you've downloaded so we know how many you are in the process of tagging.
2. Supported formats: `.mp3`, `.wav`

### 2. Run Music Segmentation

1. Navigate to and open `notebooks/music-segmentation.ipynb`
2. Make sure to select the `segmenter` environment in the top right corner of the notebook ![Picture of Segmenter Environment selected in the Jupyter Notebook](segmenter.png)
3. Run all cells in the notebook

The segmentation process will:

- Analyze each audio file
- Generate label files in the `./labels` directory
- Create structural segmentation (intro, verse, chorus, etc.)

### 3. Run Data Tagging Tool

1. Open Terminal
2. Navigate to your project directory
3. Activate the `data-tagging` environment:

```bash
conda activate data-tagging
```

4. Run:

```bash
python scripts/checks.py
```

### 4. Using the Data Tagging Interface

1. You'll see a list of audio files with their processing status
2. Choose an action:
   - 1: Process Audio File (Edit Labels & Description)
   - 2: Edit Labels Only
   - 3: Edit Description Only
3. When editing labels in Audacity:
   - Wait for the file to open
   - Edit the labels as needed
   - Return to the terminal to continue
4. For descriptions:
   - Enter a description (i.e. "EDM track with a heavy dance bass and start synth leads that build up to a big drop in the middle of the piece")
   - Add genre tags as comma-separated values (i.e. "EDM, Dance, House")

## Important Notes

1. The system requires proper file permissions to:

   - Read from the `./audio` directory
   - Write to the `./labels` and `./descriptions` directories
   - Control Audacity via AppleScript

2. If you encounter permission issues:

   - Check folder permissions
   - Verify Accessibility settings
   - Ensure Audacity has proper permissions

3. For audio files that fail to process:
   - Verify the file format is supported
   - Check if the file is corrupted
   - Try re-encoding the file using a tool like `ffmpeg`

## Troubleshooting

If you encounter the error "can't sync to MPEG frame":

1. The MP3 file might be corrupted
2. Try re-encoding the file:

```bash
brew install ffmpeg
ffmpeg -i input.mp3 -acodec libmp3lame -q:a 2 output.mp3
```

For AppleScript permission issues:

1. Remove and re-add Terminal/Audacity in Security & Privacy
2. Restart both applications
3. Ensure both applications are not running when adding permissions

## Reference Documentation

For more details on the implementation, see:

- Music segmentation notebook: `notebooks/music-segmentation.ipynb` (lines 1-314)
- Audio processing: `notebooks/audio-to-midi.ipynb` (lines 1-121)
- Environment configuration: `envs/audio-to-midi-environment.yml`
