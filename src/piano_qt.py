# -*- coding: utf-8 -*-
"""piano_qt.py - NowPiano на PyQt6. Полная сборка: PDF, Audiveris, звук, клавиатура."""

import os
import sys
import time
import threading

from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QElapsedTimer
from PyQt6.QtGui import QAction, QKeySequence, QFont, QPixmap, QImage
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QProgressBar, QToolBar, QStatusBar,
    QSizePolicy, QFileDialog, QMessageBox, QSpinBox
)

# --- PyInstaller windowed mode fix: sys.stdout/stderr = None ---
if getattr(sys, "frozen", False):
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
from qt_audio import (
    AudioEngine, run_audiveris, musicxml_to_events,
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

        # Индекс следующего события для проигрывания
        self._next_event_idx = 0

        self._build_ui()
        self.setStyleSheet(QSS)

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

        self.btn_open = QPushButton("📂 Open")
        self.btn_open.clicked.connect(self.on_open)
        tb.addWidget(self.btn_open)

        self.btn_midi = QPushButton("💾 MIDI")
        self.btn_midi.setToolTip("Экспорт текущей партитуры в MIDI")
        self.btn_midi.clicked.connect(self.on_export_midi)
        self.btn_midi.setEnabled(False)
        tb.addWidget(self.btn_midi)

        tb.addSeparator()

        self.btn_rewind = QPushButton("⏮")
        self.btn_rewind.setToolTip("В начало (Home)")
        self.btn_rewind.clicked.connect(self.on_rewind)
        tb.addWidget(self.btn_rewind)

        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("play")
        self.btn_play.setToolTip("Играть / Пауза (Space)")
        self.btn_play.clicked.connect(self.on_play_pause)
        tb.addWidget(self.btn_play)

        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setObjectName("stop")
        self.btn_stop.setToolTip("Стоп (S)")
        self.btn_stop.clicked.connect(self.on_stop)
        tb.addWidget(self.btn_stop)

        self.btn_loop = QPushButton("🔁")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setToolTip("Повтор")
        self.btn_loop.toggled.connect(self.on_loop)
        tb.addWidget(self.btn_loop)

        # Иконки: прозрачный фон, крупный размер - индивидуальный QSS для каждой кнопки
        _icon_qss = """
            QPushButton {
                background: transparent;
                border: none;
                font-size: 30px;
                min-width: 54px;
                min-height: 42px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background: rgba(74, 144, 226, 50);
                border-radius: 8px;
            }
            QPushButton:pressed {
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
        for _b in (self.btn_rewind, self.btn_stop, self.btn_loop):
            _b.setStyleSheet(_icon_qss)
        self.btn_play.setStyleSheet(_play_qss)
        tb.addSeparator()

        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setMinimumWidth(300)
        self.progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.progress.mousePressEvent = self._progress_click
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
        _BACK_IMG = r'C:\Users\blazh\OneDrive\Desktop\assets\back.jpg'
        self.welcome_view = WelcomeView(_BACK_IMG)
        self.welcome_view.setVisible(False)
        root.addWidget(self.pdf_view, stretch=1)
        root.addWidget(self.welcome_view, stretch=1)
        root.addWidget(self.pianoroll_view, stretch=1)

        # Клавиатура
        self.keyboard = KeyboardView()
        self.keyboard.note_clicked.connect(self.on_note_clicked)
        root.addWidget(self.keyboard, stretch=0)

        # Статус
        self.status = QStatusBar()
        self.setStatusBar(self.status)

    # ---------- Загрузка PDF ----------
    def on_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть", "", "Музыка (*.pdf *.mid *.midi);;PDF (*.pdf);;MIDI (*.mid *.midi);;Все файлы (*.*)"
        )
        if not path:
            return
        self.status.showMessage(f"Загрузка: {os.path.basename(path)}")
        self.btn_open.setEnabled(False)
        lower = path.lower()
        if lower.endswith((".mid", ".midi")):
            threading.Thread(target=self._load_midi_worker, args=(path,), daemon=True).start()
        else:
            threading.Thread(target=self._load_pdf_worker, args=(path,), daemon=True).start()

    def _load_pdf_worker(self, path):
        try:
            # 1. Рендер первой страницы PDF через Poppler (pdf2image)
            self.sig_status.emit("Шаг 1/3: рендер PDF...")
            pix = None
            try:
                from pdf2image import convert_from_path
                poppler_path = None
                _cand = []
                if getattr(sys, "frozen", False):
                    _exe_dir = os.path.dirname(sys.executable)
                    _cand.append(os.path.join(_exe_dir, "_internal", "poppler", "Library", "bin"))
                    _cand.append(os.path.join(_exe_dir, "poppler", "Library", "bin"))
                    _cand.append(os.path.join(_exe_dir, "poppler", "bin"))
                _cand.append(r"C:\poppler\Library\bin")
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

            # 2. Audiveris
            self.sig_status.emit("Шаг 2/3: Audiveris распознаёт (может занять минуту)...")
            mxl = run_audiveris(path)
            self._last_mxl = mxl
            self._last_pdf_path = path

            # 3. MusicXML -> события
            self.sig_status.emit("Шаг 3/3: разбор MusicXML...")
            events, bpm, n_parts = musicxml_to_events(mxl)

            self.sig_load_done.emit(events, bpm, "")
        except Exception as e:
            self.sig_load_done.emit(None, MANUAL_BPM, str(e))

    def _on_page_ready(self, pixmap):
        self.pdf_view.set_page(pixmap)
        self._pdf_pages = [pixmap]
        if self.events:
            self._cursor_map = self._build_cursor_map(pixmap, self.events)

    def _on_load_done(self, events, bpm, error):
        self.btn_open.setEnabled(True)
        if error or events is None:
            self.status.showMessage(f"Ошибка: {error}")
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
        # Показываем piano roll только если это MIDI (нет PDF-страниц)
        _lower = (self._last_pdf_path or "").lower()
        if _lower.endswith((".mid", ".midi")):
            self.pianoroll_view.setVisible(False)
            self.welcome_view.setVisible(True)
            self.pdf_view.setVisible(False)
        else:
            self.pianoroll_view.setVisible(False)
            self.welcome_view.setVisible(False)
            self.pdf_view.setVisible(True)
        self.btn_midi.setEnabled(True)
        self._update_time_label()
        self.status.showMessage(
            f"Готово: {len(events)} событий, {self.duration:.1f} сек, Темп={bpm:.0f}"
        )

    def _on_status(self, text):
        self.status.showMessage(text)

    # ---------- Управление воспроизведением ----------
    def on_play_pause(self):
        if not self.events:
            self.status.showMessage("Сначала загрузи PDF")
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
        self.keyboard.set_active_notes(set())
        self.pdf_view.clear_cursor()
        self._update_time_label()
        self.status.showMessage("Стоп")

    def on_rewind(self):
        self.position = 0.0
        self._next_event_idx = 0
        self.audio.all_off()
        self.keyboard.set_active_notes(set())
        self.pdf_view.clear_cursor()
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
        # Подсветим на 300 мс
        cur = set(self.keyboard.active_notes)
        cur.add(midi)
        self.keyboard.set_active_notes(cur)
        QTimer.singleShot(300, lambda: self.keyboard.set_active_notes(
            self.keyboard.active_notes - {midi}
        ))

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
        while self._next_event_idx < len(self.events):
            ev = self.events[self._next_event_idx]
            if ev.time_seconds > self.position:
                break
            velocity = 100 if ev.hand == "R" else 70
            for n in ev.notes:
                self.audio.note_on(n, velocity)
                self.audio.note_off_later(n, max(0.15, ev.duration * 1.2))
                active_notes.add(n)
            self._next_event_idx += 1

        # Подсветка активных
        still_active = set()
        lookback = min(self._next_event_idx, 16)
        for i in range(self._next_event_idx - lookback, self._next_event_idx):
            if i < 0:
                continue
            ev = self.events[i]
            if self.position <= ev.time_seconds + ev.duration * 1.2:
                still_active.update(ev.notes)
        self.keyboard.set_active_notes(still_active)

        # Курсор в партитуре
        if self._next_event_idx > 0 and self._cursor_map:
            self._set_cursor_for_bar(self.events[self._next_event_idx - 1].bar)

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
                self.keyboard.set_active_notes(set())
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
            self.pdf_view.set_cursor(x, y, page=pg)
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
        self.pdf_view.set_cursor(x, y, page=pg)

    # ---------- Прогресс-бар ----------
    def _progress_click(self, event):
        if self.duration <= 0:
            return
        x = event.position().x() if hasattr(event, "position") else event.x()
        frac = max(0.0, min(1.0, x / self.progress.width()))
        self.position = frac * self.duration
        # Пересчитать next_event_idx
        self._next_event_idx = 0
        for i, ev in enumerate(self.events):
            if ev.time_seconds >= self.position:
                self._next_event_idx = i
                break
        self.audio.all_off()
        self._update_time_label()

    def _update_time_label(self):
        def fmt(s):
            s = max(0, int(s))
            return f"{s // 60:02d}:{s % 60:02d}"
        self.lbl_time.setText(f"{fmt(self.position)} / {fmt(self.duration)}")
        if self.duration > 0:
            self.progress.setValue(int(1000 * self.position / self.duration))

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
    def _load_midi_worker(self, path):
        """Загружает .mid/.midi без Audiveris и PDF."""
        try:
            self.sig_status.emit("Загрузка MIDI...")
            events, bpm = load_midi_events(path)
            # Piano roll: только данные (без визуальных изменений из потока)
            _dur = total_duration(events)
            self.pianoroll_view.set_events(events, _dur, bpm)
            self._last_mxl = path
            self._last_pdf_path = path
            self.sig_load_done.emit(events, bpm, "")
        except Exception as e:
            self.sig_load_done.emit(None, MANUAL_BPM, f"Ошибка MIDI: {e}")
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
