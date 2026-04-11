# My Video Player Style

A minimal, TikTok-style media player built in Python and PyQt6. It elegantly plays your local videos and music with automatic aspect ratio fitting and immersive fullscreen controls.

## Features
- **TikTok-Style scrolling**: Instantly navigate through your media library using your mouse wheel.
- **Auto-Fit Display**: Automatically resizes the window to match each video's aspect ratio (targets a sleek 600px height by default).
- **Immersive Fullscreen**: View your media without distractions by toggling fullscreen mode.
- **Keyboard Mastery**: Full control via keyboard (Up/Down skipping, Spacebar pause, Left/Right seeking by 5% of the current video length, rounded up to the next whole second).
- **Universal Media Support**: Plays `.mp4`, `.avi`, `.mkv`, `.mp3`, `.wav`, `.m4a`, `.mov`, and `.flac`.
- **Clickable Progress Bar**: Instantly seek through the timeline by clicking anywhere on the track.
- **Click to Play/Pause**: Click the video area to toggle playback.
- **Persistent Memory**: Remembers your preferred media folder across sessions.

## Developer Installation

### Prerequisites
Make sure you have Python installed on your system.

### Setup Environment
1. Open Command Prompt and navigate to the project directory:
   ```cmd
   cd c:\_Data\_Personal_Project\Desktop\myPlayer
   ```
2. Install the necessary Python packages:
   ```cmd
   pip install -r requirements.txt
   ```

### Running the App
Open the app any time directly through Python:
```cmd
python main.py
```

## Application Controls
- **Up Arrow** / **`Mouse Scroll Up`**: Previous video/song.
- **Down Arrow** / **`Mouse Scroll Down`**: Next video/song.
- **Left Arrow**: Rewind by 5% of the current media length, rounded up to the next whole second.
- **Right Arrow**: Fast-forward by 5% of the current media length, rounded up to the next whole second.
- **Spacebar**: Play / Pause playback.
- **Single Click Video**: Play / Pause playback.
- **`F` Key** / **`Double-Click Video`**: Toggle Fullscreen.
- **`Esc` Key**: Exit Fullscreen.

## Deployment (Creating an `.exe` version)

If you'd like to create a standalone executable so you don't have to launch it via Command Prompt every time, follow these steps:

1. Install the PyInstaller compiler package:
   ```cmd
   pip install pyinstaller
   ```

2. Run the build command (the `--windowed` flag hides the background console while `--name` sets the app title):
   ```cmd
   pyinstaller --name "My Video Player Style" --windowed --onefile main.py
   ```

3. Once completed, navigate into the `dist` folder to find your generated `My Video Player Style.exe` application! You can make a shortcut of it directly to your Desktop.
