# -*- coding: utf-8 -*-
"""qt_render.py - виджеты PDF и клавиатуры на QPainter."""
import os
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QPixmap
from PyQt6.QtWidgets import QWidget, QSizePolicy
from qt_audio import START_NOTE, NUM_KEYS


def is_black_key(midi: int) -> bool:
    return ((midi - 12) % 12) in (1, 3, 6, 8, 10)

LETTERS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
def note_letter(midi: int) -> str:
    return LETTERS[midi % 12]


def chord_name(midis) -> str:
    """Определяет наиболее вероятное название аккорда по наборам нот MIDI."""
    pcs = sorted({int(n) % 12 for n in midis})
    if len(pcs) < 3:
        return ""
    templates = [
        ((0, 4, 7), ""), ((0, 3, 7), "m"), ((0, 3, 6), "dim"),
        ((0, 4, 8), "aug"), ((0, 4, 7, 10), "7"),
        ((0, 4, 7, 11), "maj7"), ((0, 3, 7, 10), "m7"),
        ((0, 3, 7, 11), "m(maj7)"), ((0, 3, 6, 10), "m7b5"),
        ((0, 5, 7), "sus4"), ((0, 2, 7), "sus2"),
        ((0, 4, 7, 9), "6"), ((0, 3, 7, 9), "m6"),
        ((0, 2, 4, 7), "add9"), ((0, 2, 4, 7, 10), "9"),
    ]
    # Try every pitch class as the root; prefer templates matching all unique notes.
    candidates = []
    for root in pcs:
        rel = tuple(sorted((pc - root) % 12 for pc in pcs))
        for intervals, suffix in templates:
            target = tuple(sorted(intervals))
            if rel == target:
                candidates.append((len(target), root, suffix))
    if not candidates:
        return ""
    _, root, suffix = max(candidates, key=lambda c: c[0])
    return f"{LETTERS[root]}{suffix}"


