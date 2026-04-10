# My Video Player Style

A minimal, TikTok-style media player built in Python and PyQt6. It elegantly plays your local videos and music while supporting integrated YouTube Music search streams!

## Features
- **TikTok-Style Scrolling**: Instantly scroll through your media library using your mouse wheel.
- **Keyboard Shortcuts**: Control playback without the mouse (Up/Down skipping, Spacebar pause, Left/Right seeking).
- **Universal Media Support**: Plays `.mp4`, `.avi`, `.mkv`, `.mp3`, `.wav`, `.m4a`, and `.flac`.
- **YouTube Music Integration**: Search for any song on YouTube Music and magically play the audio stream directly within the app.
- **Clickable Progress Bar**: Instantly seek through the timeline by clicking anywhere on the track.
- **Auto-Memory**: Remembers your designated media folder across sessions.

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
- **Up Arrow** / **`Mouse Scroll Up`**: Skip to the previous video/song.
- **Down Arrow** / **`Mouse Scroll Down`**: Skip to the next video/song.
- **Left Arrow**: Rewind 30 seconds.
- **Right Arrow**: Fast-forward 30 seconds.
- **Spacebar**: Play / Pause playback.

## Deployment (Creating an `.exe` version)

If you'd like to create a standalone executable so you don't have to launch it via Command Prompt every time, follow these steps:

1. Install the PyInstaller compiler package:
   ```cmd
   pip install pyinstaller
   ```

2. Run the build command (the `--windowed` flag hides the messy background console while `--name` sets the app title):
   ```cmd
   pyinstaller --name "My Video Player Style" --windowed --onefile main.py
   ```

3. Once completed, navigate into the incredibly fresh `dist` folder to find your generated `My Video Player Style.exe` application! You can make a shortcut of it directly to your Desktop.
