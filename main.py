import sys
import os
import random
import json
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QFileDialog, QLabel, QLineEdit, QHBoxLayout,
                             QSlider)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtGui import QIcon




CONFIG_FILE = "config.json"
SUPPORTED_EXT = ['.mp4', '.avi', '.mkv', '.mp3', '.wav', '.flac', '.m4a', '.mov']




class VideoWidget(QVideoWidget):
    doubleClicked = pyqtSignal()
    
    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Calculate value directly from the X click position
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.pos().x()) / self.width()
            self.setValue(int(val))
            self.sliderMoved.emit(int(val))
        # Keep base behavior (like drag to slide)
        super().mousePressEvent(event)


class TikTokPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Video Player Style")
        self.resize(520, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #111; }
            QWidget { color: #fff; font-family: Arial; }
            QLineEdit { 
                background-color: #333; border: 1px solid #555; 
                padding: 10px; border-radius: 6px; 
            }
            QPushButton { 
                background-color: #ff0050; 
                border: none; padding: 10px; 
                border-radius: 6px; font-weight: bold; color: white;
            }
            QPushButton:hover { background-color: #d00040; }
            QPushButton:disabled { background-color: #555; }
            
            /* Custom Seek Bar Styling */
            QSlider::groove:horizontal {
                border: 1px solid #444;
                height: 6px;
                background: #333;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #ff0050;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
        """)

        self.playlist = []
        self.current_idx = -1

        # Central Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # --- TOP CONTROLS ---
        self.ui_container = QWidget()
        self.ui_container.setStyleSheet("background-color: #222; border-top: 2px solid #ff0050;")
        self.ui_layout = QVBoxLayout(self.ui_container)
        self.ui_layout.setContentsMargins(10, 15, 10, 15)
        self.ui_layout.setSpacing(12)
        
        self.btn_folder = QPushButton("📁 Select Media Folder")
        self.btn_folder.setToolTip("Select a folder to auto-load media")
        self.btn_folder.clicked.connect(self.select_folder)
        self.ui_layout.addWidget(self.btn_folder)

        # --- SEEK BAR ---
        self.seek_layout = QHBoxLayout()
        
        self.seek_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderMoved.connect(self.set_position)
        self.seek_layout.addWidget(self.seek_slider)
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #ccc; font-size: 13px; font-weight: bold; margin-left: 8px;")
        self.seek_layout.addWidget(self.time_label)
        
        self.ui_layout.addLayout(self.seek_layout)

        # Info Label (Now Playing, Status)
        self.info_label = QLabel("Ready. Click 'Select Media Folder' to start.")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #aaa;")
        self.ui_layout.addWidget(self.info_label)
        
        # UI container will be added later at the bottom

        # --- VIDEO PLAYER AREA ---
        self.video_container = QWidget()
        self.video_container.setStyleSheet("background-color: #000;")
        self.video_layout = QVBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_widget = VideoWidget()
        self.video_widget.doubleClicked.connect(self.toggle_fullscreen)
        self.video_layout.addWidget(self.video_widget)
        
        self.layout.addWidget(self.video_container, stretch=1)
        self.layout.addWidget(self.ui_container)
        
        # Multimedia initialization
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        
        # Auto-fit connection: resize window when video size is detected
        self.video_widget.videoSink().videoSizeChanged.connect(self.resize_to_video)
        
        # Focus policy so we can capture keyboard events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.video_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Try loading config immediately
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    folder = config.get("folder", "")
                    if folder and os.path.exists(folder):
                        self.scan_folder(folder)
            except Exception as e:
                print("Failed to load config:", e)

    def save_config(self, folder):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"folder": folder}, f)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Media Folder")
        if folder:
            self.save_config(folder)
            self.scan_folder(folder)
            self.setFocus() # return focus to main window to detect keys

    def scan_folder(self, folder):
        self.info_label.setText(f"Scanning folder...")
        self.playlist = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if any(file.lower().endswith(ext) for ext in SUPPORTED_EXT):
                    self.playlist.append(os.path.join(root, file))
        
        # Reshuffle randomly
        random.shuffle(self.playlist)
        if self.playlist:
            self.current_idx = 0
            self.play_current()
        else:
            self.info_label.setText("No media found in selected folder.")

    def play_current(self):
        if self.playlist and 0 <= self.current_idx < len(self.playlist):
            media_path = self.playlist[self.current_idx]
            # Set local file source
            self.player.setSource(QUrl.fromLocalFile(media_path))
            name = os.path.basename(media_path)
                
            self.info_label.setText(f"Playing: {name}\nPress UP/DOWN keys to navigate!")
            self.player.play()
            
            # Request focus back so keyboard arrows aren't hijacked
            self.setFocus()

    def play_next(self):
        if self.playlist:
            self.current_idx = (self.current_idx + 1) % len(self.playlist)
            self.play_current()

    def play_prev(self):
        if self.playlist:
            self.current_idx = (self.current_idx - 1) % len(self.playlist)
            self.play_current()

    def on_media_status_changed(self, status):
        # Auto-play next on end
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_next()

    def format_time(self, ms):
        s = round(ms / 1000)
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}"

    def resize_to_video(self, size=None):
        if size is None:
            size = self.video_widget.videoSink().videoSize()
            
        if size.isEmpty() or self.isFullScreen():
            return
            
        # Get target dimensions while keeping a reasonable height
        target_height = 600
        aspect_ratio = size.width() / size.height()
        target_width = int(target_height * aspect_ratio)
        
        # Ensure it's not too wide or too narrow
        target_width = max(300, min(target_width, 1200))
        
        # Account for the UI container height at the bottom
        ui_height = self.ui_container.sizeHint().height()
        self.resize(target_width, target_height + ui_height)
        
        # Center the window on the screen if it was just loaded
        frame = self.frameGeometry()
        center = self.screen().availableGeometry().center()
        frame.moveCenter(center)
        self.move(frame.topLeft())

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.ui_container.show()
        else:
            self.showFullScreen()
            self.ui_container.hide() # Hide controls in fullscreen for TikTok feel

    def position_changed(self, position):
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(position)
        
        current_time = self.format_time(position)
        total_time = self.format_time(self.player.duration())
        self.time_label.setText(f"{current_time} / {total_time}")

    def duration_changed(self, duration):
        self.seek_slider.setRange(0, duration)

    def set_position(self, position):
        self.player.setPosition(position)

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        if angle < 0:
            self.play_next()
        elif angle > 0:
            self.play_prev()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up:
            self.play_prev()
        elif event.key() == Qt.Key.Key_Down:
            self.play_next()
        elif event.key() == Qt.Key.Key_Space:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            else:
                self.player.play()
        elif event.key() == Qt.Key.Key_Left:
            new_pos = max(0, self.player.position() - 30000)
            self.player.setPosition(new_pos)
        elif event.key() == Qt.Key.Key_Right:
            new_pos = min(self.player.duration(), self.player.position() + 30000)
            self.player.setPosition(new_pos)
        elif event.key() == Qt.Key.Key_F:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = TikTokPlayer()
    player.show()
    sys.exit(app.exec())
