# -*- coding: utf-8 -*-
"""piano_qt.py - NowPiano на PyQt6. Полная сборка: PDF, Audiveris, звук, клавиатура."""

import os
import sys
import time
import threading
from bisect import bisect_right
from html import escape as html_escape

from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QElapsedTimer, QRectF, QSettings, QEvent
from PyQt6.QtGui import QAction, QKeySequence, QFont, QPixmap, QImage, QPainter, QPen, QBrush, QColor, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QProgressBar, QToolBar, QStatusBar,
    QSizePolicy, QFileDialog, QMessageBox, QSpinBox, QDialog, QComboBox, QInputDialog,
    QTextBrowser, QTextEdit
)


def resource_path(rel: str) -> str:
    """Find resources both in source layout and PyInstaller builds."""
    if getattr(sys, "frozen", False):
        bases = [
            getattr(sys, "_MEIPASS", ""),
            os.path.dirname(sys.executable),
        ]
    else:
        source_dir = os.path.dirname(os.path.abspath(__file__))
        bases = [
            source_dir,
            os.path.dirname(source_dir),
        ]

    for base in bases:
        if base:
            candidate = os.path.join(base, rel)
            if os.path.isfile(candidate):
                return candidate

    return os.path.join(bases[0] or os.path.dirname(__file__), rel)


# --- PyInstaller windowed mode fix: sys.stdout/stderr = None ---
if getattr(sys, "frozen", False):
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
from qt_audio import (
    AudioEngine, run_audiveris, run_homr, run_homr_image, recognize_tempo_from_image, _image_to_pdf, musicxml_to_events,
    total_duration, NoteEvent, MANUAL_BPM, START_NOTE, NUM_KEYS, set_keyboard_size, get_keyboard_range,
    SOUNDFONT_PATH, AUDIVERIS_EXE,
    export_midi, load_midi_events, load_kar_lyrics, load_kar_note_events, render_score_to_pngs
)
from qt_render import KeyboardView, PdfView, WelcomeView
from qt_pianoroll import PianoRollView
from qt_midi_recorder import MidiRecorder


# ---------- QSS ----------
QSS = """
QMainWindow, QWidget {
    background-color: #f3f5f9;
    color: #1a1c24;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 13px;
}
QToolBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffffff, stop:1 #eef1f6);
    border: none;
    border-bottom: 1px solid #d0d4dc;
    padding: 3px 6px;
    spacing: 3px;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffffff, stop:1 #e6eaf2);
    color: #1a1c24;
    border: 1px solid #c8cdd8;
    border-radius: 10px;
    padding: 6px 14px;
    font-weight: 600;
    min-width: 40px;
    min-height: 28px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #f4f7fc, stop:1 #dde3ee);
    border: 1px solid #a8b0c0;
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #d8dde8, stop:1 #e6eaf2);
    padding-top: 7px; padding-bottom: 5px;
}
QPushButton:checked {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4a90e2, stop:1 #2f6dbb);
    border: 1px solid #1f4a80;
    color: #ffffff;
}
QPushButton#play {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4ecb71, stop:1 #2ea44f);
    border: 1px solid #1e7a3a;
    color: #ffffff;
}
QPushButton#play:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #5fdc82, stop:1 #38b85b);
}
QPushButton#stop {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ef5b4d, stop:1 #c0392b);
    border: 1px solid #8e2a1f;
    color: #ffffff;
}
QPushButton#stop:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ff6c5e, stop:1 #d0442f);
}
QPushButton[icon_button="true"] {
    background: transparent;
    border: none;
    font-size: 44px;
    min-width: 72px;
    min-height: 56px;
    padding: 4px 12px;
}
QPushButton[icon_button="true"]:hover {
    background: rgba(74, 144, 226, 50);
    border-radius: 8px;
}
QPushButton[icon_button="true"]:pressed {
    background: rgba(74, 144, 226, 100);
    border-radius: 8px;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #d8dde8;
    border: 1px solid #c0c6d2;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #4a90e2, stop:1 #7bb8ff);
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffffff, stop:1 #c8ccd6);
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: 1px solid #8a92a4;
}
QProgressBar {
    background: #e2e6ee;
    border: 1px solid #c0c6d2;
    border-radius: 8px;
    height: 10px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #4a90e2, stop:1 #7bb8ff);
    border-radius: 7px;
}
QStatusBar {
    background: #eef1f6;
    color: #4a5060;
    border-top: 1px solid #d0d4dc;
}
QLabel#time {
    color: #1a1c24;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 15px;
    font-weight: bold;
    padding: 0 8px;
}
QLabel#bpm {
    color: #1a1c24;
    font-weight: bold;
    padding: 0 6px;
}
"""



# Международная буквенная нотация: C D E F G A B.
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

CHORD_TYPES = [
    ((0, 4, 7), "major"), ((0, 3, 7), "minor"),
    ((0, 3, 6), "dim"), ((0, 4, 8), "aug"),
    ((0, 2, 7), "sus2"), ((0, 5, 7), "sus4"),
    ((0, 4, 7, 10), "7"), ((0, 4, 7, 11), "maj7"),
    ((0, 3, 7, 10), "m7"), ((0, 3, 7, 11), "m(maj7)"),
    ((0, 3, 6, 10), "m7b5"), ((0, 3, 6, 9), "dim7"),
    ((0, 4, 7, 9), "6"), ((0, 3, 7, 9), "m6"),
    ((0, 2, 4, 7), "add9"), ((0, 2, 4, 7, 10), "9"),
]

def note_name(midi, octave=True):
    midi = int(midi)
    name = NOTE_NAMES[midi % 12]
    return name + str(midi // 12 - 1) if octave else name

def chord_name(notes):
    pitches = sorted(set(int(n) % 12 for n in notes))
    if len(pitches) < 3:
        return ""
    candidates = []
    for root in pitches:
        intervals = {(pitch - root) % 12 for pitch in pitches}
        for template, suffix in CHORD_TYPES:
            if intervals == set(template):
                candidates.append((len(template), root, suffix))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: item[0], reverse=True)
    _, root, suffix = candidates[0]
    return f"{NOTE_NAMES[root]} {suffix}"


