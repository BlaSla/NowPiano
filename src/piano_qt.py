# -*- coding: utf-8 -*-
"""piano_qt.py - NowPiano на PyQt6. Полная сборка: PDF, Audiveris, звук, клавиатура."""

import os
import sys
import time
import threading

from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QElapsedTimer, QRectF
from PyQt6.QtGui import QAction, QKeySequence, QFont, QPixmap, QImage, QPainter, QPen, QBrush, QColor, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QProgressBar, QToolBar, QStatusBar,
    QSizePolicy, QFileDialog, QMessageBox, QSpinBox, QDialog
)

# --- PyInstaller windowed mode fix: sys.stdout/stderr = None ---
if getattr(sys, "frozen", False):
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
from qt_audio import (
    AudioEngine, run_audiveris, run_homr, run_homr_image, recognize_tempo_from_image, _image_to_pdf, musicxml_to_events,
    total_duration, NoteEvent, MANUAL_BPM, START_NOTE, NUM_KEYS,
    SOUNDFONT_PATH, AUDIVERIS_EXE,
    export_midi, load_midi_events, render_score_to_pngs
)
from qt_render import KeyboardView, PdfView, WelcomeView
from qt_pianoroll import PianoRollView


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
    padding: 6px 10px;
    spacing: 6px;
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
        p.setPen(self.RIGHT); p.drawText(max(180, w-260), 22, '● Правая рука')
        p.setPen(self.LEFT); p.drawText(max(300, w-130), 22, '● Левая рука')
        if not self.events:
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
            p.setFont(QFont('Segoe UI', 8)); p.drawText(left, int(y0-7), 'ПРАВАЯ РУКА' if clef=='treble' else 'ЛЕВАЯ РУКА')

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
    sig_page_ready = pyqtSignal(object)              # QPixmap

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NowPiano")
        self.resize(1400, 860)
        self.setMinimumSize(1000, 700)

        # Иконка окна
        _icon_path = os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            os.pardir, "resources", "app_icon.png"
        ))
        if os.path.exists(_icon_path):
            self.setWindowIcon(QIcon(_icon_path))

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
        self._flash_notes = {}  # midi -> время старта (для вспышки на клавише)
        self._flash_notes = {}  # midi -> время старта (для вспышки на клавише)
        self._elapsed.start()
        self._cursor_map: dict = {}
        self._last_mxl: str = ''
        self._last_pdf_path: str = ''
        self._pdf_pages: list = []
        self._load_gen: int = 0
        self._loading: bool = False

        # Индекс следующего события для проигрывания
        self._next_event_idx = 0

        self._build_ui()
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
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)

        self.btn_open = QPushButton("Open")
        self.btn_open.setFixedWidth(72)
        self.btn_open.clicked.connect(self.on_open)
        tb.addWidget(self.btn_open)

        self.btn_midi = QPushButton("MIDI")
        self.btn_midi.setFixedWidth(64)
        self.btn_midi.setToolTip("Экспорт текущей партитуры в MIDI")
        self.btn_midi.clicked.connect(self.on_export_midi)
        self.btn_midi.setEnabled(False)
        tb.addWidget(self.btn_midi)

        self.btn_about = QPushButton("\u2139")
        self.btn_about.setFixedWidth(34)
        self.btn_about.setToolTip("О программе NowPiano")
        self.btn_about.setToolTip("Информация о NowPiano")
        self.btn_about.clicked.connect(self._show_about)
        tb.addWidget(self.btn_about)

        tb.addSeparator()

        self.btn_rewind = QPushButton("⏮")
        self.btn_rewind.setObjectName("btn_rewind")
        self.btn_rewind.setProperty("icon_button", "true")
        self.btn_rewind.setToolTip("В начало (Home)")
        self.btn_rewind.clicked.connect(self.on_rewind)
        tb.addWidget(self.btn_rewind)

        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("btn_play")
        self.btn_play.setProperty("icon_button", "true")
        self.btn_play.setFlat(True)
        self.btn_play.setToolTip("Играть / Пауза (Space)")
        self.btn_play.clicked.connect(self.on_play_pause)
        tb.addWidget(self.btn_play)

        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setProperty("icon_button", "true")
        self.btn_stop.setFlat(True)
        self.btn_stop.setToolTip("Стоп (S)")
        self.btn_stop.clicked.connect(self.on_stop)
        tb.addWidget(self.btn_stop)

        self.btn_loop = QPushButton("🔁")
        self.btn_loop.setObjectName("btn_loop")
        self.btn_loop.setProperty("icon_button", "true")
        self.btn_loop.setFlat(True)
        self.btn_loop.setCheckable(True)
        self.btn_loop.setToolTip("Повтор")
        self.btn_loop.toggled.connect(self.on_loop)
        tb.addWidget(self.btn_loop)

        # Иконки: прозрачный фон, крупный размер - индивидуальный QSS для каждой кнопки
        _icon_qss = """
            QPushButton {
                background: transparent;
                border: none;
                outline: none;
                color: #2f6dbb;
                font-size: 30px;
                min-width: 54px;
                min-height: 42px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                color: #4a90e2;
                background: rgba(74, 144, 226, 50);
                border-radius: 8px;
            }
            QPushButton:pressed {
                color: #1f4a80;
                background: rgba(74, 144, 226, 100);
                border-radius: 8px;
            }
        """
        _play_qss = """
            QPushButton {
                background: transparent;
                border: none;
                color: #2f6dbb;
                font-size: 30px;
                min-width: 54px;
                min-height: 42px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                color: #4a90e2;
                background: rgba(74, 144, 226, 50);
                border-radius: 8px;
            }
            QPushButton:pressed {
                color: #1f4a80;
                background: rgba(74, 144, 226, 100);
                border-radius: 8px;
            }
        """
        self.btn_play.setStyleSheet(_play_qss)
        tb.addSeparator()

        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setMinimumWidth(300)
        self.progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.progress.setMouseTracking(True)
        self.progress.mousePressEvent = self._progress_click
        self.progress.mouseMoveEvent = self._progress_move
        self.progress.mouseReleaseEvent = self._progress_release
        tb.addWidget(self.progress)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setObjectName("time")
        tb.addWidget(self.lbl_time)
        tb.addSeparator()

        # BPM
        self.lbl_bpm_title = QLabel("Temp")
        self.lbl_bpm_title.setObjectName("bpm")
        tb.addWidget(self.lbl_bpm_title)

        self.slider_bpm = QSlider(Qt.Orientation.Horizontal)
        self.slider_bpm.setRange(30, 200)
        self.slider_bpm.setValue(int(MANUAL_BPM))
        self.slider_bpm.setFixedWidth(180)
        self.slider_bpm.valueChanged.connect(self.on_bpm)
        tb.addWidget(self.slider_bpm)

        self.lbl_bpm = QSpinBox()
        self.lbl_bpm.setRange(30, 200)
        self.lbl_bpm.setValue(int(MANUAL_BPM))
        self.lbl_bpm.setFixedWidth(70)
        self.lbl_bpm.setToolTip("Введите темп цифрами (30-200)")
        self.lbl_bpm.valueChanged.connect(self.on_bpm)
        tb.addWidget(self.lbl_bpm)

        # Область PDF
        self.pdf_view = PdfView()
        self.pianoroll_view = PianoRollView()
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
        root.addWidget(chord_panel)

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
            "Ноты (*.pdf *.jpg *.jpeg *.png *.tif *.tiff *.bmp *.mid *.midi *.mxl *.musicxml *.xml);;"
            "PDF (*.pdf);;"
            "Картинки (*.jpg *.jpeg *.png *.tif *.tiff *.bmp);;"
            "MIDI (*.mid *.midi);;"
            "MusicXML (*.mxl *.musicxml *.xml);;"
            "Все файлы (*.*)"
        )
        if not path:
            return

        # Сброс предыдущей партитуры
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
        self._update_time_label()
        self.btn_midi.setEnabled(False)
        self.staff_view.setVisible(False)

        # Перед новым файлом останавливаем старое воспроизведение.
        self.on_stop()
        # Во время загрузки Play сообщает пользователю, что распознавание ещё идёт.
        self._loading = True
        self.btn_play.setEnabled(True)
        self.recognition_label.setVisible(True)
        self.recognition_progress.setVisible(True)

        # Новое поколение загрузки — старый фоновый поток не должен ничего менять
        self._load_gen = getattr(self, "_load_gen", 0) + 1
        gen = self._load_gen

        self.status.showMessage(f"Загрузка: {os.path.basename(path)}")
        lower = path.lower()
        if lower.endswith((".mid", ".midi")):
            self.recognition_label.setText("MIDI: загрузка")
            self.recognition_progress.setRange(0, 100)
            self.recognition_progress.setValue(0)
            threading.Thread(target=self._load_midi_worker, args=(path, gen), daemon=True).start()
        else:
            self.recognition_label.setText("Распознавание PDF")
            self.recognition_progress.setRange(0, 100)
            self.recognition_progress.setValue(0)
            threading.Thread(target=self._load_pdf_worker, args=(path, gen), daemon=True).start()

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
    def on_play_pause(self):
        if self._loading:
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
        self.position = 0.0
        self._next_event_idx = 0
        self.btn_play.setText("▶")
        self.audio.all_off()
        self.keyboard.set_active_notes(set(), set(), set())
        self.chord_left_label.setText("ЛЕВАЯ РУКА: —")
        self.chord_right_label.setText("ПРАВАЯ РУКА: —")
        self.pdf_view.clear_cursor()
        self.staff_view.set_position(0.0, set())
        self._update_time_label()
        self.status.showMessage("Стоп")
        # Разблокируем Open, чтобы можно было открыть другой файл
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
        if not self.audio_ok:
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
                self.audio.note_off_later(n, max(0.15, ev.duration * 1.2))
                active_notes.add(n)
                self._flash_notes[n] = now
            self._next_event_idx += 1
        # Убираем старые вспышки (>0.15 c назад)
        cutoff = now - 0.15
        for k in list(self._flash_notes.keys()):
            if self._flash_notes[k] < cutoff:
                del self._flash_notes[k]
        flash = set(self._flash_notes.keys())

        # Подсветка активных
        still_active = set()
        still_active_right = set()
        still_active_left = set()
        lookback = min(self._next_event_idx, 64)
        for i in range(self._next_event_idx - lookback, self._next_event_idx):
            if i < 0:
                continue
            ev = self.events[i]
            if ev.time_seconds <= self.position <= ev.time_seconds + max(0.08, ev.duration * 1.2):
                still_active.update(ev.notes)
                if getattr(ev, 'hand', 'R') == 'R':
                    still_active_right.update(ev.notes)
                else:
                    still_active_left.update(ev.notes)
        self.keyboard.set_active_notes(still_active, still_active_right, still_active_left, flash)
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
            if ev.time_seconds <= self.position < ev.time_seconds + max(0.05, ev.duration):
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
        if self.duration <= 0 or not self.events:
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

        self._flash_notes.clear()
        active = set()
        active_right = set()
        active_left = set()

        for ev in self.events:
            if ev.time_seconds > self.position:
                break
            if self.position <= ev.time_seconds + max(0.08, ev.duration * 1.2):
                for n in ev.notes:
                    active.add(n)
                    if getattr(ev, "hand", "R") == "R":
                        active_right.add(n)
                    else:
                        active_left.add(n)

        self.keyboard.set_active_notes(active, active_right, active_left, set())

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

        self._update_time_label()
        self.status.showMessage("\u041f\u0430\u0443\u0437\u0430 \u2014 \u043f\u043e\u0437\u0438\u0446\u0438\u044f \u0432\u044b\u0431\u0440\u0430\u043d\u0430")

    def _update_time_label(self):
        def fmt(s):
            s = max(0, int(s))
            return f"{s // 60:02d}:{s % 60:02d}"
        self.lbl_time.setText(f"{fmt(self.position)} / {fmt(self.duration)}")
        if self.duration > 0:
            self.progress.setValue(int(1000 * self.position / self.duration))

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
        ok = export_midi(self._last_mxl, out_path)
        if ok:
            self.status.showMessage(f"MIDI сохранён: {out_path}")
            QMessageBox.information(self, "Готово", f"MIDI сохранён:\n{out_path}")
        else:
            self.status.showMessage("Ошибка экспорта MIDI")
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить MIDI.")
    def _load_midi_worker(self, path, gen):
        """Загружает .mid/.midi без Audiveris и PDF."""
        if gen != self._load_gen:
            return
        try:
            self.sig_status.emit("Загрузка MIDI...")
            events, bpm = load_midi_events(path)
            # Все изменения виджетов выполняются в главном потоке — через sig_load_done.
            self._last_mxl = path
            self._last_pdf_path = path
            if gen != self._load_gen:
                return
            self.sig_load_done.emit(events, bpm, "")
        except Exception as e:
            if gen != self._load_gen:
                return
            self.sig_load_done.emit(None, MANUAL_BPM, f"Ошибка MIDI: {e}")
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

        qr_path = os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            os.pardir, "resources", "donate_qr.png"
        ))
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

    def closeEvent(self, event):
        self.is_playing = False
        try:
            self.audio.shutdown()
        except Exception:
            pass
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = PianoWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
