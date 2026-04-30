import sys
import os
import random
import sqlite3
import math
from PyQt6.QtCore import Qt, QUrl, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QFileDialog, QLabel, QLineEdit, QHBoxLayout,
                             QSlider, QComboBox)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut




def get_db_path():
    # Use user app data directory for DB to avoid conflicts between dev and bundled app
    app_data = os.path.expanduser("~\\AppData\\Roaming")
    config_dir = os.path.join(app_data, "MyVideoPlayer")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "config.db")

DB_PATH = get_db_path()


def _init_db():
    """Initialize the SQLite database and create config table if not exists."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)"
    )
    conn.commit()
    conn.close()


def _db_get(key, default=None):
    """Get a config value from SQLite by key."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default


def _db_set(key, value):
    """Set a config value in SQLite (upsert)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO config (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


_init_db()
SUPPORTED_EXT = ['.mp4', '.avi', '.mkv', '.mp3', '.wav', '.flac', '.m4a', '.mov']




class VideoWidget(QVideoWidget):
    clicked = pyqtSignal()
    doubleClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self.clicked.emit)
        self._ignore_next_release = False
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._ignore_next_release:
                self._ignore_next_release = False
            else:
                self._click_timer.start(QApplication.doubleClickInterval())
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self._click_timer.isActive():
            self._click_timer.stop()
        self._ignore_next_release = True
        self.doubleClicked.emit()
        event.accept()


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
    SEEK_PERCENT = 0.05  # default, overridden by user selection
    SEEK_OPTIONS = [1, 2, 3, 5, 10, 15, 20, 25]  # available seek % choices
    DEFAULT_VOLUME = 70

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
            
            /* Seek Percent ComboBox Styling */
            QComboBox {
                background-color: #333;
                border: 1px solid #555;
                padding: 6px 10px;
                border-radius: 6px;
                color: #fff;
                font-size: 13px;
                font-weight: bold;
            }
            QComboBox:hover { border-color: #ff0050; }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #ff0050;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #333;
                color: #fff;
                selection-background-color: #ff0050;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
        """)

        self.playlist = []
        self.current_idx = -1
        self.current_folder = ""

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
        self.seek_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderMoved.connect(self.set_position)
        self.seek_layout.addWidget(self.seek_slider)
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #ccc; font-size: 13px; font-weight: bold; margin-left: 8px;")
        self.seek_layout.addWidget(self.time_label)
        
        self.ui_layout.addLayout(self.seek_layout)

        # --- VOLUME CONTROL ---
        self.volume_layout = QHBoxLayout()
        self.volume_label = QLabel("Volume")
        self.volume_label.setStyleSheet("color: #ccc; font-size: 13px; font-weight: bold; margin-right: 8px;")
        self.volume_layout.addWidget(self.volume_label)

        self.volume_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.volume_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.DEFAULT_VOLUME)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.volume_layout.addWidget(self.volume_slider)

        self.volume_value_label = QLabel(f"{self.DEFAULT_VOLUME}%")
        self.volume_value_label.setStyleSheet("color: #ccc; font-size: 13px; font-weight: bold; margin-left: 8px;")
        self.volume_layout.addWidget(self.volume_value_label)

        self.ui_layout.addLayout(self.volume_layout)

        # --- SEEK PERCENT CONTROL ---
        self.seek_pct_layout = QHBoxLayout()
        self.seek_pct_label = QLabel("Seek Step")
        self.seek_pct_label.setStyleSheet("color: #ccc; font-size: 13px; font-weight: bold; margin-right: 8px;")
        self.seek_pct_layout.addWidget(self.seek_pct_label)

        self.seek_pct_combo = QComboBox()
        self.seek_pct_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.seek_pct_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for pct in self.SEEK_OPTIONS:
            self.seek_pct_combo.addItem(f"{pct}%", pct)
        # Set default to 5%
        default_idx = self.SEEK_OPTIONS.index(5)
        self.seek_pct_combo.setCurrentIndex(default_idx)
        self.seek_pct_combo.currentIndexChanged.connect(self.on_seek_pct_changed)
        self.seek_pct_layout.addWidget(self.seek_pct_combo, stretch=1)

        self.ui_layout.addLayout(self.seek_pct_layout)

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
        self.video_widget.clicked.connect(self.toggle_play_pause)
        self.video_widget.doubleClicked.connect(self.toggle_fullscreen)
        self.video_layout.addWidget(self.video_widget)
        
        self.layout.addWidget(self.video_container, stretch=1)
        self.layout.addWidget(self.ui_container)
        
        # Multimedia initialization
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(self.DEFAULT_VOLUME / 100.0)
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

        self._setup_shortcuts()
        
        # Try loading config immediately
        self.load_config()

    def _setup_shortcuts(self):
        shortcuts = [
            ("Up", self.play_prev),
            ("Down", self.play_next),
            ("Left", lambda: self.seek_relative(-self._seek_step_ms())),
            ("Right", lambda: self.seek_relative(self._seek_step_ms())),
            ("Space", self.toggle_play_pause),
            ("F", self.toggle_fullscreen),
            ("Esc", self.exit_fullscreen),
        ]

        self._shortcuts = []
        for key, handler in shortcuts:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

    def load_config(self):
        try:
            folder = _db_get("folder", "")
            volume = _db_get("volume", str(self.DEFAULT_VOLUME))
            volume = max(0, min(100, int(volume)))
            self.volume_slider.setValue(volume)
            self.set_volume(volume, persist=False)

            # Restore seek percent
            seek_pct = int(_db_get("seek_percent", "5"))
            if seek_pct in self.SEEK_OPTIONS:
                idx = self.SEEK_OPTIONS.index(seek_pct)
                self.seek_pct_combo.setCurrentIndex(idx)
                self.SEEK_PERCENT = seek_pct / 100.0

            if folder and os.path.exists(folder):
                self.current_folder = folder
                self.scan_folder(folder)
        except Exception as e:
            print("Failed to load config:", e)

    def save_config(self, folder=None):
        folder_to_save = self.current_folder if folder is None else folder
        self.current_folder = folder_to_save or ""
        _db_set("folder", self.current_folder)
        _db_set("volume", self.volume_slider.value())
        _db_set("seek_percent", self.seek_pct_combo.currentData())

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Media Folder")
        if folder:
            self.current_folder = folder
            self.save_config(folder)
            self.scan_folder(folder)
            self.setFocus() # return focus to main window to detect keys

    def set_volume(self, value, persist=True):
        self.audio_output.setVolume(value / 100.0)
        self.volume_value_label.setText(f"{value}%")
        if persist:
            self.save_config()

    def on_seek_pct_changed(self, index):
        pct = self.seek_pct_combo.currentData()
        if pct is not None:
            self.SEEK_PERCENT = pct / 100.0
            self.save_config()

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
            self.current_idx = random.randint(0, len(self.playlist) - 1)
            self.play_current()

    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def seek_relative(self, delta_ms):
        if self.player.duration() <= 0:
            return
        new_pos = max(0, min(self.player.duration(), self.player.position() + delta_ms))
        self.player.setPosition(new_pos)

    def _seek_step_ms(self):
        step_ms = self.player.duration() * self.SEEK_PERCENT
        return max(1000, int(math.ceil(step_ms / 1000.0) * 1000))

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
            self.toggle_play_pause()
        elif event.key() == Qt.Key.Key_Left:
            self.seek_relative(-self._seek_step_ms())
        elif event.key() == Qt.Key.Key_Right:
            self.seek_relative(self._seek_step_ms())
        elif event.key() == Qt.Key.Key_F:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape:
            self.exit_fullscreen()
        else:
            super().keyPressEvent(event)

    def exit_fullscreen(self):
        if self.isFullScreen():
            self.toggle_fullscreen()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = TikTokPlayer()
    player.show()
    sys.exit(app.exec())
