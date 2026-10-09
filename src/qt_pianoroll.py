# -*- coding: utf-8 -*-
"""qt_pianoroll.py - Piano roll widget."""

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QLinearGradient
from PyQt6.QtWidgets import QWidget, QSizePolicy


PALETTE = [
    QColor(220, 40, 40),     # Part 0 - красный
    QColor(30, 120, 255),    # Part 1 - синий
    QColor(255, 160, 0),     # Part 2 - оранжевый
    QColor(15, 157, 88),     # Part 3 - зелёный
    QColor(171, 71, 188),    # Part 4 - пурпурный
    QColor(0, 172, 193),     # Part 5 - бирюзовый
]


class PianoRollView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(300)

        self.events = []
        self.duration = 0.0
        self.position = 0.0
        self.original_bpm = 120.0

        self.left_margin = 60
        self.top_margin = 20
        self.bottom_margin = 30

    def set_events(self, events, duration, original_bpm):
        self.events = events or []
        self.duration = max(0.1, float(duration))
        self.original_bpm = max(1.0, float(original_bpm))
        self.update()

    def set_position(self, seconds):
        self.position = float(seconds)
        self.update()

    def _time_to_x(self, t, w):
        usable = w - self.left_margin - 20
        frac = max(0.0, min(1.0, t / self.duration))
        return self.left_margin + frac * usable

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Фон
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(248, 250, 253))
        grad.setColorAt(1.0, QColor(230, 235, 242))
        p.fillRect(self.rect(), QBrush(grad))

        if not self.events:
            p.setPen(QColor(120, 126, 140))
            p.setFont(QFont("Segoe UI", 14))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No notes loaded.")
            p.end()
            return

        # Тактовые линии
        beat_sec = 60.0 / self.original_bpm
        bar_sec = beat_sec * 4.0
        t = 0.0
        p.setPen(QPen(QColor(200, 208, 220), 1, Qt.PenStyle.SolidLine))
        while t <= self.duration:
            x = self._time_to_x(t, w)
            p.drawLine(QPointF(x, self.top_margin), QPointF(x, h - self.bottom_margin))
            t += bar_sec

        # Разбиваем партии по вертикали
        parts_seen = sorted(set(getattr(e, "part", 0) for e in self.events))
        n_parts = max(1, len(parts_seen))
        top = self.top_margin
        bottom = h - self.bottom_margin
        total_h = bottom - top
        part_h = total_h / n_parts

        # Полу-прозрачные горизонтальные разделители
        p.setPen(QPen(QColor(180, 188, 200, 120), 1, Qt.PenStyle.DashLine))
        for i in range(1, n_parts):
            y = top + i * part_h
            p.drawLine(QPointF(0, y), QPointF(w, y))

        # Глобальный диапазон midi для нормализации
        all_midi = [m for e in self.events for m in e.notes]
        lo_midi = min(all_midi) if all_midi else 40
        hi_midi = max(all_midi) if all_midi else 80
        if hi_midi <= lo_midi:
            hi_midi = lo_midi + 1

        # Ноты
        note_h = 3.0
        for ev in self.events:
            _part = getattr(ev, "part", 0)
            try:
                band_idx = parts_seen.index(_part)
            except ValueError:
                band_idx = 0
            band_top = top + band_idx * part_h
            band_bottom = band_top + part_h
            x1 = self._time_to_x(ev.time_seconds, w)
            x2 = self._time_to_x(ev.time_seconds + ev.duration, w)
            if x2 - x1 < 2:
                x2 = x1 + 2
            col = PALETTE[_part % len(PALETTE)]
            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            for midi in ev.notes:
                frac = (midi - lo_midi) / (hi_midi - lo_midi)
                frac = max(0.0, min(1.0, frac))
                y = band_bottom - frac * (band_bottom - band_top) - note_h
                p.drawRoundedRect(QRectF(x1, y, x2 - x1, note_h), 1.5, 1.5)

        # Курсор
        cx = self._time_to_x(self.position, w)
        p.setPen(QPen(QColor(220, 40, 40, 220), 2))
        p.drawLine(QPointF(cx, self.top_margin), QPointF(cx, h - self.bottom_margin))

        # Рамка
        p.setPen(QPen(QColor(180, 188, 200), 1))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))

        p.end()