class StaffTimelineView(QWidget):
    """Читаемая движущаяся цифровая партитура: правая рука синяя, левая зелёная."""
    RIGHT = QColor('#2878d0')
    LEFT = QColor('#159b69')
    def __init__(self, parent=None):
        super().__init__(parent)
        self.events = []
        self._live_recording = False
        self.duration = 0.0
        self.position = 0.0
        self.active_notes = set()
        self.active_right = set()
        self.active_left = set()
        self._played_notes = set()
        self._dragging_cursor = False
        self._manual_view = False
        self._drag_t0 = 0.0
        self._drag_window = 8.0
        self.seek_callback = None
        self.setMouseTracking(True)
        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_events(self, events, duration):
        self.events = list(events or [])
        self.duration = max(float(duration or 0), 0.01)
        self.position = 0.0
        self.active_notes = set(); self.active_right = set(); self.active_left = set()
        self._played_notes = set()
        self.update()

    def set_position(self, position, active_notes=None, right_notes=None, left_notes=None):
        self.position = max(0.0, float(position or 0))
        if active_notes is not None: self.active_notes = set(active_notes)
        if right_notes is not None: self.active_right = set(right_notes)
        if left_notes is not None: self.active_left = set(left_notes)
        self._played_notes.update(self.active_notes)
        self._played_notes.update(self.active_right)
        self._played_notes.update(self.active_left)
        self.update()

    @staticmethod
    def _pitch_y(midi, clef, y_top, line_gap):
        names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        steps = {'C': 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6}
        base = 64 if clef == 'treble' else 43  # E4 / G2, нижняя линия
        def dia(n):
            return (n // 12 - 1) * 7 + steps[names[n % 12][0]]
        return y_top + 4 * line_gap - (dia(int(midi)) - dia(base)) * (line_gap / 2.0)

    def _time_at_x(self, x):
        w = max(1, self.width())
        left = 62
        right = w - 22
        window = max(6.0, min(12.0, (right-left) / 95.0))
        if self._dragging_cursor or self._manual_view:
            t0 = self._drag_t0
            window = self._drag_window
        else:
            t0 = max(0.0, self.position - window * 0.22)
        frac = max(0.0, min(1.0, (float(x)-left) / max(1.0, right-left)))
        return max(0.0, min(self.duration, t0 + frac * window))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.events and self.duration > 0:
            w = max(1, self.width())
            left, right = 62, w - 22
            self._drag_window = max(6.0, min(12.0, (right-left) / 95.0))
            self._drag_t0 = max(0.0, self.position - self._drag_window * 0.22)
            self._dragging_cursor = True
            self._manual_view = True
            if callable(self.seek_callback):
                self.seek_callback(self._time_at_x(event.position().x()))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging_cursor and (event.buttons() & Qt.MouseButton.LeftButton):
            if callable(self.seek_callback):
                self.seek_callback(self._time_at_x(event.position().x()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging_cursor and event.button() == Qt.MouseButton.LeftButton:
            if callable(self.seek_callback):
                self.seek_callback(self._time_at_x(event.position().x()))
            self._dragging_cursor = False
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor('#fbfcff'))
        w, h = self.width(), self.height(); left = 62; right = w - 22
        line_gap = max(9, min(13, (h - 100) / 12)); staff_h = 4 * line_gap
        # Центрирование по вертикали: два нотоносца + отступ между ними
        _gap_between = 170  # вертикальный промежуток между верхним и нижним станом
        _used = staff_h * 2 + _gap_between + 16  # +16 запас снизу/сверху
        top = max(20, int((h - _used) / 2))
        p.setPen(QColor('#26364a')); p.setFont(QFont('Segoe UI', 10, QFont.Weight.DemiBold))
        p.drawText(12, 22, 'ЦИФРОВАЯ ПАРТИТУРА')
        p.setFont(QFont('Segoe UI', 9))
        if not self.events and not self._live_recording:
            p.setPen(QColor('#788397')); p.drawText(left, 75, 'Загрузите PDF или MIDI-файл')
            p.end(); return

        # Follow playback: keep a short readable time window rather than compressing
        # the entire piece into a few pixels. The notes scroll from right to left.
        window = max(6.0, min(12.0, (right-left) / 95.0))
        if self._dragging_cursor or self._manual_view:
            t0 = self._drag_t0
            window = self._drag_window
        else:
            t0 = max(0.0, self.position - window * 0.22)
        t1 = t0 + window
        def xpos(t): return left + (float(t)-t0) / max(.001, window) * (right-left)

        treble_y = top + 8; bass_y = top + staff_h + 128
        if bass_y + staff_h > h - 18:
            line_gap = max(7, (h - top - 80) / 12); staff_h = 4 * line_gap
            treble_y = top + 8; bass_y = top + staff_h + 118
        # Если после пересчёта снизу осталось много места — сдвинуть блок вниз
        _bottom_used = bass_y + staff_h + 8
        _extra = h - _bottom_used - top
        if _extra > 20:
            _shift = _extra // 2
            treble_y += _shift
            bass_y += _shift
        for clef, y0, color in [('treble', treble_y, self.RIGHT), ('bass', bass_y, self.LEFT)]:
            p.setPen(QPen(QColor('#aab4c3'), 1))
            for i in range(5): p.drawLine(left, int(y0+i*line_gap), right, int(y0+i*line_gap))
            p.setPen(color); p.setFont(QFont('Serif', 25))
            p.drawText(12, int(y0+3.5*line_gap), '𝄞' if clef == 'treble' else '𝄢')

        # Beat grid (approx. quarter-second labels are intentionally omitted).
        p.setPen(QPen(QColor('#e0e6ef'), 1, Qt.PenStyle.DotLine))
        tick = max(.25, 60.0 / 72.0)
        first = int(t0 / tick)
        for beat_idx in range(first, int(t1/tick)+2):
            t = beat_idx*tick; x = xpos(t)
            if left <= x <= right: p.drawLine(int(x), top, int(x), min(h-10, bass_y+staff_h+8))

        for ev in self.events:
            t = float(getattr(ev, 'time_seconds', 0.0)); dur = max(.08, float(getattr(ev, 'duration', .2)))
            if t + dur < t0 or t > t1: continue
            hand = getattr(ev, 'hand', 'R')
            clef = 'treble' if hand == 'R' else 'bass'
            y0 = treble_y if hand == 'R' else bass_y
            color = self.RIGHT if hand == 'R' else self.LEFT
            x = xpos(t); active = (t <= self.position <= t+dur and any(n in (self.active_right if hand=='R' else self.active_left or self.active_notes) for n in ev.notes))
            note_w = max(5, min(12, (right-left)/window*dur))
            for midi in ev.notes:
                y = self._pitch_y(int(midi), clef, y0, line_gap)
                # Ledger lines above and below each staff.
                if y < y0:
                    ly = y0-line_gap
                    while ly >= y-line_gap*.15:
                        p.setPen(QPen(QColor('#8d99aa'), 1)); p.drawLine(int(x-7), int(ly), int(x+7), int(ly)); ly -= line_gap
                elif y > y0+staff_h:
                    ly = y0+staff_h+line_gap
                    while ly <= y+line_gap*.15:
                        p.setPen(QPen(QColor('#8d99aa'), 1)); p.drawLine(int(x-7), int(ly), int(x+7), int(ly)); ly += line_gap
                p.setPen(QPen(color.darker(125) if not active else QColor('#e53935'), 1.5))
                p.setBrush(QBrush(color.lighter(125) if active else color))
                p.save(); p.translate(x, y); p.rotate(-18); p.drawEllipse(QRectF(-6, -4, 12, 8)); p.restore()
                # Show accidentals beside noteheads when spelling contains them.
                spelling = str(getattr(ev, "note_names", {}).get(int(midi), ""))
                accidental = ""
                if "#" in spelling:
                    accidental = chr(0x266f)
                elif "-" in spelling:
                    accidental = chr(0x266d)
                if accidental:
                    p.save()
                    p.setPen(color.darker(120))
                    p.setFont(QFont("Segoe UI Symbol", 12, QFont.Weight.Bold))
                    p.drawText(
                        QRectF(x - 21, y - 10, 14, 18),
                        Qt.AlignmentFlag.AlignCenter,
                        accidental
                    )
                    p.restore()
                p.setPen(QPen(color.darker(120), 1.4)); p.drawLine(int(x+5), int(y), int(x+5), int(y-22 if hand=='R' else y-18))
                # Note labels: single notes share a line; chords stack vertically.
                notes_sorted = sorted({int(n) for n in ev.notes}, reverse=True)
                rank = notes_sorted.index(int(midi))
                count = len(notes_sorted)
                label = ev.note_names.get(int(midi), note_name(midi))
                label = label.replace("#", chr(0x266f)).replace("-", chr(0x266d))
                p.setFont(QFont('Segoe UI', 8, QFont.Weight.Bold))
                p.setPen(color.darker(120))
                p.setBrush(Qt.BrushStyle.NoBrush)

                if hand == 'R':
                    base_y = int(treble_y - 18 - 3 * line_gap)
                    label_y = base_y - (count - 1 - rank) * 14
                else:
                    base_y = int(bass_y + staff_h + 15 + 2 * line_gap)
                    label_y = base_y + rank * 14

                p.drawText(
                    QRectF(x - 20, label_y - 11, 46, 14),
                    Qt.AlignmentFlag.AlignCenter,
                    label
                )

        # Fixed playhead makes the score appear to move underneath it.
        cursor_x = xpos(self.position)
        p.setPen(QPen(QColor('#e53935'), 2))
        p.drawLine(int(cursor_x), top-4, int(cursor_x), min(h-8, bass_y+staff_h+8))
        p.setPen(QColor('#e53935')); p.setFont(QFont('Segoe UI', 8, QFont.Weight.Bold))
        p.drawText(int(cursor_x+4), top-8, f'{self.position:.1f}s')
        p.end()


# ---------- Главное окно ----------
class PianoWindow(QMainWindow):

    sig_load_done = pyqtSignal(object, float, str)   # events, bpm, error
    sig_status = pyqtSignal(str)
    sig_page_ready = pyqtSignal(object)
    sig_lyrics_loaded = pyqtSignal(int, object)              # QPixmap

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NowPiano")
        self.resize(1400, 860)
        self.setMinimumSize(1000, 700)

        # Иконка окна
        _ico = resource_path(os.path.join("resources", "app_icon.ico"))
        _png = resource_path(os.path.join("resources", "app_icon.png"))
        _icon_file = _ico if os.path.isfile(_ico) else _png
        if os.path.isfile(_icon_file):
            self.setWindowIcon(QIcon(_icon_file))

        # Аудио
        self.audio = AudioEngine()
        self.audio_ok = self.audio.init()

        # Данные
        self.events: list[NoteEvent] = []
        self.current_bpm = MANUAL_BPM
        self.original_bpm = MANUAL_BPM
        self.duration = 0.0
        self.position = 0.0
        self.is_playing = False
        self.loop_enabled = False
        self._elapsed = QElapsedTimer()
        self._elapsed.start()
        self._cursor_map: dict = {}
        self._last_mxl: str = ''
        self._last_pdf_path: str = ''
        self._pdf_pages: list = []
        self._load_gen: int = 0
        self._loading: bool = False
        self._kar_lyrics = []
        self._kar_lyric_times = []

        # Индекс следующего события для проигрывания
        self._next_event_idx = 0

        self._training_active = False
        self._training_event_idx = 0
        self._training_event_remaining = set()
        self._training_correct = 0
        self._training_errors = 0
        self.midi_recorder = MidiRecorder()
        self._live_midi_score_active = False
        self._build_ui()

        # Приём файлов из Проводника Windows.
        # Accept file drops on the main window and all its child widgets.
        self.setAcceptDrops(True)
        for _widget in self.findChildren(QWidget):
            _widget.setAcceptDrops(True)
            _widget.installEventFilter(self)

        self._init_midi_input()
        self.setStyleSheet(QSS)

        # лоский стиль для кнопок управления в тулбаре
        self.setStyleSheet(self.styleSheet() + """
        QPushButton#btn_rewind, QPushButton#btn_play,
        QPushButton#btn_stop, QPushButton#btn_loop {
            background: transparent;
            border: none;
            outline: none;
            padding: 2px 6px;
            border-radius: 6px;
            font-size: 18px;
        }
        QPushButton#btn_rewind:hover, QPushButton#btn_play:hover,
        QPushButton#btn_stop:hover, QPushButton#btn_loop:hover {
            background: rgba(40, 120, 208, 60);
        }
        QPushButton#btn_rewind:pressed, QPushButton#btn_play:pressed,
        QPushButton#btn_stop:pressed, QPushButton#btn_loop:pressed {
            background: rgba(40, 120, 208, 120);
        }
        """)


        # Сигналы из фонового потока
        self.sig_load_done.connect(self._on_load_done)
        self.sig_status.connect(self._on_status)
        self.sig_page_ready.connect(self._on_page_ready)
        self.sig_lyrics_loaded.connect(self._set_kar_lyrics)

        # Таймер позиции
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

        if not self.audio_ok:
            self.status.showMessage(
                f"Внимание: звук не инициализирован. Проверь SoundFont: {SOUNDFONT_PATH}"
            )
        else:
            self.status.showMessage("Готов. Нажми «Открыть».")

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Топбар

        # ??????? ???? ??????????
        menubar = self.menuBar()

        menu_file = menubar.addMenu("\u0424\u0430\u0439\u043b")
        self.btn_open = QAction("\u041e\u0442\u043a\u0440\u044b\u0442\u044c...", self)
        self.btn_open.setShortcut(QKeySequence.StandardKey.Open)
        self.btn_open.triggered.connect(self.on_open)
        menu_file.addAction(self.btn_open)

        menu_score = menubar.addMenu("\u041f\u0430\u0440\u0442\u0438\u0442\u0443\u0440\u0430")
        self.btn_midi = QAction("\u042d\u043a\u0441\u043f\u043e\u0440\u0442 MIDI", self)
        self.btn_midi.triggered.connect(self.on_export_midi)
        self.btn_midi.setEnabled(False)
        menu_score.addAction(self.btn_midi)
        self.act_record_pdf_export = QAction("\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u043f\u0430\u0440\u0442\u0438\u0442\u0443\u0440\u0443 PDF...", self)
        self.act_record_pdf_export.triggered.connect(self._record_export_pdf)
        self.act_record_pdf_export.setEnabled(False)
        menu_score.addAction(self.act_record_pdf_export)

        menu_view = menubar.addMenu("\u0412\u0438\u0434")
        act_staff = QAction("\u0426\u0438\u0444\u0440\u043e\u0432\u0430\u044f \u043f\u0430\u0440\u0442\u0438\u0442\u0443\u0440\u0430", self)
        act_staff.triggered.connect(lambda: self._set_display_view("staff"))
        menu_view.addAction(act_staff)
        act_roll = QAction("Piano Roll", self)
        act_roll.triggered.connect(lambda: self._set_display_view("roll"))
        menu_view.addAction(act_roll)
        act_pdf = QAction("PDF / \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435", self)
        act_pdf.triggered.connect(lambda: self._set_display_view("pdf"))
        menu_view.addAction(act_pdf)

        menu_midi = menubar.addMenu("MIDI")
        self.btn_midi_input = QAction("MIDI IN: \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435...", self)
        self.btn_midi_input.triggered.connect(self._show_midi_dialog)
        menu_midi.addAction(self.btn_midi_input)
        self.btn_midi_output = QAction("MIDI OUT: \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435...", self)
        self.btn_midi_output.triggered.connect(self._show_midi_out_dialog)
        menu_midi.addAction(self.btn_midi_output)

        menu_midi.addSeparator()
        self.act_record_start = QAction("\u041d\u0430\u0447\u0430\u0442\u044c \u0437\u0430\u043f\u0438\u0441\u044c \u0438\u0441\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f", self)
        self.act_record_start.triggered.connect(self._record_start)
        menu_midi.addAction(self.act_record_start)

        self.act_record_pause = QAction("\u041f\u0430\u0443\u0437\u0430 / \u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c \u0437\u0430\u043f\u0438\u0441\u044c", self)
        self.act_record_pause.triggered.connect(self._record_pause)
        menu_midi.addAction(self.act_record_pause)

        self.act_record_stop = QAction("\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u044c \u0437\u0430\u043f\u0438\u0441\u044c", self)
        self.act_record_stop.triggered.connect(self._record_stop)
        menu_midi.addAction(self.act_record_stop)

        self.act_record_export = QAction("\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c MIDI-\u0437\u0430\u043f\u0438\u0441\u044c...", self)
        self.act_record_export.triggered.connect(self._record_export)
        self.act_record_export.setEnabled(False)
        menu_midi.addAction(self.act_record_export)

        menu_training = menubar.addMenu("\u0422\u0440\u0435\u043d\u0438\u0440\u043e\u0432\u043a\u0430")
        self.btn_training = QAction("MIDI-\u0442\u0440\u0435\u043d\u0438\u0440\u043e\u0432\u043a\u0430", self)
        self.btn_training.setCheckable(True)
        self.btn_training.toggled.connect(self._toggle_midi_training)
        menu_training.addAction(self.btn_training)

        self._training_waiting_for_correct = False

        menu_settings = menubar.addMenu("\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438")
        act_bpm = QAction("\u0422\u0435\u043c\u043f (BPM)...", self)
        act_bpm.triggered.connect(self._choose_bpm)
        menu_settings.addAction(act_bpm)
        act_keys = QAction("\u0420\u0430\u0437\u043c\u0435\u0440 \u043a\u043b\u0430\u0432\u0438\u0430\u0442\u0443\u0440\u044b...", self)
        act_keys.triggered.connect(self._choose_keyboard_size)
        menu_settings.addAction(act_keys)

        menu_help = menubar.addMenu("\u0421\u043f\u0440\u0430\u0432\u043a\u0430")
        self.btn_about = QAction("\u041e \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0435 NowPiano", self)
        self.btn_about.triggered.connect(self._show_about)
        menu_help.addAction(self.btn_about)

        # ?????????? ?????? ?????????? ????????????????
        tb = QToolBar("\u041f\u0440\u043e\u0438\u0433\u0440\u044b\u0432\u0430\u0442\u0435\u043b\u044c", self)
        tb.setObjectName("player_toolbar")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(tb)

        self.btn_rewind = QPushButton("\u21e4")
        self.btn_rewind.setObjectName("btn_rewind")
        self.btn_rewind.setToolTip("\u0412 \u043d\u0430\u0447\u0430\u043b\u043e")
        self.btn_rewind.clicked.connect(self.on_rewind)
        tb.addWidget(self.btn_rewind)

        self.btn_play = QPushButton("\u25b6")
        self.btn_play.setObjectName("btn_play")
        self.btn_play.setToolTip("\u0412\u043e\u0441\u043f\u0440\u043e\u0438\u0437\u0432\u0435\u0441\u0442\u0438")
        self.btn_play.clicked.connect(self.on_play_pause)
        tb.addWidget(self.btn_play)


        self.btn_stop = QPushButton("\u25a0")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setToolTip("\u0421\u0442\u043e\u043f")
        self.btn_stop.clicked.connect(self.on_stop)
        tb.addWidget(self.btn_stop)

        self.btn_loop = QPushButton("\u21bb")
        self.btn_loop.setObjectName("btn_loop")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setToolTip("\u041f\u043e\u0432\u0442\u043e\u0440")
        self.btn_loop.toggled.connect(self.on_loop)
        tb.addWidget(self.btn_loop)

        tb.addSeparator()

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setMinimumWidth(120)
        self.progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.progress.setMouseTracking(True)
        self.progress.mousePressEvent = self._progress_click
        self.progress.mouseMoveEvent = self._progress_move
        self.progress.mouseReleaseEvent = self._progress_release
        tb.addWidget(self.progress)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setObjectName("time")
        tb.addWidget(self.lbl_time)

        # ??????? ??????????? ???????? ??????????? ??? ?????????????
        # ? ????????????? ????????????? ????????, ????? ? ??????????.
        self.slider_bpm = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_bpm.setRange(30, 200)
        self.slider_bpm.setValue(int(MANUAL_BPM))
        self.slider_bpm.valueChanged.connect(self.on_bpm)
        self.slider_bpm.setFixedWidth(125)
        self.slider_bpm.setToolTip("???? ???????????????")
        tb.addWidget(QLabel("BPM"))
        tb.addWidget(self.slider_bpm)

        self.lbl_bpm = QSpinBox(self)
        self.lbl_bpm.setRange(30, 200)
        self.lbl_bpm.setValue(int(MANUAL_BPM))
        self.lbl_bpm.valueChanged.connect(self.on_bpm)
        self.lbl_bpm.setFixedWidth(65)
        self.lbl_bpm.setToolTip("?????? ???? (BPM)")
        tb.addWidget(self.lbl_bpm)

        self.combo_keys = QComboBox(self)
        self.combo_keys.addItem("88", 88)
        self.combo_keys.addItem("76", 76)
        self.combo_keys.addItem("61", 61)
        self.combo_keys.setCurrentIndex(0)
        try:
            from qt_audio import set_keyboard_size as _set
            _set(88)
        except Exception:
            pass
        self.combo_keys.currentIndexChanged.connect(self.on_keys_changed)
        self.combo_keys.hide()

        self.pdf_view = PdfView()
        self.pianoroll_view = PianoRollView()
        self.pianoroll_view.keyboard_size_requested.connect(
            self._set_keyboard_size_from_roll
        )
        _low, _num_keys = get_keyboard_range()
        self.pianoroll_view.set_keyboard_range(_low, _num_keys)
        self.pianoroll_view.setVisible(False)
        self.staff_view = StaffTimelineView()
        self.staff_view.seek_callback = self._seek_to_time
        self.staff_view.setVisible(False)
        _BACK_IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "assets", "back.jpg")
        self.welcome_view = WelcomeView(_BACK_IMG)
        self.welcome_view.setVisible(False)
        root.addWidget(self.pdf_view, stretch=1)
        root.addWidget(self.welcome_view, stretch=1)
        root.addWidget(self.pianoroll_view, stretch=1)
        root.addWidget(self.staff_view, stretch=1)

        # Два независимых индикатора аккордов — по рукам.
        chord_panel = QWidget()
        chord_layout = QHBoxLayout(chord_panel)
        chord_layout.setContentsMargins(8, 4, 8, 4)
        chord_layout.setSpacing(8)

        self.chord_left_label = QLabel("ЛЕВАЯ РУКА: —")
        self.chord_left_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chord_left_label.setMinimumHeight(38)
        self.chord_left_label.setStyleSheet("""
            QLabel {
                background: #e4f6ee; color: #08784d;
                font-size: 15px; font-weight: bold;
                border: 1px solid #9bd8bd; border-radius: 7px;
                padding: 4px;
            }
        """)

        self.chord_right_label = QLabel("ПРАВАЯ РУКА: —")
        self.chord_right_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chord_right_label.setMinimumHeight(38)
        self.chord_right_label.setStyleSheet("""
            QLabel {
                background: #eaf2ff; color: #174ea6;
                font-size: 15px; font-weight: bold;
                border: 1px solid #b4cff8; border-radius: 7px;
                padding: 4px;
            }
        """)

        chord_layout.addWidget(self.chord_left_label, 1)
        chord_layout.addWidget(self.chord_right_label, 1)
        self.chord_panel = chord_panel
        root.addWidget(chord_panel)

        self.kar_lyric_label = QTextBrowser()
        self.kar_lyric_label.setReadOnly(True)
        self.kar_lyric_label.setOpenExternalLinks(False)
        self.kar_lyric_label.setMinimumHeight(135)
        self.kar_lyric_label.setMaximumHeight(215)
        self.kar_lyric_label.setStyleSheet(
            "QTextBrowser { background: #202633; color: #e8edf5; "
            "font-size: 19px; font-weight: 600; "
            "border: 1px solid #39465a; border-radius: 8px; "
            "padding: 7px 12px; }"
        )
        self.kar_lyric_label.setVisible(False)
        self._kar_last_rendered_idx = None
        root.addWidget(self.kar_lyric_label)


        # Клавиатура — сохраняем исходную отрисовку и подписи клавиш.
        self.keyboard = KeyboardView()
        self.keyboard.note_clicked.connect(self.on_note_clicked)
        root.addWidget(self.keyboard, stretch=0)

        # Статус + отдельный индикатор распознавания PDF/MIDI
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.recognition_label = QLabel("Распознавание: —")
        self.recognition_label.setMinimumWidth(170)
        self.recognition_progress = QProgressBar()
        self.recognition_progress.setRange(0, 100)
        self.recognition_progress.setValue(0)
        self.recognition_progress.setFixedWidth(150)
        self.recognition_progress.setFixedHeight(14)
        self.recognition_progress.setTextVisible(True)
        self.recognition_label.setVisible(True)
        self.recognition_progress.setVisible(True)
        self.recognition_label.setStyleSheet("font-weight: 600; color: #303846; padding: 0 6px;")
        self.status.addPermanentWidget(self.recognition_label)
        self.status.addPermanentWidget(self.recognition_progress)

    # ---------- Загрузка PDF ----------
    def on_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть",
            "",
            "Ноты (*.pdf *.jpg *.jpeg *.png *.tif *.tiff *.bmp *.mid *.midi *.kar *.mxl *.musicxml *.xml);;"
            "PDF (*.pdf);;"
            "Картинки (*.jpg *.jpeg *.png *.tif *.tiff *.bmp);;"
            "MIDI/KAR (*.mid *.midi *.kar);;"
            "MusicXML (*.mxl *.musicxml *.xml);;"
            "Все файлы (*.*)"
        )
        if path:
            self._open_path(path)

    def _open_path(self, path):
        if not path:
            return
        path = os.path.abspath(path)
        lower = path.lower()

        # Сброс предыдущей партитуры — сохранён исходный порядок действий.
        self.is_playing = False
        try:
            self.audio.all_off()
        except Exception:
            pass
        self.keyboard.set_active_notes(set(), set(), set())
        self.chord_left_label.setText("ЛЕВАЯ РУКА: —")
        self.chord_right_label.setText("ПРАВАЯ РУКА: —")
        self.pdf_view.clear_cursor()
        self.events = []
        self._cursor_map = {}
        self._pdf_pages = []
        self.pdf_view.set_page(None)
        self._last_mxl = ""
        self._last_pdf_path = ""
        self.duration = 0.0
        self.position = 0.0
        self._next_event_idx = 0
        self._kar_lyrics = []
        self._kar_lyric_times = []
        self._kar_last_rendered_idx = None
        self.kar_lyric_label.clear()
        self.kar_lyric_label.setVisible(False)
        self._update_time_label()
        self.btn_midi.setEnabled(False)
        self.staff_view.setVisible(False)

        self.on_stop()
        self._loading = True
        self.btn_play.setEnabled(True)
        self.recognition_label.setVisible(True)
        self.recognition_progress.setVisible(True)

        self._load_gen = getattr(self, "_load_gen", 0) + 1
        gen = self._load_gen

        self.status.showMessage(f"Загрузка: {os.path.basename(path)}")
        if lower.endswith((".mid", ".midi", ".kar")):
            self.recognition_label.setText("KAR: загрузка караоке" if lower.endswith(".kar") else "MIDI: загрузка")
            self.recognition_progress.setRange(0, 100)
            self.recognition_progress.setValue(0)
            threading.Thread(
                target=self._load_midi_worker,
                args=(path, gen),
                daemon=True
            ).start()
        else:
            self.recognition_label.setText("Распознавание PDF")
            self.recognition_progress.setRange(0, 100)
            self.recognition_progress.setValue(0)
            threading.Thread(
                target=self._load_pdf_worker,
                args=(path, gen),
                daemon=True
            ).start()

    def _load_pdf_worker(self, path, gen):
        if gen != self._load_gen:
            return
        try:
            # 1. Рендер первой страницы PDF через Poppler (pdf2image)
            self.sig_status.emit("Шаг 1/3: рендер PDF...")
            pix = None
            try:
                from pdf2image import convert_from_path
                poppler_path = None
                _cand = []
                _exe_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
                if getattr(sys, "frozen", False):
                    _cand.append(os.path.join(_exe_dir, "_internal", "poppler", "Library", "bin"))
                    _cand.append(os.path.join(_exe_dir, "poppler", "Library", "bin"))
                    _cand.append(os.path.join(_exe_dir, "poppler", "bin"))
                _proj = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
                _cand.append(os.path.join(_proj, "tools", "poppler", "Library", "bin"))
                _cand.append(os.path.join(_proj, "tools", "poppler", "bin"))
                _cand.append(os.path.join(_exe_dir, "tools", "poppler", "Library", "bin"))
                for _c in _cand:
                    if os.path.exists(os.path.join(_c, "pdfinfo.exe")):
                        poppler_path = _c
                        break
                if poppler_path:
                    images = convert_from_path(path, dpi=140, first_page=1, last_page=1, poppler_path=poppler_path)
                else:
                    images = convert_from_path(path, dpi=140, first_page=1, last_page=1)
                if images:
                    img = images[0].convert("RGB")
                    data = img.tobytes("raw", "RGB")
                    qimg = QImage(data, img.width, img.height, img.width * 3,
                                  QImage.Format.Format_RGB888)
                    pix = QPixmap.fromImage(qimg)
            except Exception as e:
                print("[pdf] render error:", e)
            if pix is not None:
                self.sig_page_ready.emit(pix)

            # 2. Распознавание: PDF -> Audiveris -> homr; картинка -> homr -> PDF -> Audiveris
            _ext = os.path.splitext(path)[1].lower()
            mxl = None
            e_aud = None
            e_homr = None
            e_homr_img = None
            e_conv = None
            tempo_override = None

            if _ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"):
                self.sig_status.emit("Картинка — распознаю через homr...")
                try:
                    tempo_override = recognize_tempo_from_image(path)
                    if tempo_override is not None:
                        print(f"[tempo] Image tempo: {tempo_override} BPM", flush=True)
                except Exception as e_tempo:
                    print("[tempo] Image tempo recognition skipped:", e_tempo, flush=True)

                try:
                    mxl = run_homr_image(path)
                except Exception as e_img:
                    e_homr_img = e_img
                    print("[homr-img] ошибка:", e_img, flush=True)

                if (not mxl) or (not os.path.exists(mxl)):
                    self.sig_status.emit("homr не справился — конвертирую в PDF и пробую Audiveris...")
                    pdf_tmp = None
                    try:
                        pdf_tmp = _image_to_pdf(path)
                        try:
                            mxl = run_audiveris(pdf_tmp)
                        except Exception as e_a:
                            e_aud = e_a
                            print("[audiveris] ошибка:", e_a, flush=True)
                        if (not mxl) or (not os.path.exists(mxl)):
                            try:
                                mxl = run_homr(pdf_tmp)
                            except Exception as e_h:
                                e_homr = e_h
                                print("[homr-pdf] ошибка:", e_h, flush=True)
                    except Exception as e_c:
                        e_conv = e_c
                        print("[conv] ошибка конвертации:", e_c, flush=True)
                    finally:
                        if pdf_tmp and os.path.isfile(pdf_tmp):
                            try:
                                os.remove(pdf_tmp)
                            except OSError:
                                pass

                if (not mxl) or (not os.path.exists(mxl)):
                    msg = ("Не удалось распознать картинку.\n"
                           "homr(img): " + str(e_homr_img) + "\n"
                           "conv: " + str(e_conv) + "\n"
                           "Audiveris: " + str(e_aud) + "\n"
                           "homr(pdf): " + str(e_homr))
                    print("[omr-img]", msg, flush=True)
                    if gen != self._load_gen:
                        return
                    self.sig_load_done.emit(None, MANUAL_BPM, msg)
                    return
            else:
                self.sig_status.emit("Шаг 2/3: Audiveris распознаёт (может занять минуту)...")
                try:
                    mxl = run_audiveris(path)
                except Exception as e:
                    e_aud = e
                    print("[audiveris] ошибка:", e, flush=True)

                if (not mxl) or (not os.path.exists(mxl)):
                    self.sig_status.emit("Audiveris не справился — пробую homr...")
                    try:
                        mxl = run_homr(path)
                    except Exception as e_h:
                        e_homr = e_h
                        print("[homr] ошибка:", e_h, flush=True)

                if (not mxl) or (not os.path.exists(mxl)):
                    msg = ("Ни Audiveris, ни homr не смогли распознать ноты.\n"
                           "Audiveris: " + str(e_aud) + "\n"
                           "homr: " + str(e_homr))
                    print("[omr]", msg, flush=True)
                    if gen != self._load_gen:
                        return
                    self.sig_load_done.emit(None, MANUAL_BPM, msg)
                    return
            self._last_mxl = mxl
            self._last_pdf_path = path

            # 3. MusicXML -> события
            self.sig_status.emit("Шаг 3/3: разбор MusicXML...")
            events, bpm, n_parts = musicxml_to_events(mxl, bpm_override=tempo_override)

            if gen != self._load_gen:
                return
            self.sig_load_done.emit(events, bpm, "")
        except Exception as e:
            if gen != self._load_gen:
                return
            self.sig_load_done.emit(None, MANUAL_BPM, str(e))

    def _on_page_ready(self, pixmap):
        self.pdf_view.set_page(pixmap)
        if not hasattr(self, "_pdf_pages") or self._pdf_pages is None:
            self._pdf_pages = []
        self._pdf_pages.append(pixmap)
        if self.events:
            self._cursor_map = self._build_cursor_map(pixmap, self.events)

    def _on_load_done(self, events, bpm, error):
        self._loading = False
        self.btn_open.setEnabled(True)
        if error or events is None:
            self.status.showMessage(f"Ошибка: {error}")
            if hasattr(self, "recognition_label"):
                self.recognition_label.setText("Распознавание: ошибка")
                self.recognition_progress.setRange(0, 100)
                self.recognition_progress.setValue(0)
            QMessageBox.warning(self, "Ошибка загрузки", str(error))
            return
        self.events = events
        self.current_bpm = bpm
        self.original_bpm = bpm
        self.duration = total_duration(events)
        self.position = 0.0
        self._next_event_idx = 0
        if hasattr(self, "btn_training"):
            previous = self.btn_training.blockSignals(True)
            self.btn_training.setChecked(False)
            self.btn_training.blockSignals(previous)
        self._training_event_idx = 0
        self._training_event_remaining = set()
        self._training_correct = 0
        self._training_errors = 0
        self.slider_bpm.blockSignals(True)
        self.slider_bpm.setValue(int(bpm))
        self.slider_bpm.blockSignals(False)
        self.lbl_bpm.setValue(int(bpm))
        # Для PDF показываем не исходную картинку, а новую цифровую партитуру,
        # построенную по распознанным событиям MusicXML. Это позволяет подсвечивать
        # ноты по времени воспроизведения; исходный PDF остаётся источником OCR.
        self.pianoroll_view.setVisible(False)
        self.staff_view.setVisible(True)
        self.welcome_view.setVisible(False)
        self.pdf_view.setVisible(False)
        self.staff_view.set_events(events, self.duration)
        self.pianoroll_view.set_events(events, self.duration, bpm)
        if self._pdf_pages:
            self._cursor_map = self._build_cursor_map(self._pdf_pages[0], events)
        self.btn_midi.setEnabled(bool(self._last_mxl) and self._last_mxl.lower().endswith((".mxl", ".musicxml", ".xml")))
        self._update_time_label()
        if hasattr(self, "recognition_label"):
            if self._last_pdf_path.lower().endswith(".pdf"):
                self.recognition_label.setText(f"Ноты распознаны: {len(events)} событий")
            else:
                self.recognition_label.setText(f"MIDI: {len(events)} событий")
            self.recognition_progress.setRange(0, 100)
            self.recognition_progress.setValue(100)
        self.status.showMessage(
            f"Готово: {len(events)} событий, {self.duration:.1f} сек, Темп={bpm:.0f}"
        )

    def _on_status(self, text):
        self.status.showMessage(text)
        if not hasattr(self, "recognition_progress"):
            return
        if "Шаг 1/3" in text:
            self.recognition_label.setText("PDF: подготовка")
            self.recognition_progress.setRange(0, 100)
            self.recognition_progress.setValue(10)
        elif "Шаг 2/3" in text or "Audiveris распознаёт" in text:
            self.recognition_label.setText("Распознавание нот")
            self.recognition_progress.setRange(0, 0)  # Audiveris не сообщает точный процент
        elif "Шаг 3/3" in text:
            self.recognition_label.setText("Разбор нот")
            self.recognition_progress.setRange(0, 100)
            self.recognition_progress.setValue(80)

    # ---------- Управление воспроизведением ----------

    def _set_display_view(self, mode):
        if mode == "staff":
            self.chord_panel.setVisible(True)
            self.pdf_view.setVisible(False)
            self.pianoroll_view.setVisible(False)
            self.welcome_view.setVisible(False)
            self.staff_view.setVisible(True)
        elif mode == "roll":
            self.chord_panel.setVisible(False)
            self.pdf_view.setVisible(False)
            self.staff_view.setVisible(False)
            self.welcome_view.setVisible(False)
            self.pianoroll_view.setVisible(True)
        elif mode == "pdf":
            self.chord_panel.setVisible(True)
            self.staff_view.setVisible(False)
            self.pianoroll_view.setVisible(False)
            self.welcome_view.setVisible(False)
            self.pdf_view.setVisible(True)

    def _choose_bpm(self):
        value, accepted = QInputDialog.getInt(
            self, "\u0422\u0435\u043c\u043f",
            "\u0423\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c BPM:",
            int(self.current_bpm), 30, 200
        )
        if accepted:
            self.lbl_bpm.setValue(value)

    def _choose_keyboard_size(self):
        labels = ["88", "76", "61"]
        current = str(self.combo_keys.currentData())
        value, accepted = QInputDialog.getItem(
            self, "\u041a\u043b\u0430\u0432\u0438\u0430\u0442\u0443\u0440\u0430",
            "\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u043a\u043b\u0430\u0432\u0438\u0448:",
            labels, labels.index(current) if current in labels else 0, False
        )
        if accepted:
            index = self.combo_keys.findData(int(value))
            if index >= 0:
                self.combo_keys.setCurrentIndex(index)

    def on_play_only(self):
        if not self.is_playing:
            self.on_play_pause()

    def _sync_play_button(self):
        if self.is_playing:
            self.btn_play.setText("\u23f8")
            self.btn_play.setToolTip("?????")
        else:
            self.btn_play.setText("\u25b6")
            self.btn_play.setToolTip("?????????????")

    def on_play_pause(self):
        if self._training_active:
            self.status.showMessage("?????????? MIDI-?????????? ??? ???????? ???????????????")
            return
            QMessageBox.information(
                self,
                "Идёт распознавание нот",
                "Программа ещё распознаёт ноты и подготавливает партитуру.\n\n"
                "Дождитесь завершения распознавания, после этого нажмите Play ещё раз."
            )
            return
        if not self.events:
            self.status.showMessage("Нет партитуры — нажми «Открыть» и выбери PDF или MIDI")
            return
        if self.is_playing:
            self.is_playing = False
            self.btn_play.setText("▶")
            self.audio.all_off()
            self.status.showMessage("Пауза")
        else:
            # Если стоим в конце — начнём с начала
            if self.position >= self.duration - 0.01:
                self.position = 0.0
                self._next_event_idx = 0
            else:
                # Найти индекс следующего события от текущей позиции
                self._next_event_idx = 0
                for i, ev in enumerate(self.events):
                    if ev.time_seconds >= self.position:
                        self._next_event_idx = i
                        break
            self.staff_view._manual_view = False
            self.staff_view._dragging_cursor = False
            self.staff_view.update()
            self.is_playing = True
            self._elapsed.restart()

            self.btn_play.setText("⏸")
            self.status.showMessage("Играет")

    def on_stop(self):
        self.is_playing = False
        self._training_active = False
        self._training_waiting_for_correct = False
        self._training_event_idx = 0
        self._training_event_remaining.clear()

        if hasattr(self, "btn_training"):
            previous = self.btn_training.blockSignals(True)
            self.btn_training.setChecked(False)
            self.btn_training.blockSignals(previous)

        self.position = 0.0
        self._next_event_idx = 0
        self.btn_play.setText("\u25b6")
        self.audio.all_off()
        self.keyboard.set_active_notes(set(), set(), set())
        self.chord_left_label.setText("ЛЕВАЯ РУКА: —")
        self.chord_right_label.setText("ПРАВАЯ РУКА: —")
        self.pdf_view.clear_cursor()
        self.staff_view.set_position(0.0, set())
        self._update_time_label()
        self.status.showMessage("Стоп")
        self.btn_open.setEnabled(True)

    def on_rewind(self):
        self.position = 0.0
        self._next_event_idx = 0
        self.audio.all_off()
        self.keyboard.set_active_notes(set(), set(), set())
        self.pdf_view.clear_cursor()
        self.staff_view.set_position(0.0, set())
        self._update_time_label()
        self.status.showMessage("В начало")

    def on_loop(self, checked):
        self.loop_enabled = checked
        self.status.showMessage("Повтор включён" if checked else "Повтор выключен")

    def _set_keyboard_size_from_roll(self, count):
        index = self.combo_keys.findData(int(count))
        if index < 0:
            return
        if self.combo_keys.currentIndex() != index:
            self.combo_keys.setCurrentIndex(index)
        else:
            self.on_keys_changed(index)

    def on_keys_changed(self, index):
        preset = self.combo_keys.currentData()
        try:
            set_keyboard_size(preset)
        except Exception as e:
            self.status.showMessage(f'Ошибка смены диапазона: {e}')
            return
        self.keyboard.set_keyboard_size(preset)
        self.keyboard.update()
        low, num_keys = get_keyboard_range()
        self.pianoroll_view.set_keyboard_range(low, num_keys)
        QSettings('NowPiano', 'NowPiano').setValue('keyboard_size', preset)
        self.status.showMessage(f'Клавиатура: {preset} клавиш')


    def on_bpm(self, value):
        self.current_bpm = float(value)
        if self.slider_bpm.value() != int(value):
            self.slider_bpm.blockSignals(True)
            self.slider_bpm.setValue(int(value))
            self.slider_bpm.blockSignals(False)
        if self.lbl_bpm.value() != int(value):
            self.lbl_bpm.blockSignals(True)
            self.lbl_bpm.setValue(int(value))
            self.lbl_bpm.blockSignals(False)
        self.status.showMessage(f"Темп: {value}")

    def on_note_clicked(self, midi):
        if not self.audio_ok and self.audio.midi_out is None:
            return
        self.audio.note_on(midi, 110)
        self.audio.note_off_later(midi, 0.6)
        # Подсветка живёт ровно столько же, сколько звук (0.6 с).
        # Снимаем ТОЛЬКО эту ноту, не трогая другие активные.
        cur = set(self.keyboard.active_notes)
        cur.add(midi)
        cur_r = set(self.keyboard.right_notes)
        cur_l = set(self.keyboard.left_notes)
        if midi >= 60:
            cur_r.add(midi)
        else:
            cur_l.add(midi)
        self.keyboard.set_active_notes(cur, cur_r, cur_l)
        def _release(m=midi):
            n = set(self.keyboard.active_notes); n.discard(m)
            r = set(self.keyboard.right_notes); r.discard(m)
            l = set(self.keyboard.left_notes); l.discard(m)
            self.keyboard.set_active_notes(n, r, l)
        QTimer.singleShot(600, _release)

    # ---------- Таймер позиции ----------
    def _tick(self):
        if getattr(self, '_live_midi_score_active', False):
            self._refresh_live_score()
        if not self.is_playing:
            return

        # Точное время с момента последнего тика
        if not self._elapsed.isValid():
            self._elapsed.start()
        dt = self._elapsed.restart() / 1000.0
        if dt > 0.5:
            dt = 0.5

        speed = self.current_bpm / max(1.0, self.original_bpm)
        self.position += dt * speed

        # Догоняем события — если отстали, играем несколько подряд
        active_notes = set()
        now = self.position
        while self._next_event_idx < len(self.events):
            ev = self.events[self._next_event_idx]
            if ev.time_seconds > now:
                break
            velocity = 100 if ev.hand == "R" else 70
            for n in ev.notes:
                self.audio.note_on(n, velocity)
                self.audio.note_off_later(n, max(0.05, ev.duration))
                active_notes.add(n)
            self._next_event_idx += 1
        # Убираем старые вспышки (>0.15 c назад)

        # Подсветка активных
        still_active = set()
        still_active_right = set()
        still_active_left = set()
        for i in range(self._next_event_idx - 1, -1, -1):
            ev = self.events[i]
            ev_end = ev.time_seconds + max(0.05, ev.duration)
            if ev_end < self.position:
                break
            if ev.time_seconds <= self.position:
                still_active.update(ev.notes)
                if getattr(ev, 'hand', 'R') == 'R':
                    still_active_right.update(ev.notes)
                else:
                    still_active_left.update(ev.notes)
        self.keyboard.set_active_notes(still_active, still_active_right, still_active_left)
        # Распознаём аккорды каждой руки независимо.
        left_chord = chord_name(still_active_left)
        right_chord = chord_name(still_active_right)

        if left_chord:
            left_text = f"ЛЕВАЯ РУКА: {left_chord}"
        elif still_active_left:
            bass_note = min(still_active_left)
            left_text = f"ЛЕВАЯ РУКА: {note_name(bass_note)}"
        else:
            left_text = "ЛЕВАЯ РУКА: —"

        if right_chord:
            right_text = f"ПРАВАЯ РУКА: {right_chord}"
        elif still_active_right:
            note_list = " ".join(
                note_name(n, octave=False)
                for n in sorted(still_active_right)
            )
            right_text = f"ПРАВАЯ РУКА: {note_list}"
        else:
            right_text = "ПРАВАЯ РУКА: —"

        self.chord_left_label.setText(left_text)
        self.chord_right_label.setText(right_text)

        # MIDI: подсветить ноты, звучащие сейчас.
        try:
            self.staff_view.set_position(self.position, still_active, still_active_right, still_active_left)
        except Exception:
            pass
        # PDF: показываем приблизительную позицию события и названия звучащих нот.
        if self._last_pdf_path.lower().endswith('.pdf') and self._cursor_map:
            self._set_cursor_for_bar(getattr(self.events[max(0, self._next_event_idx - 1)], 'bar', 0))

        # Конец трека
        if self.position >= self.duration:
            if self.loop_enabled:
                self.position = 0.0
                self._next_event_idx = 0
                self._elapsed.restart()
                self.audio.all_off()
            else:
                self.is_playing = False
                self.btn_play.setText("▶")
                self.audio.all_off()
                self.keyboard.set_active_notes(set(), set(), set())
                self.chord_left_label.setText("ЛЕВАЯ РУКА: —")
                self.chord_right_label.setText("ПРАВАЯ РУКА: —")
                self.pdf_view.clear_cursor()
                self.status.showMessage("Готово")

        try:
            self.pianoroll_view.set_position(self.position)
        except Exception:
            pass
        self._update_kar_lyric()
        self._update_time_label()

    def _build_cursor_map(self, pixmap, events):
        """Раскладывает события по станам PDF. event_idx -> (page, x, y)."""
        result = {}
        if pixmap is None or not events:
            return result

        pw = float(pixmap.width())
        ph = float(pixmap.height())

        events_by_bar = {}
        for idx, ev in enumerate(events):
            events_by_bar.setdefault(ev.bar, []).append(idx)
        all_bars = sorted(events_by_bar.keys())
        if not all_bars:
            return result

        n_systems = 5
        top_m = ph * 0.08
        bot_m = ph * 0.08
        system_h = (ph - top_m - bot_m) / n_systems

        staves = []
        for i in range(n_systems):
            sys_top = top_m + i * system_h
            staves.append((sys_top + system_h * 0.05,
                           sys_top + system_h * 0.45, "R"))
            staves.append((sys_top + system_h * 0.55,
                           sys_top + system_h * 0.95, "L"))

        n_staves = len(staves)
        n_bars = len(all_bars)
        bars_per_staff = max(1, (n_bars + n_staves - 1) // n_staves)

        for s_idx, (staff_top, staff_bottom, hand) in enumerate(staves):
            y_mid = (staff_top + staff_bottom) / 2.0
            x_left = pw * 0.05
            x_right = pw * 0.95
            sb_start = s_idx * bars_per_staff
            staff_bars = all_bars[sb_start:sb_start + bars_per_staff]
            if not staff_bars:
                continue
            for b_idx, bar in enumerate(staff_bars):
                idxs = [i for i in events_by_bar.get(bar, [])
                        if events[i].hand == hand]
                if not idxs:
                    continue
                bar_w = (x_right - x_left) / max(1, len(staff_bars))
                bx_left = x_left + b_idx * bar_w
                bx_right = bx_left + bar_w
                n_ev = len(idxs)
                for k, ev_idx in enumerate(idxs):
                    frac = (k + 0.5) / n_ev
                    x = bx_left + frac * (bx_right - bx_left)
                    result[ev_idx] = (0, x, y_mid)

        print(f"[cursor] build map: {len(result)} points")
        return result

    def _set_cursor_for_bar(self, bar):
        """Курсор по текущей позиции self.position (секунды)."""
        if not self.events or not self._cursor_map:
            return

        idx = None
        for i, ev in enumerate(self.events):
            if ev.time_seconds <= self.position < ev.time_seconds + ev.duration:
                idx = i
                break
        if idx is None:
            self.pdf_view.clear_cursor()
            return

        if idx in self._cursor_map:
            pg, x, y = self._cursor_map[idx]
            self.pdf_view.set_cursor(x, y, page=pg, notes=self.events[idx].notes)
            return

        prev_i = next_i = None
        for i in range(idx, -1, -1):
            if i in self._cursor_map:
                prev_i = i
                break
        for i in range(idx, len(self.events)):
            if i in self._cursor_map:
                next_i = i
                break
        if prev_i is None and next_i is None:
            self.pdf_view.clear_cursor()
            return
        if prev_i is None:
            pg, x, y = self._cursor_map[next_i]
        elif next_i is None:
            pg, x, y = self._cursor_map[prev_i]
        else:
            pg1, x1, y1 = self._cursor_map[prev_i]
            pg2, x2, y2 = self._cursor_map[next_i]
            if pg1 != pg2:
                pg, x, y = self._cursor_map[prev_i]
            else:
                t1 = self.events[prev_i].time_seconds
                t2 = self.events[next_i].time_seconds
                k = 0.0 if t2 <= t1 else (self.position - t1) / (t2 - t1)
                k = max(0.0, min(1.0, k))
                pg = pg1
                x = x1 + (x2 - x1) * k
                y = y1 + (y2 - y1) * k
        self.pdf_view.set_cursor(x, y, page=pg, notes=self.events[idx].notes)

    # ---------- Прогресс-бар ----------
    def _progress_event_time(self, event):
        x = event.position().x() if hasattr(event, "position") else event.x()
        width = max(1, self.progress.width())
        frac = max(0.0, min(1.0, x / width))
        return frac * self.duration

    def _progress_click(self, event):
        if self.duration <= 0 or not self.events:
            return
        self._progress_dragging = True
        self._seek_to_time(self._progress_event_time(event))

    def _progress_move(self, event):
        if (getattr(self, "_progress_dragging", False)
                and event.buttons() & Qt.MouseButton.LeftButton):
            self._seek_to_time(self._progress_event_time(event))

    def _progress_release(self, event):
        if getattr(self, "_progress_dragging", False):
            self._seek_to_time(self._progress_event_time(event))
            self._progress_dragging = False

    def _seek_to_time(self, seconds):
        if self._training_active:
            return
            return

        self.is_playing = False
        self.btn_play.setText("\u25b6")
        self.audio.all_off()
        self.position = max(0.0, min(self.duration, float(seconds)))
        self._elapsed.restart()

        self._next_event_idx = len(self.events)
        for i, ev in enumerate(self.events):
            if ev.time_seconds >= self.position:
                self._next_event_idx = i
                break

        active = set()
        active_right = set()
        active_left = set()

        for ev in self.events:
            if ev.time_seconds > self.position:
                break
            if self.position <= ev.time_seconds + ev.duration:
                for n in ev.notes:
                    active.add(n)
                    if getattr(ev, "hand", "R") == "R":
                        active_right.add(n)
                    else:
                        active_left.add(n)

        self.keyboard.set_active_notes(active, active_right, active_left)

        left_chord = chord_name(active_left)
        right_chord = chord_name(active_right)

        if left_chord:
            left_text = f"\u041b\u0415\u0412\u0410\u042f \u0420\u0423\u041a\u0410: {left_chord}"
        elif active_left:
            left_text = f"\u041b\u0415\u0412\u0410\u042f \u0420\u0423\u041a\u0410: \u0411\u0430\u0441 {note_name(min(active_left))}"
        else:
            left_text = "\u041b\u0415\u0412\u0410\u042f \u0420\u0423\u041a\u0410: \u2014"

        if right_chord:
            right_text = f"\u041f\u0420\u0410\u0412\u0410\u042f \u0420\u0423\u041a\u0410: {right_chord}"
        elif active_right:
            right_text = "\u041f\u0420\u0410\u0412\u0410\u042f \u0420\u0423\u041a\u0410: " + " ".join(
                note_name(n, octave=False) for n in sorted(active_right)
            )
        else:
            right_text = "\u041f\u0420\u0410\u0412\u0410\u042f \u0420\u0423\u041a\u0410: \u2014"

        self.chord_left_label.setText(left_text)
        self.chord_right_label.setText(right_text)

        try:
            self.staff_view.set_position(
                self.position, active, active_right, active_left
            )
        except Exception:
            pass

        if self._last_pdf_path.lower().endswith(".pdf") and self._cursor_map:
            idx = min(
                range(len(self.events)),
                key=lambda i: abs(self.events[i].time_seconds - self.position)
            )
            self._set_cursor_for_bar(getattr(self.events[idx], "bar", 0))

        try:
            self.pianoroll_view.set_position(self.position)
        except Exception:
            pass

        self._update_kar_lyric()
        self._update_time_label()
        self.status.showMessage("\u041f\u0430\u0443\u0437\u0430 \u2014 \u043f\u043e\u0437\u0438\u0446\u0438\u044f \u0432\u044b\u0431\u0440\u0430\u043d\u0430")

    def _update_time_label(self):
        def fmt(s):
            s = max(0, int(s))
            return f"{s // 60:02d}:{s % 60:02d}"
        self.lbl_time.setText(f"{fmt(self.position)} / {fmt(self.duration)}")
        if self.duration > 0:
            self.progress.setValue(int(1000 * self.position / self.duration))


    def _set_kar_lyrics(self, gen, lyrics):
        """Принимает текстовые события KAR из фонового загрузчика."""
        if gen != self._load_gen:
            return
        self._kar_lyrics = sorted(
            [(float(t), str(text)) for t, text in (lyrics or [])],
            key=lambda item: item[0]
        )
        self._kar_lyric_times = [item[0] for item in self._kar_lyrics]
        self._kar_last_rendered_idx = None
        self._update_kar_lyric()

    def _update_kar_lyric(self):
        """Displays one continuous karaoke line and scrolls to the active fragment."""
        if not self._kar_lyrics:
            self.kar_lyric_label.clear()
            self.kar_lyric_label.setVisible(False)
            self._kar_last_rendered_idx = None
            return

        idx = bisect_right(self._kar_lyric_times, float(self.position)) - 1
        if idx == getattr(self, "_kar_last_rendered_idx", None):
            return

        self.kar_lyric_label.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.kar_lyric_label.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        parts = []
        plain_pos = 0
        current_cursor_pos = 0
        previous_text = ""

        for i, (_, raw_text) in enumerate(self._kar_lyrics):
            fragment = str(raw_text)

            if fragment.startswith(("/", "\\")):
                fragment = fragment[1:]
                if previous_text and not previous_text[-1].isspace():
                    if fragment and not fragment[0].isspace():
                        parts.append("&nbsp;")
                        plain_pos += 1

            if not fragment:
                continue

            safe = html_escape(fragment).replace(" ", "&nbsp;")
            if i == idx:
                current_cursor_pos = plain_pos + max(0, (len(fragment) - 1) // 2)
                parts.append(
                    '<span style="background-color:#f4d34e; color:#172033; '
                    'border-radius:4px; padding:2px 3px;">'
                    + safe + '</span>'
                )
            else:
                parts.append('<span style="color:#e8edf5;">' + safe + '</span>')

            plain_pos += len(fragment)
            previous_text += fragment

        if idx < 0:
            heading = '<span style="color:#91a0b5;">??????? ? ???????? ?????? ?????</span>&nbsp;&nbsp;'
        else:
            heading = ""

        document = (
            '<html><body style="font-family:Segoe UI,Arial; '
            'font-size:21px; color:#e8edf5;">'
            '<div style="white-space:nowrap;">'
            + heading + "".join(parts) +
            '</div></body></html>'
        )

        self.kar_lyric_label.setHtml(document)
        self.kar_lyric_label.setVisible(True)

        if idx >= 0:
            cursor = self.kar_lyric_label.textCursor()
            cursor.setPosition(min(
                current_cursor_pos,
                self.kar_lyric_label.document().characterCount() - 1
            ))
            self.kar_lyric_label.setTextCursor(cursor)

            # ?????? ???????? ???????? ????? ?? ?????? ??????? ???????.
            cursor_rect = self.kar_lyric_label.cursorRect(cursor)
            viewport_width = self.kar_lyric_label.viewport().width()
            scrollbar = self.kar_lyric_label.horizontalScrollBar()

            target = (
                scrollbar.value()
                + cursor_rect.center().x()
                - viewport_width // 2
            )
            target = max(scrollbar.minimum(), min(scrollbar.maximum(), target))
            scrollbar.setValue(target)

        self._kar_last_rendered_idx = idx

    def _handle_file_drop_event(self, event, open_file=False):
        """????? ????????? ?????????????? ?????? ?? ??????????."""
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            return False

        supported = (
            ".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff",
            ".bmp", ".mid", ".midi", ".kar", ".mxl",
            ".musicxml", ".xml"
        )

        paths = []
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if os.path.splitext(path)[1].lower() in supported:
                paths.append(path)

        if not paths:
            return False

        if open_file:
            self._open_path(paths[0])

        event.acceptProposedAction()
        return True

    def dragEnterEvent(self, event):
        if self._handle_file_drop_event(event, False):
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._handle_file_drop_event(event, False):
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if self._handle_file_drop_event(event, True):
            return
        super().dropEvent(event)

    def eventFilter(self, watched, event):
        """????????? ?????, ??????????????? ?? ???????? ???????? ????."""
        if event.type() in (
            QEvent.Type.DragEnter,
            QEvent.Type.DragMove
        ):
            if self._handle_file_drop_event(event, False):
                return True

        elif event.type() == QEvent.Type.Drop:
            if self._handle_file_drop_event(event, True):
                return True

        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        """Увеличиваем высоту клавиш на больших/полноэкранных окнах."""
        super().resizeEvent(event)
        if hasattr(self, "keyboard"):
            target = max(285, min(390, int(self.height() * 0.34)))
            self.keyboard.setFixedHeight(target)

    # ---------- Горячие клавиши ----------
    def keyPressEvent(self, event):
        k = event.key()
        if k == Qt.Key.Key_Space:
            self.on_play_pause()
        elif k == Qt.Key.Key_S:
            self.on_stop()
        elif k == Qt.Key.Key_Left:
            self.position = max(0.0, self.position - 5.0)
            self._update_time_label()
        elif k == Qt.Key.Key_Right:
            self.position = min(self.duration, self.position + 5.0)
            self._update_time_label()
        elif k == Qt.Key.Key_Home:
            self.on_rewind()
        else:
            super().keyPressEvent(event)

    def on_export_midi(self):
        """Экспорт текущей партитуры в MIDI."""
        if not self._last_mxl:
            QMessageBox.information(self, "Нет данных",
                                    "Сначала загрузите PDF или MIDI.")
            return
        default_name = "NowPiano_export.mid"
        if self._last_pdf_path:
            base = os.path.splitext(os.path.basename(self._last_pdf_path))[0]
            default_dir = os.path.dirname(self._last_pdf_path)
            default_name = os.path.join(default_dir, base + ".mid")
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить MIDI", default_name, "MIDI (*.mid);;Все файлы (*.*)"
        )
        if not out_path:
            return
        ok = export_midi(self._last_mxl, out_path, bpm=self.current_bpm)
        if ok:
            self.status.showMessage(f"MIDI сохранён: {out_path}")
            QMessageBox.information(self, "Готово", f"MIDI сохранён:\n{out_path}")
        else:
            self.status.showMessage("Ошибка экспорта MIDI")
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить MIDI.")
    def _load_midi_worker(self, path, gen):
        """Загрузка MIDI/KAR без Audiveris и PDF."""
        if gen != self._load_gen:
            return
        is_kar = path.lower().endswith(".kar")
        try:
            self.sig_status.emit("Загрузка текста караоке..." if is_kar else "Загрузка MIDI...")
            if is_kar:
                try:
                    lyrics = load_kar_lyrics(path)
                except Exception:
                    lyrics = []
                if gen != self._load_gen:
                    return
                self.sig_lyrics_loaded.emit(gen, lyrics)

            try:
                events, bpm = load_midi_events(path)
            except Exception:
                if not is_kar:
                    raise
                events, bpm = load_kar_note_events(path)

            self._last_mxl = path
            self._last_pdf_path = path
            if gen != self._load_gen:
                return
            self.sig_load_done.emit(events, bpm, "")
        except Exception as e:
            if gen != self._load_gen:
                return
            self.sig_load_done.emit(None, MANUAL_BPM, f"Ошибка MIDI/KAR: {e}")
    def _show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("О программе NowPiano")
        dialog.setMinimumWidth(380)
        layout = QVBoxLayout(dialog)

        title = QLabel("NowPiano")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        description = QLabel(
            "Распознавание нот из PDF и изображений,\n"
            "просмотр партитуры и воспроизведение музыки."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)

        qr_path = resource_path(os.path.join("resources", "donate_qr.png"))
        if os.path.isfile(qr_path):
            pixmap = QPixmap(qr_path)
            if not pixmap.isNull():
                qr = QLabel()
                qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
                qr.setPixmap(pixmap.scaled(
                    220, 220,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                layout.addWidget(qr)
            else:
                layout.addWidget(QLabel("Не удалось загрузить QR-код."))
        else:
            layout.addWidget(QLabel("QR-код не найден: resources/donate_qr.png"))

        link = QLabel(
            '<a href="https://github.com/BlaSla/NowPiano">'
            'GitHub: BlaSla/NowPiano</a>'
        )
        link.setOpenExternalLinks(True)
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(link)

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()


    def _refresh_live_score(self):
        if not getattr(self, "_live_midi_score_active", False):
            return

        records = self.midi_recorder.snapshot()
        bpm = max(1.0, float(getattr(self, "current_bpm", 72.0)))
        quarter_per_second = bpm / 60.0

        events = []
        latest_end = 0.0

        for item in records:
            note = int(item["note"])
            start = max(0.0, float(item["start"]))
            duration = max(0.0, float(item["duration"]))
            end = start + duration
            latest_end = max(latest_end, end)

            quarter_position = start * quarter_per_second
            bar = int(quarter_position // 4.0) + 1
            offset_q = quarter_position % 4.0
            hand = "L" if note < 60 else "R"

            events.append(NoteEvent(
                bar=bar,
                offset_q=offset_q,
                time_seconds=start,
                notes=[note],
                duration=max(0.08, duration),
                hand=hand,
                part=0,
                note_names={note: note_name(note)}
            ))

        events.sort(key=lambda ev: (ev.time_seconds, ev.notes[0]))

        position = max(0.0, float(self.midi_recorder.duration))
        total_duration = max(0.01, position, latest_end)

        self.staff_view.events = events
        self.staff_view.duration = total_duration

        active = set(getattr(self, "_midi_notes", set()))
        right = {n for n in active if n >= 60}
        left = {n for n in active if n < 60}

        self.staff_view.set_position(
            position,
            active_notes=active,
            right_notes=right,
            left_notes=left
        )
        self.staff_view.update()


    def _record_start(self):
        midi_input = getattr(self, "midi_input", None)
        if midi_input is None or not midi_input.connected:
            QMessageBox.information(
                self,
                "MIDI ?? ?????????",
                "??????? ?????????? MIDI-?????????? ? ???? MIDI."
            )
            return

        self.midi_recorder.start()
        self._live_midi_score_active = True

        self.staff_view.set_events([], 0.01)
        self.staff_view._live_recording = True
        self.staff_view._manual_view = False
        self.staff_view._dragging_cursor = False

        self._set_display_view("staff")
        self.act_record_export.setEnabled(False)
        self.act_record_pdf_export.setEnabled(False)
        self.status.showMessage(
            "?????? MIDI ???????? ? ????????? ???? ???????? ?? ?????? ?????"
        )
        self._refresh_live_score()

    def _record_pause(self):
        if self.midi_recorder.state == "recording":
            self.midi_recorder.pause()
            self.status.showMessage("?????? MIDI ??????????????")
        elif self.midi_recorder.state == "paused":
            self.midi_recorder.resume()
            self.status.showMessage("?????? MIDI ????????????")
        else:
            self.status.showMessage("??????? ?????? MIDI")


    def _record_stop(self):
        if self.midi_recorder.state == "stopped":
            self.status.showMessage("?????? MIDI ?? ???????????")
            return

        notes = self.midi_recorder.stop()
        self._refresh_live_score()
        self._live_midi_score_active = False
        self.staff_view._live_recording = False
        self.staff_view.update()

        self.act_record_export.setEnabled(bool(notes))
        self.act_record_pdf_export.setEnabled(bool(notes))
        self.status.showMessage(
            f"???????? ???: {len(notes)}"
        )


    def _record_export_pdf(self):
        if self.midi_recorder.state != "stopped":
            QMessageBox.information(
                self, "\u0417\u0430\u043f\u0438\u0441\u044c \u0435\u0449\u0451 \u0438\u0434\u0451\u0442",
                "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0438\u0442\u0435 MIDI-\u0437\u0430\u043f\u0438\u0441\u044c."
            )
            return

        records = self.midi_recorder.snapshot()
        if not records:
            QMessageBox.information(
                self, "\u041d\u0435\u0442 \u043d\u043e\u0442",
                "\u0412 \u0437\u0430\u043f\u0438\u0441\u0438 \u043d\u0435\u0442 \u043d\u043e\u0442 \u0434\u043b\u044f \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u044f."
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u043d\u043e\u0442\u043d\u0443\u044e \u043f\u0430\u0440\u0442\u0438\u0442\u0443\u0440\u0443",
            "NowPiano_performance.pdf",
            "PDF (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        try:
            import subprocess
            import tempfile
            from pathlib import Path
            from music21 import stream, note, meter, clef, tempo

            bpm = float(self.current_bpm)
            if not 20.0 <= bpm <= 400.0:
                raise ValueError("BPM ?????? ???? ?? 20 ?? 400.")

            score = stream.Score()
            score.insert(0, tempo.MetronomeMark(number=bpm))

            for hand, part_name, staff_clef in [
                ("R", "Right Hand", clef.TrebleClef()),
                ("L", "Left Hand", clef.BassClef()),
            ]:
                part = stream.Part()
                part.partName = part_name
                part.insert(0, staff_clef)
                part.insert(0, meter.TimeSignature("4/4"))

                # Insert notes directly into the part.
                # Manual makeMeasures()/Voice nesting caused MuseScore to fail
                # on dense live recordings (exit code 1320).
                for item in records:
                    pitch = int(item["note"])
                    if (hand == "L" and pitch >= 60) or (hand == "R" and pitch < 60):
                        continue

                    start_q = max(0.0, float(item["start"])) * bpm / 60.0
                    start_q = round(start_q * 16.0) / 16.0

                    duration_q = max(0.0, float(item["duration"])) * bpm / 60.0
                    duration_q = max(1.0 / 16.0, round(duration_q * 16.0) / 16.0)

                    n = note.Note()
                    n.pitch.midi = pitch
                    n.duration.quarterLength = duration_q
                    part.insert(start_q, n)

                score.append(part)

            exe_candidates = [
                Path(r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe")
            ]
            try:
                from music21 import environment
                configured = environment.UserSettings()["musicxmlPath"]
                if configured:
                    exe_candidates.insert(0, Path(configured))
            except Exception:
                pass

            exe = next((p for p in exe_candidates if p.is_file()), None)
            if exe is None:
                raise FileNotFoundError("?? ?????? MuseScore4.exe.")

            output_path = Path(path)
            with tempfile.TemporaryDirectory(prefix="nowpiano_score_") as td:
                mx_path = Path(td) / "performance.musicxml"
                score.write("musicxml", fp=str(mx_path))

                # MuseScore requires voice numbers to start at 1.
                # music21 may export voices as 0, 1, 2; remap them
                # consistently while preserving their separation.
                import xml.etree.ElementTree as ET

                xml_tree = ET.parse(mx_path)
                xml_root = xml_tree.getroot()

                def _xml_local_name(tag):
                    return tag.rsplit("}", 1)[-1]

                voice_elements = [
                    element for element in xml_root.iter()
                    if _xml_local_name(element.tag) == "voice"
                    and element.text is not None
                ]

                voice_order = list(dict.fromkeys(
                    element.text.strip() for element in voice_elements
                ))
                voice_mapping = {
                    old_voice: str(index + 1)
                    for index, old_voice in enumerate(voice_order)
                }

                for element in voice_elements:
                    element.text = voice_mapping[element.text.strip()]

                xml_tree.write(
                    mx_path,
                    encoding="utf-8",
                    xml_declaration=True
                )

                result = subprocess.run(
                    [str(exe), "-o", str(output_path), str(mx_path)],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )

                if result.returncode != 0:
                    details = (result.stderr or result.stdout or "").strip()
                    raise RuntimeError(
                        "MuseScore ?????????? ? ???????: " + details[-1800:]
                    )

            if not output_path.is_file() or output_path.stat().st_size < 1000:
                raise RuntimeError("MuseScore ?? ?????? ?????????? PDF-????.")

        except Exception as exc:
            QMessageBox.warning(
                self, "\u041e\u0448\u0438\u0431\u043a\u0430 PDF",
                "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u043f\u0430\u0440\u0442\u0438\u0442\u0443\u0440\u0443:\n" + str(exc)
            )
            return

        self.status.showMessage(
            f"PDF \u043f\u0430\u0440\u0442\u0438\u0442\u0443\u0440\u044b \u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d: {path}",
            8000
        )
        QMessageBox.information(
            self, "\u0413\u043e\u0442\u043e\u0432\u043e",
            f"\u041f\u0430\u0440\u0442\u0438\u0442\u0443\u0440\u0430 PDF \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0430:\n{path}\n\n"
            f"\u0417\u0430\u043f\u0438\u0441\u0430\u043d\u043e \u043d\u043e\u0442: {len(records)}"
        )

    def _record_export(self):
        if self.midi_recorder.state != "stopped":
            QMessageBox.information(
                self, "?????????? MIDI",
                "??????? ????????? ??????."
            )
            return

        if not self.midi_recorder.snapshot():
            QMessageBox.information(
                self, "??? ???", "? ?????? ???? ??? ???."
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "????????? MIDI-??????",
            "NowPiano_performance.mid",
            "MIDI (*.mid)"
        )
        if not path:
            return
        if not path.lower().endswith(".mid"):
            path += ".mid"

        try:
            count = self.midi_recorder.export_midi(
                path, bpm=float(self.current_bpm)
            )
        except Exception as exc:
            QMessageBox.warning(self, "?????? ??????????", str(exc))
            return

        self.status.showMessage(
            f"MIDI-?????? ?????????: {path} ({count} ???)"
        )
        QMessageBox.information(
            self, "??????",
            f"????????? ???: {count}\n????: {path}"
        )

    def _init_midi_input(self):
        """Подключает MIDI-сигналы к интерфейсу."""
        from PyQt6.QtCore import QTimer

        if not hasattr(self, "midi_input"):
            from qt_midi_input import MidiInput
            self.midi_input = MidiInput(self)

        self._midi_notes = set()
        self.midi_input.status_changed.connect(self._on_midi_status)
        self.midi_input.note_on.connect(self._on_midi_note_on)
        self.midi_input.note_off.connect(self._on_midi_note_off)

        QTimer.singleShot(700, self._midi_auto_connect)

    def _on_midi_status(self, message):
        self.status.showMessage(message, 5000)
        if hasattr(self, "btn_midi_input"):
            self.btn_midi_input.setText(f"MIDI IN : {self.midi_input.port_name}" if self.midi_input.connected else "MIDI IN")

    def _on_midi_note_on(self, note, velocity, channel):
        note = int(note)
        self.midi_recorder.note_on(note, velocity, channel)
        already_held = note in self._midi_notes
        self._midi_notes.add(note)
        if hasattr(self, 'keyboard'):
            self.keyboard.set_midi_notes(self._midi_notes)
        if not already_held and self._training_active:
            self._check_training_note(note)

    def _on_midi_note_off(self, note, channel):
        self.midi_recorder.note_off(note, channel)
        if not self.midi_input.is_note_held(note):
            self._midi_notes.discard(int(note))
        if hasattr(self, "keyboard"):
            self.keyboard.set_midi_notes(self._midi_notes)

    def _prepare_training_event(self):
        if not self._training_active:
            return

        events = self.events or []
        idx = int(getattr(self, "_training_event_idx", 0))

        while idx < len(events):
            first_event = events[idx]
            first_time = float(first_event.time_seconds)
            group_end = idx

            notes = set()
            right_notes = set()
            left_notes = set()

            # ?????????? ??????? ????? ??? ? ??????????? ?????????? ????????.
            while group_end < len(events):
                ev = events[group_end]
                ev_time = float(ev.time_seconds)

                if abs(ev_time - first_time) > 0.02:
                    break

                ev_notes = {int(n) for n in (ev.notes or [])}
                notes.update(ev_notes)

                if getattr(ev, "hand", "R") == "L":
                    left_notes.update(ev_notes)
                else:
                    right_notes.update(ev_notes)

                group_end += 1

            if not notes:
                idx = group_end
                self._training_event_idx = idx
                continue

            self._training_event_idx = idx
            self._training_event_end_idx = group_end
            self._training_event_remaining = set(notes)
            self.position = first_time
            self._next_event_idx = group_end

            self.audio.all_off()
            self.keyboard.set_active_notes(notes, right_notes, left_notes)
            self.staff_view._manual_view = False
            self.staff_view._dragging_cursor = False
            self.staff_view.set_position(
                self.position, notes, right_notes, left_notes
            )

            left_chord = chord_name(left_notes)
            right_chord = chord_name(right_notes)

            self.chord_left_label.setText(
                f"\u041b\u0435\u0432\u0430\u044f \u0440\u0443\u043a\u0430: {left_chord}" if left_chord else
                (f"\u041b\u0435\u0432\u0430\u044f \u0440\u0443\u043a\u0430: {note_name(min(left_notes))}"
                 if left_notes else "\u041b\u0435\u0432\u0430\u044f \u0440\u0443\u043a\u0430: \u2014")
            )
            self.chord_right_label.setText(
                f"\u041f\u0440\u0430\u0432\u0430\u044f \u0440\u0443\u043a\u0430: {right_chord}" if right_chord else
                ("\u041f\u0440\u0430\u0432\u0430\u044f \u0440\u0443\u043a\u0430: " + " ".join(
                    note_name(n, octave=False) for n in sorted(right_notes)
                ) if right_notes else "\u041f\u0440\u0430\u0432\u0430\u044f \u0440\u0443\u043a\u0430: \u2014")
            )

            if self._last_pdf_path.lower().endswith(".pdf") and self._cursor_map:
                self._set_cursor_for_bar(getattr(first_event, "bar", 0))

            try:
                self.pianoroll_view.set_position(self.position)
            except Exception:
                pass

            expected = ", ".join(str(n) for n in sorted(notes))
            self.status.showMessage(
                f"\u0410\u043a\u043a\u043e\u0440\u0434 {idx + 1}/"
                f"{len(events)}. \u041e\u0436\u0438\u0434\u0430\u044e MIDI-\u043d\u043e\u0442\u044b: {expected}"
            )
            self._update_time_label()
            return

        self._training_active = False
        self._training_event_remaining = set()
        self.is_playing = False
        self.audio.all_off()
        self.btn_play.setText("\u25b6")
        self.keyboard.set_active_notes(set(), set(), set())
        self.staff_view.set_position(self.position, set(), set(), set())
        self.chord_left_label.setText("\u041b\u0435\u0432\u0430\u044f \u0440\u0443\u043a\u0430: \u2014")
        self.chord_right_label.setText("\u041f\u0440\u0430\u0432\u0430\u044f \u0440\u0443\u043a\u0430: \u2014")

        previous = self.btn_training.blockSignals(True)
        self.btn_training.setChecked(False)
        self.btn_training.blockSignals(previous)
        self.status.showMessage(
            f"\u0422\u0440\u0435\u043d\u0438\u0440\u043e\u0432\u043a\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430. "
            f"\u0412\u0435\u0440\u043d\u043e: {self._training_correct}; "
            f"\u043e\u0448\u0438\u0431\u043e\u043a: {self._training_errors}"
        )


    def _toggle_midi_training(self, checked):
        if checked:
            if not getattr(self, "events", None):
                previous = self.btn_training.blockSignals(True)
                self.btn_training.setChecked(False)
                self.btn_training.blockSignals(previous)
                self.status.showMessage(
                    "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u0435 \u043f\u0430\u0440\u0442\u0438\u0442\u0443\u0440\u0443"
                )
                return

            self.is_playing = False
            self.audio.all_off()
            self.btn_play.setText("\u25b6")
            self._training_active = True
            self._training_event_idx = 0
            self._training_event_end_idx = 0
            self._training_event_remaining = set()
            self._training_correct = 0
            self._training_errors = 0
            self.position = 0.0
            self._next_event_idx = 0
            self._elapsed.restart()
            self.staff_view._manual_view = False
            self.staff_view._dragging_cursor = False
            self._prepare_training_event()
        else:
            self._training_active = False
            self._training_event_remaining = set()
            self.audio.all_off()
            self.keyboard.set_active_notes(set(), set(), set())
            self.staff_view.set_position(self.position, set(), set(), set())
            self.chord_left_label.setText("\u041b\u0435\u0432\u0430\u044f \u0440\u0443\u043a\u0430: \u2014")
            self.chord_right_label.setText("\u041f\u0440\u0430\u0432\u0430\u044f \u0440\u0443\u043a\u0430: \u2014")
            self.status.showMessage(
                f"\u0422\u0440\u0435\u043d\u0438\u0440\u043e\u0432\u043a\u0430 \u043e\u0442\u043a\u043b\u044e\u0447\u0435\u043d\u0430. "
                f"\u0412\u0435\u0440\u043d\u043e: {self._training_correct}; "
                f"\u043e\u0448\u0438\u0431\u043e\u043a: {self._training_errors}"
            )




    def _check_training_note(self, note):
        if not self._training_active or not self._training_event_remaining:
            return

        note = int(note)

        if note in self._training_event_remaining:
            self._training_event_remaining.remove(note)
            self._training_correct += 1

            if not self._training_event_remaining:
                # ????????? ????? ??? ?????? ????????????? ??????? ????? ???.
                self._training_event_idx = self._training_event_end_idx
                self._prepare_training_event()
            else:
                self.status.showMessage(
                    f"\u0412\u0435\u0440\u043d\u043e! \u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c \u043d\u043e\u0442: "
                    f"{len(self._training_event_remaining)}"
                )
        else:
            self._training_errors += 1
            expected = ", ".join(
                str(n) for n in sorted(self._training_event_remaining)
            )
            self.status.showMessage(
                f"\u041d\u0435\u0432\u0435\u0440\u043d\u0430\u044f \u043d\u043e\u0442\u0430: {note}. "
                f"\u041e\u0448\u0438\u0431\u043e\u043a: {self._training_errors}. "
                f"\u041e\u0436\u0438\u0434\u0430\u044e: {expected}"
            )


    def _midi_auto_connect(self):
        from PyQt6.QtCore import QSettings

        ports = self.midi_input.available_ports()
        if not ports:
            return

        settings = QSettings("NowPiano", "NowPiano")
        last_port = settings.value("midi_input/last_port", "", type=str)
        selected = last_port if last_port in ports else ports[0]
        if self.midi_input.connect_port(selected):
            settings.setValue("midi_input/last_port", selected)

    def _show_midi_dialog(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("Настройка MIDI-входа")
        dialog.setMinimumWidth(380)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Выберите MIDI-клавиатуру:"))

        combo = QComboBox()
        ports = self.midi_input.available_ports()
        combo.addItems(ports)
        if self.midi_input.port_name in ports:
            combo.setCurrentText(self.midi_input.port_name)
        layout.addWidget(combo)

        status = QLabel(
            "Подключено: " + self.midi_input.port_name
            if self.midi_input.connected else "MIDI не подключён"
        )
        layout.addWidget(status)

        buttons = QHBoxLayout()
        connect_button = QPushButton("Подключить")
        disconnect_button = QPushButton("Отключить")
        close_button = QPushButton("Закрыть")

        buttons.addWidget(connect_button)
        buttons.addWidget(disconnect_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        def connect_selected():
            name = combo.currentText().strip()
            if self.midi_input.connect_port(name):
                from PyQt6.QtCore import QSettings
                QSettings("NowPiano", "NowPiano").setValue(
                    "midi_input/last_port", name
                )
                status.setText("Подключено: " + name)
            else:
                status.setText("Не удалось подключить MIDI")

        def disconnect():
            self.midi_input.disconnect_port()
            status.setText("MIDI не подключён")

        connect_button.clicked.connect(connect_selected)
        disconnect_button.clicked.connect(disconnect)
        close_button.clicked.connect(dialog.accept)
        dialog.exec()

    def _show_midi_out_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 MIDI OUT")
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 MIDI-\u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e \u0434\u043b\u044f \u0432\u044b\u0432\u043e\u0434\u0430:"))
        combo = QComboBox()
        ports = self.audio.get_output_names()
        combo.addItems(ports)

        settings = QSettings("NowPiano", "NowPiano")
        last_port = settings.value("midi_output/last_port", "")
        if last_port in ports:
            combo.setCurrentText(last_port)
        elif self.audio.midi_out_name in ports:
            combo.setCurrentText(self.audio.midi_out_name)
        layout.addWidget(combo)

        status = QLabel(
            "\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u043e: " + self.audio.midi_out_name
            if self.audio.midi_out is not None else "MIDI OUT \u043d\u0435 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0451\u043d"
        )
        layout.addWidget(status)

        buttons = QHBoxLayout()
        connect_button = QPushButton("\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c")
        disconnect_button = QPushButton("\u041e\u0442\u043a\u043b\u044e\u0447\u0438\u0442\u044c")
        close_button = QPushButton("\u0417\u0430\u043a\u0440\u044b\u0442\u044c")
        buttons.addWidget(connect_button)
        buttons.addWidget(disconnect_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        def connect_selected():
            name = combo.currentText()
            if not name:
                QMessageBox.warning(dialog, "MIDI OUT", "\u041d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d MIDI-\u0432\u044b\u0445\u043e\u0434.")
                return
            if self.audio.open_output(name):
                settings.setValue("midi_output/last_port", name)
                status.setText("\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u043e: " + name)
                self.btn_midi_output.setText("MIDI OUT: " + name)
                self.status.showMessage("MIDI OUT \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0451\u043d: " + name, 5000)
            else:
                status.setText("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c: " + name)
                QMessageBox.warning(dialog, "MIDI OUT", "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043a\u0440\u044b\u0442\u044c MIDI-\u043f\u043e\u0440\u0442.")

        def disconnect_output():
            self.audio.close_output()
            status.setText("MIDI OUT \u043d\u0435 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0451\u043d")
            self.btn_midi_output.setText("MIDI OUT: \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435...")
            self.status.showMessage("MIDI OUT \u043e\u0442\u043a\u043b\u044e\u0447\u0451\u043d", 5000)

        connect_button.clicked.connect(connect_selected)
        disconnect_button.clicked.connect(disconnect_output)
        close_button.clicked.connect(dialog.accept)
        dialog.exec()

    def closeEvent(self, event):
        self.is_playing = False
        try:
            if hasattr(self, "midi_input"):
                self.midi_input.disconnect_port()
        except Exception:
            pass
        try:
            self.audio.shutdown()
        except Exception:
            pass
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    _ico = resource_path(os.path.join("resources", "app_icon.ico"))
    _png = resource_path(os.path.join("resources", "app_icon.png"))
    _icon_file = _ico if os.path.isfile(_ico) else _png
    if os.path.isfile(_icon_file):
        app.setWindowIcon(QIcon(_icon_file))

    win = PianoWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


