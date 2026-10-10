# -*- coding: utf-8 -*-
"""qt_render.py - виджеты PDF и клавиатуры на QPainter."""

import os
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient,
    QPainterPath, QImage, QPixmap
)
from PyQt6.QtWidgets import QWidget, QSizePolicy

from qt_audio import START_NOTE, NUM_KEYS


# ---------- Утилиты ----------
def is_black_key(midi: int) -> bool:
    return ((midi - 12) % 12) in (1, 3, 6, 8, 10)


LETTERS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_letter(midi: int) -> str:
    return LETTERS[midi % 12]


# ---------- Клавиатура ----------
class KeyboardView(QWidget):
    """Рисует 88 клавиш, подсвечивает активные ноты."""

    note_clicked = pyqtSignal(int)  # сигнал: пользователь кликнул по клавише

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.active_notes = set()
        self._white_x = {}   # midi -> x белой клавиши
        self._white_w = 0.0

    def set_active_notes(self, notes):
        if notes != self.active_notes:
            self.active_notes = set(notes)
            self.update()

    # ---------- Геометрия ----------
    def _compute_layout(self):
        w = self.width()
        n_white = sum(1 for n in range(START_NOTE, START_NOTE + NUM_KEYS)
                      if not is_black_key(n))
        kw = w / max(1, n_white)
        self._white_w = kw
        self._white_x = {}
        idx = 0
        for n in range(START_NOTE, START_NOTE + NUM_KEYS):
            if not is_black_key(n):
                self._white_x[n] = idx * kw
                idx += 1
        return kw

    def _black_x(self, midi: int, kw: float):
        prev = self._white_x.get(midi - 1)
        nxt = self._white_x.get(midi + 1)
        if prev is not None:
            return prev + kw * 0.7
        if nxt is not None:
            return nxt - kw * 0.3
        return 0.0

    # ---------- Отрисовка ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad_top = 6
        pad_bottom = 6
        kh = h - pad_top - pad_bottom
        kw = self._compute_layout()

        # Фон панели
        grad_bg = QLinearGradient(0, 0, 0, h)
        grad_bg.setColorAt(0.0, QColor(250, 251, 253))
        grad_bg.setColorAt(1.0, QColor(228, 232, 240))
        p.fillRect(self.rect(), QBrush(grad_bg))

        # --- Белые клавиши ---
        for n in range(START_NOTE, START_NOTE + NUM_KEYS):
            if is_black_key(n):
                continue
            x = self._white_x[n]
            rect = QRectF(x, pad_top, kw - 1, kh)
            active = n in self.active_notes

            grad = QLinearGradient(x, pad_top, x, pad_top + kh)
            if active:
                grad.setColorAt(0.0, QColor(120, 190, 255))
                grad.setColorAt(1.0, QColor(60, 140, 220))
            else:
                grad.setColorAt(0.0, QColor(252, 252, 255))
                grad.setColorAt(1.0, QColor(225, 228, 235))
            p.setBrush(QBrush(grad))
            p.setPen(QPen(QColor(60, 60, 70), 1))
            p.drawRoundedRect(rect, 3, 3)

            # Подпись ноты: у активных — буква, у C — с октавой
            letter = note_letter(n)
            if active:
                f = QFont("Segoe UI", 10, QFont.Weight.Bold)
                p.setFont(f)
                p.setPen(QColor(20, 40, 80))
                txt = f"{letter}{n // 12 - 1}"
                p.drawText(rect.adjusted(0, kh - 22, 0, -4),
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                           txt)
            elif letter == "C":
                f = QFont("Segoe UI", 8)
                p.setFont(f)
                p.setPen(QColor(150, 150, 160))
                p.drawText(rect.adjusted(0, kh - 18, 0, -2),
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                           f"C{n // 12 - 1}")

        # --- Чёрные клавиши ---
        black_h = kh * 0.62
        black_w = kw * 0.62
        for n in range(START_NOTE, START_NOTE + NUM_KEYS):
            if not is_black_key(n):
                continue
            x = self._black_x(n, kw)
            rect = QRectF(x, pad_top, black_w, black_h)
            active = n in self.active_notes

            grad = QLinearGradient(x, pad_top, x, pad_top + black_h)
            if active:
                grad.setColorAt(0.0, QColor(255, 120, 110))
                grad.setColorAt(1.0, QColor(200, 50, 40))
            else:
                grad.setColorAt(0.0, QColor(60, 62, 72))
                grad.setColorAt(1.0, QColor(10, 10, 15))
            p.setBrush(QBrush(grad))
            p.setPen(QPen(QColor(0, 0, 0), 1))
            p.drawRoundedRect(rect, 2, 2)

            # Блик
            hl = QRectF(x + 2, pad_top + 2, black_w - 4, 4)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 40))
            p.drawRoundedRect(hl, 1, 1)

            # Подпись ноты на активной чёрной клавише
            if active:
                letter = note_letter(n)
                f = QFont("Segoe UI", 7, QFont.Weight.Bold)
                p.setFont(f)
                p.setPen(QColor(255, 255, 255))
                txt = f"{letter}{n // 12 - 1}"
                inner = rect.adjusted(1, 1, -1, -1)
                p.drawText(inner, Qt.AlignmentFlag.AlignCenter, txt)

        p.end()

    def mousePressEvent(self, event):
        pos = event.position()
        kw = self._white_w
        # Ищем ближайшую клавишу
        for n in range(START_NOTE, START_NOTE + NUM_KEYS):
            if is_black_key(n):
                x = self._black_x(n, kw)
                if x <= pos.x() <= x + kw * 0.62 and pos.y() <= self.height() * 0.62:
                    self.note_clicked.emit(n)
                    return
        for n in range(START_NOTE, START_NOTE + NUM_KEYS):
            if not is_black_key(n):
                x = self._white_x.get(n, 0)
                if x <= pos.x() <= x + kw:
                    self.note_clicked.emit(n)
                    return