class KeyboardView(QWidget):
    """Рисует 88 клавиш, подсвечивает активные ноты."""
    note_clicked = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        # Высота клавиш может увеличиваться вместе с окном; основная настройка — в PianoWindow.resizeEvent.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.active_notes = set()
        self.right_notes = set()
        self.left_notes = set()
        self.flash_notes = set()
        self._white_x = {}
        self._white_w = 0.0

    def set_active_notes(self, notes, right_notes=None, left_notes=None, flash_notes=None):
        notes = set(notes or [])
        # При передаче раздельных наборов цвет показывает руку:
        # правая (скрипичный ключ) — синий, левая (басовый ключ) — зелёный.
        if right_notes is None and left_notes is None:
            right_notes, left_notes = notes, set()
        right_notes = set(right_notes or [])
        left_notes = set(left_notes or [])
        flash_notes = set()  # ?????? ??????? ?????? ?????????
        changed = (notes != self.active_notes or right_notes != self.right_notes or left_notes != self.left_notes or flash_notes != self.flash_notes)
        self.active_notes = notes
        self.right_notes = right_notes
        self.left_notes = left_notes
        self.flash_notes = flash_notes
        if changed:
            self.update()

    def _active_color(self, midi):
        right = midi in self.right_notes
        left = midi in self.left_notes
        if right and left:
            return QColor(165, 95, 220)  # одновременно обе руки
        if left:
            return QColor(45, 190, 125)  # левая рука / басовый стан
        if right:
            return QColor(55, 145, 245)  # правая рука / скрипичный стан
        return None

    def _compute_layout(self):
        w = self.width()
        n_white = sum(1 for n in range(START_NOTE, START_NOTE + NUM_KEYS) if not is_black_key(n))
        kw = w / max(1, n_white)
        self._white_w, self._white_x = kw, {}
        idx = 0
        for n in range(START_NOTE, START_NOTE + NUM_KEYS):
            if not is_black_key(n):
                self._white_x[n] = idx * kw
                idx += 1
        return kw

    def _black_x(self, midi: int, kw: float):
        prev, nxt = self._white_x.get(midi - 1), self._white_x.get(midi + 1)
        if prev is not None: return prev + kw * 0.7
        if nxt is not None: return nxt - kw * 0.3
        return 0.0

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height(); pad_top = 6; kh = h - 12; kw = self._compute_layout()
        grad_bg = QLinearGradient(0, 0, 0, h); grad_bg.setColorAt(0, QColor(250,251,253)); grad_bg.setColorAt(1, QColor(228,232,240)); p.fillRect(self.rect(), QBrush(grad_bg))
        for n in range(START_NOTE, START_NOTE + NUM_KEYS):
            if is_black_key(n): continue
            x = self._white_x[n]; rect = QRectF(x, pad_top, kw - 1, kh); active = n in self.active_notes
            active_color = self._active_color(n)
            flashing = n in self.flash_notes
            grad = QLinearGradient(x, pad_top, x, pad_top + kh)
            if flashing:
                base = active_color or QColor(255,235,120)
                grad.setColorAt(0, QColor(255,255,255)); grad.setColorAt(1, base.lighter(115))
            else:
                grad.setColorAt(0, QColor(active_color).lighter(135) if active_color else QColor(252,252,255)); grad.setColorAt(1, active_color if active_color else QColor(225,228,235))
            p.setBrush(QBrush(grad))
            p.setPen(QPen(QColor(255,200,0), 3) if flashing else QPen(QColor(60,60,70), 1))
            p.drawRoundedRect(rect, 3, 3)
            letter = note_letter(n)
            if active or letter == "C":
                label = f"{letter}{n//12-1}"
                if active:
                    # Контрастная плашка гарантирует, что название ноты видно на цветной клавише.
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(0, 0, 0, 125))
                    tag = rect.adjusted(2, kh-27, -2, -3)
                    p.drawRoundedRect(tag, 4, 4)
                    p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    p.setPen(QColor(255, 255, 255))
                    p.drawText(tag, Qt.AlignmentFlag.AlignCenter, label)
                else:
                    p.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
                    p.setPen(QColor(150,150,160))
                    p.drawText(rect.adjusted(0, kh-22, 0, -4), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, label)
        black_h, black_w = kh * .62, kw * .62
        for n in range(START_NOTE, START_NOTE + NUM_KEYS):
            if not is_black_key(n): continue
            x = self._black_x(n, kw); rect = QRectF(x, pad_top, black_w, black_h); active = n in self.active_notes
            active_color = self._active_color(n)
            flashing = n in self.flash_notes
            grad = QLinearGradient(x, pad_top, x, pad_top + black_h)
            if flashing:
                base = active_color or QColor(255,220,100)
                grad.setColorAt(0, base.lighter(160)); grad.setColorAt(1, base.lighter(120))
            else:
                grad.setColorAt(0, QColor(active_color).lighter(135) if active_color else QColor(60,62,72)); grad.setColorAt(1, active_color if active_color else QColor(10,10,15))
            p.setBrush(QBrush(grad))
            p.setPen(QPen(QColor(255,200,0), 2) if flashing else QPen(QColor(0,0,0),1))
            p.drawRoundedRect(rect,2,2)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255,255,255,40)); p.drawRoundedRect(QRectF(x+2,pad_top+2,black_w-4,4),1,1)
            if active:
                label = f"{note_letter(n)}{n//12-1}"
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(0, 0, 0, 145))
                tag = rect.adjusted(1, black_h*.35, -1, -2)
                p.drawRoundedRect(tag, 3, 3)
                p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                p.setPen(QColor(255,255,255))
                p.drawText(tag, Qt.AlignmentFlag.AlignCenter, label)
        p.end()

    def mousePressEvent(self, event):
        pos = event.position(); kw = self._white_w
        for n in range(START_NOTE, START_NOTE + NUM_KEYS):
            if is_black_key(n):
                x = self._black_x(n, kw)
                if x <= pos.x() <= x + kw*.62 and pos.y() <= self.height()*.62:
                    self.note_clicked.emit(n); return
        for n in range(START_NOTE, START_NOTE + NUM_KEYS):
            if not is_black_key(n):
                x = self._white_x.get(n,0)
                if x <= pos.x() <= x+kw:
                    self.note_clicked.emit(n); return


