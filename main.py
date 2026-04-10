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

import yt_dlp
from ytmusicapi import YTMusic

CONFIG_FILE = "config.json"
SUPPORTED_EXT = ['.mp4', '.avi', '.mkv', '.mp3', '.wav', '.flac', '.m4a', '.mov']

class YTSearchThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query
        self.ytmusic = YTMusic()

    def run(self):
        try:
            results = self.ytmusic.search(self.query, filter="songs")
            if results:
                video_id = results[0]['videoId']
                url = f"https://music.youtube.com/watch?v={video_id}"
                
                ydl_opts = {
                    'format': 'bestaudio/best', 
                    'quiet': True, 
                    'skip_download': True
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    self.finished.emit(info.get('url', ''))
            else:
                self.finished.emit("")
        except Exception as e:
            print("YT Search Error:", e)
            self.finished.emit("")


class TikTokPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikTok-Style Media Player")
        self.resize(500, 800)
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
        self.ui_container.setStyleSheet("background-color: #222; border-bottom: 2px solid #ff0050;")
        self.ui_layout = QVBoxLayout(self.ui_container)
        self.ui_layout.setContentsMargins(10, 15, 10, 15)
        self.ui_layout.setSpacing(12)
        
        self.top_row = QHBoxLayout()
        
        self.btn_folder = QPushButton("📁 Folder")
        self.btn_folder.setToolTip("Select a folder to auto-load media")
        self.btn_folder.clicked.connect(self.select_folder)
        self.top_row.addWidget(self.btn_folder)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search YT Music...")
        self.search_input.returnPressed.connect(self.search_youtube)
        self.top_row.addWidget(self.search_input)

        self.btn_search = QPushButton("Play YT")
        self.btn_search.clicked.connect(self.search_youtube)
        self.top_row.addWidget(self.btn_search)

        self.ui_layout.addLayout(self.top_row)
        
        # --- SEEK BAR ---
        self.seek_layout = QHBoxLayout()
        
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderMoved.connect(self.set_position)
        self.seek_layout.addWidget(self.seek_slider)
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #ccc; font-size: 13px; font-weight: bold; margin-left: 8px;")
        self.seek_layout.addWidget(self.time_label)
        
        self.ui_layout.addLayout(self.seek_layout)

        # Info Label (Now Playing, Status)
        self.info_label = QLabel("Ready. Click 'Folder' or search YT above.")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #aaa;")
        self.ui_layout.addWidget(self.info_label)
        
        self.layout.addWidget(self.ui_container)

        # --- VIDEO PLAYER AREA ---
        self.video_container = QWidget()
        self.video_container.setStyleSheet("background-color: #000;")
        self.video_layout = QVBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_widget = QVideoWidget()
        self.video_layout.addWidget(self.video_widget)
        
        self.layout.addWidget(self.video_container, stretch=1)
        
        # Multimedia initialization
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        
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
            
            # Detect YouTube Stream URL vs Local File
            if media_path.startswith("http"):
                self.player.setSource(QUrl(media_path))
                name = "YouTube Music Stream"
            else:
                self.player.setSource(QUrl.fromLocalFile(media_path))
                name = os.path.basename(media_path)
                
            self.info_label.setText(f"Playing: {name}\nScroll up/down for next!")
            self.player.play()

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

    def search_youtube(self):
        query = self.search_input.text().strip()
        if not query:
            return
            
        self.btn_search.setText("...")
        self.btn_search.setEnabled(False)
        self.info_label.setText(f"Searching Youtube Music for: '{query}'...")
        
        self.search_thread = YTSearchThread(query)
        self.search_thread.finished.connect(self.on_youtube_result)
        self.search_thread.start()

    def on_youtube_result(self, stream_url):
        self.btn_search.setText("Play YT")
        self.btn_search.setEnabled(True)
        self.search_input.clear()
        
        if stream_url:
            self.playlist.insert(self.current_idx + 1, stream_url)
            self.current_idx += 1
            self.play_current()
        else:
            self.info_label.setText("YT Search failed. Could not fetch stream.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = TikTokPlayer()
    player.show()
    sys.exit(app.exec())