# ---------- PDF-страница ----------
class PdfView(QWidget):
    """Показывает страницу PDF с белой «бумагой», тенью и курсором."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(420)
        self._pixmap: QPixmap | None = None
        self._cursor_xy: tuple[float, float] | None = None  # (x, y) в координатах страницы

    def set_page(self, pixmap: QPixmap | None):
        self._pixmap = pixmap
        self.update()

    def set_cursor(self, x: float, y: float, page=None):
        self._cursor_xy = (x, y)
        self.update()

    def clear_cursor(self):
        self._cursor_xy = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        # Фон области
        grad_bg = QLinearGradient(0, 0, 0, h)
        grad_bg.setColorAt(0.0, QColor(245, 247, 250))
        grad_bg.setColorAt(1.0, QColor(228, 232, 240))
        p.fillRect(self.rect(), QBrush(grad_bg))

        if self._pixmap is None:
            p.setPen(QColor(120, 126, 140))
            f = QFont("Segoe UI", 14)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "PDF не загружен.\nНажми «Открыть PDF».")
            p.end()
            return

        # Белая «бумага» с тенью по центру
        pm = self._pixmap
        pw, ph = pm.width(), pm.height()
        scale = min((w - 60) / pw, (h - 40) / ph)
        sw, sh = int(pw * scale), int(ph * scale)
        x0 = (w - sw) // 2
        y0 = (h - sh) // 2

        # тень
        shadow = QRectF(x0 + 6, y0 + 8, sw, sh)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawRoundedRect(shadow, 8, 8)

        # бумага
        paper = QRectF(x0, y0, sw, sh)
        p.setBrush(QColor(250, 250, 252))
        p.drawRoundedRect(paper, 6, 6)

        # сама страница
        p.drawPixmap(int(x0), int(y0), sw, sh, pm)

        # тонкая обводка
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(180, 180, 190), 1))
        p.drawRoundedRect(paper, 6, 6)

        # курсор воспроизведения
        if self._cursor_xy is not None:
            cx, cy = self._cursor_xy
            dx = x0 + cx * scale
            dy = y0 + cy * scale

            # вертикальная линия
            pen = QPen(QColor(230, 60, 60, 200), 2)
            p.setPen(pen)
            p.drawLine(QPointF(dx, y0), QPointF(dx, y0 + sh))

            # кружок
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(255, 80, 80), 3))
            p.drawEllipse(QPointF(dx, dy), 14, 14)
            p.setPen(QPen(QColor(255, 255, 255, 200), 1))
            p.drawEllipse(QPointF(dx, dy), 17, 17)


class WelcomeView(QWidget):
    """Заставка NowPiano с картинкой back.jpg и названием."""

    def __init__(self, image_path: str = None, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self._pixmap = None
        self._progress = 0.0
        self._status = "Loading..."
        if image_path and os.path.exists(image_path):
            self._pixmap = QPixmap(image_path)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_progress(self, value: float, status: str = None):
        self._progress = max(0.0, min(1.0, float(value)))
        if status is not None:
            self._status = status
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(w, h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
            x = (w - scaled.width()) // 2
            y = (h - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
        else:
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor(20, 30, 60))
            grad.setColorAt(1.0, QColor(10, 15, 35))
            p.fillRect(self.rect(), grad)
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))
        font_title = QFont("Segoe UI", 72, QFont.Weight.Bold)
        p.setFont(font_title)
        p.setPen(QColor(255, 255, 255))
        p.drawText(0, 0, w, h - 40,
                   Qt.AlignmentFlag.AlignCenter, "NowPiano")
        font_sub = QFont("Segoe UI", 20)
        p.setFont(font_sub)
        p.setPen(QColor(180, 200, 240))
        p.drawText(0, h // 2 + 50, w, 60,
                   Qt.AlignmentFlag.AlignCenter, "Piano Music Reader")
        if self._progress > 0:
            bar_y = h - 70
            bar_w = int(w * 0.6)
            bar_x = (w - bar_w) // 2
            bar_h = 6
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 60))
            p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)
            fill_w = int(bar_w * self._progress)
            p.setBrush(QColor(74, 144, 226))
            p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 3, 3)
            font_st = QFont("Segoe UI", 12)
            p.setFont(font_st)
            p.setPen(QColor(200, 210, 230))
            p.drawText(bar_x, bar_y + 15, bar_w, 30,
                       Qt.AlignmentFlag.AlignCenter, self._status)
        p.end()
        p.end()


if __name__ == "__main__":
    # Быстрый визуальный тест: показать клавиатуру и пустой PDF-виджет
    import sys
    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget as QW

    app = QApplication(sys.argv)
    win = QW()
    win.setWindowTitle("qt_render self-test")
    win.resize(1000, 600)
    layout = QVBoxLayout(win)

    pdf = PdfView()
    kb = KeyboardView()
    layout.addWidget(pdf, stretch=1)
    layout.addWidget(kb, stretch=0)

    # Подсветим случайные ноты через 1 сек
    from PyQt6.QtCore import QTimer
    def highlight():
        kb.set_active_notes({60, 64, 67, 55, 43})
    QTimer.singleShot(1000, highlight)

    win.show()
    sys.exit(app.exec())