class PdfView(QWidget):
    """Показывает страницу PDF и примерную позицию текущего события."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding); self.setMinimumHeight(420)
        self._pixmap = None; self._cursor_xy = None; self._active_notes = set()

    def set_page(self, pixmap): self._pixmap = pixmap; self.update()
    def set_cursor(self, x: float, y: float, page=None, notes=None):
        self._cursor_xy = (float(x), float(y)); self._active_notes = set(notes or []); self.update()
    def clear_cursor(self): self._cursor_xy = None; self._active_notes = set(); self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h = self.width(),self.height(); grad = QLinearGradient(0,0,0,h); grad.setColorAt(0,QColor(245,247,250)); grad.setColorAt(1,QColor(228,232,240)); p.fillRect(self.rect(),QBrush(grad))
        if self._pixmap is None or self._pixmap.isNull():
            p.setPen(QColor(120,126,140)); p.setFont(QFont("Segoe UI",14)); p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,"PDF не загружен.\nНажми «Открыть PDF»."); p.end(); return
        pm=self._pixmap; pw,ph=pm.width(),pm.height(); scale=min(max(1,w-60)/pw,max(1,h-40)/ph); sw,sh=int(pw*scale),int(ph*scale); x0=(w-sw)//2; y0=(h-sh)//2
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(0,0,0,100)); p.drawRoundedRect(QRectF(x0+6,y0+8,sw,sh),8,8); p.setBrush(QColor(250,250,252)); p.drawRoundedRect(QRectF(x0,y0,sw,sh),6,6); p.drawPixmap(x0,y0,sw,sh,pm); p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(QColor(180,180,190),1)); p.drawRoundedRect(QRectF(x0,y0,sw,sh),6,6)
        if self._cursor_xy is not None:
            cx,cy=self._cursor_xy; dx=x0+cx*scale; dy=y0+cy*scale
            p.setPen(QPen(QColor(230,60,60,190),2)); p.drawLine(QPointF(dx,y0),QPointF(dx,y0+sh))
            # Подсветка показывает приблизительное место события, не гарантирует точное совпадение с головкой ноты.
            p.setBrush(QColor(255,215,0,85)); p.setPen(QPen(QColor(255,80,40),3)); p.drawEllipse(QPointF(dx,dy),18,13)
            p.setPen(QPen(QColor(255,255,255,220),1)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(QPointF(dx,dy),22,17)
            if self._active_notes:
                notes = sorted(self._active_notes)
                note_labels = "  ".join(f"{note_letter(n)}{n//12-1}" for n in notes)
                chord = chord_name(notes)
                # На большом/развёрнутом окне подпись заметнее; блок не выходит за границы страницы.
                font_size = 13 if w >= 1100 else 10
                p.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
                fm = p.fontMetrics()
                text = f"{chord}   |   {note_labels}" if chord else note_labels
                tw = fm.horizontalAdvance(text)
                th = fm.height()
                box_w = min(tw + 18, max(180, sw - 12))
                box_h = th + 12
                bx = dx + 26
                if bx + box_w > x0 + sw - 6:
                    bx = dx - box_w - 26
                bx = max(x0 + 6, min(bx, x0 + sw - box_w - 6))
                by = dy - box_h - 20
                if by < y0 + 6:
                    by = min(y0 + sh - box_h - 6, dy + 24)
                p.setPen(QPen(QColor(35, 45, 65, 220), 1))
                p.setBrush(QColor(255, 255, 255, 238))
                p.drawRoundedRect(QRectF(bx, by, box_w, box_h), 7, 7)
                p.setPen(QColor(25, 45, 75))
                p.drawText(QRectF(bx + 9, by + 4, box_w - 18, box_h - 8), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        p.end()


class WelcomeView(QWidget):
    def __init__(self, image_path: str = None, parent=None):
        super().__init__(parent); self.image_path=image_path; self._pixmap=QPixmap(image_path) if image_path and os.path.exists(image_path) else None; self._progress=0.0; self._status="Loading..."
        self.setMinimumSize(400,300); self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
    def set_progress(self,value:float,status:str=None):
        self._progress=max(0.0,min(1.0,float(value)))
        if status is not None: self._status=status
        self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); w,h=self.width(),self.height()
        if self._pixmap and not self._pixmap.isNull():
            scaled=self._pixmap.scaled(w,h,Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation); p.drawPixmap((w-scaled.width())//2,(h-scaled.height())//2,scaled)
        else:
            grad=QLinearGradient(0,0,0,h); grad.setColorAt(0,QColor(20,30,60)); grad.setColorAt(1,QColor(10,15,35)); p.fillRect(self.rect(),grad)
        p.fillRect(self.rect(),QColor(0,0,0,110)); p.setFont(QFont("Segoe UI",72,QFont.Weight.Bold)); p.setPen(QColor(255,255,255)); p.drawText(0,0,w,h-40,Qt.AlignmentFlag.AlignCenter,"NowPiano"); p.setFont(QFont("Segoe UI",20)); p.setPen(QColor(180,200,240)); p.drawText(0,h//2+50,w,60,Qt.AlignmentFlag.AlignCenter,"Piano Music Reader")
        if self._progress>0:
            by=h-70; bw=int(w*.6); bx=(w-bw)//2; p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255,255,255,60)); p.drawRoundedRect(bx,by,bw,6,3,3); p.setBrush(QColor(74,144,226)); p.drawRoundedRect(bx,by,int(bw*self._progress),6,3,3); p.setFont(QFont("Segoe UI",12)); p.setPen(QColor(200,210,230)); p.drawText(bx,by+15,bw,30,Qt.AlignmentFlag.AlignCenter,self._status)
        p.end()
