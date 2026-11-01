# -*- coding: utf-8 -*-
"""Vertical falling-note Piano Roll for NowPiano."""

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt6.QtWidgets import QWidget, QSizePolicy


WHITE_NOTES = {0, 2, 4, 5, 7, 9, 11}
BLACK_NOTES = {1, 3, 6, 8, 10}

NOTE_NAMES = (
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B"
)

MIDI_LOW = 21
MIDI_HIGH = 108


class PianoRollView(QWidget):
    keyboard_size_requested = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.setMinimumHeight(300)
        self.setMinimumWidth(450)

        self.events = []
        self.duration = 0.0
        self.position = 0.0
        self.original_bpm = 120.0

        self.top_margin = 30
        self.visible_seconds = 5.0
        self.key_count = 88
        self.midi_low = 21
        self.midi_high = 108

        self.right_color = QColor("#2878d0")
        self.left_color = QColor("#159b69")
        self.cursor_color = QColor("#e53935")

        self.setAutoFillBackground(False)

    def _set_key_count(self, count):
        count = int(count)
        if count not in (88, 76, 61):
            return
        self.key_count = count
        self.keyboard_size_requested.emit(count)
        self.update()

    def set_keyboard_range(self, low, num_keys):
        low = int(low)
        num_keys = int(num_keys)
        if num_keys not in (88, 76, 61):
            return
        self.midi_low = low
        self.midi_high = low + num_keys - 1
        self.key_count = num_keys
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            if 3 <= pos.y() <= 28:
                x = pos.x()
                choices = (88, 76, 61)
                index = int((x - 72) // 66)
                if (
                    0 <= index < len(choices)
                    and 0 <= (x - 72) % 66 <= 58
                ):
                    self._set_key_count(choices[index])
                    event.accept()
                    return
        super().mousePressEvent(event)

    def set_events(self, events, duration, original_bpm):
        self.events = list(events or [])
        self.duration = max(0.1, float(duration))
        self.original_bpm = max(1.0, float(original_bpm))
        self.position = 0.0
        self.update()

    def set_position(self, seconds):
        self.position = max(
            0.0,
            min(float(seconds), self.duration)
        )
        self.update()

    @staticmethod
    def _note_name(midi):
        midi = int(midi)
        return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"

    @staticmethod
    def _is_black(midi):
        return midi % 12 in BLACK_NOTES

    def _white_index(self, midi):
        """Number of white keys before this MIDI note."""
        count = 0
        for n in range(self.midi_low, midi):
            if n % 12 in WHITE_NOTES:
                count += 1
        return count

    def _key_geometry(self, width):
        white_midis = [
            n for n in range(self.midi_low, self.midi_high + 1)
            if n % 12 in WHITE_NOTES
        ]
        white_width = width / max(1, len(white_midis))

        white_x = {}
        index = 0
        for midi in range(self.midi_low, self.midi_high + 1):
            if midi % 12 in WHITE_NOTES:
                white_x[midi] = index * white_width
                index += 1

        centers = {}
        widths = {}

        for midi in range(self.midi_low, self.midi_high + 1):
            if self._is_black(midi):
                prev_x = white_x.get(midi - 1)
                next_x = white_x.get(midi + 1)

                if prev_x is not None:
                    center = prev_x + white_width * 0.7
                elif next_x is not None:
                    center = next_x - white_width * 0.3
                else:
                    center = 0.0

                widths[midi] = white_width * 0.58
            else:
                center = white_x[midi] + white_width * 0.5
                widths[midi] = white_width * 0.88

            centers[midi] = center

        return white_midis, white_width, centers, widths

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()

        p.fillRect(self.rect(), QColor("#edf1f7"))

        # Переключатель размера клавиатуры
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor("#526174"))
        p.drawText(
            QRectF(8, 5, 58, 20),
            Qt.AlignmentFlag.AlignVCenter,
            "Клавиши:"
        )

        for i, count in enumerate((88, 76, 61)):
            x = 72 + i * 66
            selected = self.key_count == count
            p.setPen(QPen(
                QColor("#245b96") if selected else QColor("#b8c3d2"),
                1
            ))
            p.setBrush(QBrush(
                QColor("#d8eaff") if selected else QColor("#ffffff")
            ))
            p.drawRoundedRect(QRectF(x, 3, 58, 23), 5, 5)
            p.setPen(
                QColor("#174d86") if selected else QColor("#526174")
            )
            p.drawText(
                QRectF(x, 3, 58, 23),
                Qt.AlignmentFlag.AlignCenter,
                str(count)
            )

        keyboard_top = h
        hit_y = h - 2
        top = self.top_margin

        if keyboard_top <= top + 20:
            p.end()
            return

        # Область падающих нот
        p.fillRect(
            QRectF(0, top, w, keyboard_top - top),
            QColor("#ffffff")
        )

        play_height = hit_y - top
        pixels_per_second = play_height / self.visible_seconds

        # Вертикальные линии октав и подсветка C
        white_midis, white_width, centers, widths = (
            self._key_geometry(w)
        )

        for midi in range(self.midi_low, self.midi_high + 1):
            if midi % 12 != 0:
                continue

            x = centers[midi]
            p.setPen(QPen(QColor("#e0e6ef"), 1))
            p.drawLine(
                QPointF(x, top),
                QPointF(x, keyboard_top)
            )

        # Горизонтальная временная сетка
        beat_seconds = 60.0 / self.original_bpm
        beat = beat_seconds

        p.setFont(QFont("Segoe UI", 8))
        tick = 0

        while tick * beat <= self.visible_seconds + beat:
            future_time = tick * beat
            y = hit_y - future_time * pixels_per_second

            if y < top:
                break

            if tick % 4 == 0:
                p.setPen(QPen(QColor("#aab5c5"), 1.2))
                label = f"Такт {tick // 4 + 1}"
            else:
                p.setPen(QPen(QColor("#e4e9f0"), 0.8))
                label = ""

            p.drawLine(
                QPointF(0, y),
                QPointF(w, y)
            )

            if label:
                p.setPen(QColor("#7a879a"))
                p.drawText(
                    QRectF(5, y - 17, 70, 14),
                    Qt.AlignmentFlag.AlignLeft,
                    label
                )

            tick += 1

        # Ноты: будущие события находятся выше линии,
        # при приближении времени опускаются к клавиатуре.
        p.save()
        p.setClipRect(
            QRectF(0, top, w, keyboard_top - top)
        )

        colors = {
            "R": self.right_color,
            "L": self.left_color,
        }

        valid_events = []

        for ev in self.events:
            try:
                start = float(ev.time_seconds)
                length = max(0.04, float(ev.duration))
                notes = [
                    int(n) for n in (getattr(ev, "notes", []) or [])
                    if MIDI_LOW <= int(n) <= MIDI_HIGH
                ]
                if notes:
                    valid_events.append((start, length, notes, ev))
            except (TypeError, ValueError, AttributeError):
                continue

        for start, length, notes, ev in valid_events:
            # Нота, которая уже полностью закончилась,
            # не должна отображаться над клавиатурой.
            if start + length < self.position:
                continue

            note_bottom = (
                hit_y
                - (start - self.position) * pixels_per_second
            )
            note_top = (
                note_bottom - max(5.0, length * pixels_per_second)
            )

            if note_bottom < top or note_top > keyboard_top:
                continue

            hand = str(getattr(ev, "hand", "R")).upper()
            color = colors.get(hand, QColor("#9062bb"))

            outside_low = any(n < self.midi_low for n in notes)
            outside_high = any(n > self.midi_high for n in notes)

            p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            p.setPen(QPen(color, 2))
            if outside_low:
                p.drawText(
                    QRectF(3, note_top, 22, 20),
                    Qt.AlignmentFlag.AlignCenter,
                    "◀"
                )
            if outside_high:
                p.drawText(
                    QRectF(w - 25, note_top, 22, 20),
                    Qt.AlignmentFlag.AlignCenter,
                    "▶"
                )

            for midi in notes:
                if midi not in centers:
                    continue
                center = centers[midi]
                key_width = widths[midi]
                note_width = max(4.0, key_width * 0.72)

                rect = QRectF(
                    center - note_width / 2,
                    note_top,
                    note_width,
                    max(5.0, note_bottom - note_top)
                )

                p.setPen(QPen(color.darker(135), 1))
                p.setBrush(QBrush(color))
                p.drawRoundedRect(rect, 3, 3)

                # Светлая полоса внутри ноты
                p.setPen(QPen(color.lighter(145), 1))
                p.drawLine(
                    QPointF(rect.left() + 3, rect.top() + 3),
                    QPointF(rect.right() - 3, rect.top() + 3)
                )

        p.restore()

        # Красная линия момента исполнения
        p.setPen(QPen(self.cursor_color, 2.5))
        p.drawLine(
            QPointF(0, hit_y),
            QPointF(w, hit_y)
        )

        p.setBrush(QBrush(self.cursor_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon([
            QPointF(0, hit_y - 6),
            QPointF(10, hit_y - 6),
            QPointF(5, hit_y + 2)
        ])

        # Подпись текущей позиции
        p.setPen(QColor("#ffffff"))
        p.setBrush(QBrush(QColor("#d93434")))
        p.drawRoundedRect(
            QRectF(w - 78, hit_y - 22, 72, 18),
            4, 4
        )
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.drawText(
            QRectF(w - 76, hit_y - 21, 68, 16),
            Qt.AlignmentFlag.AlignCenter,
            f"{self.position:.1f} s"
        )

        # Клавиатура внизу

        # Рамка
        p.setPen(QPen(QColor("#c5cedb"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))

        p.end()
