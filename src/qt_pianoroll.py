# -*- coding: utf-8 -*-
"""qt_pianoroll.py - Piano roll widget."""
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QLinearGradient
from PyQt6.QtWidgets import QWidget, QSizePolicy

PALETTE = [QColor(220,40,40), QColor(30,120,255), QColor(255,160,0), QColor(15,157,88), QColor(171,71,188), QColor(0,172,193)]

class PianoRollView(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding); self.setMinimumHeight(300)
        self.events=[]; self.duration=0.0; self.position=0.0; self.original_bpm=120.0; self.left_margin=60; self.top_margin=20; self.bottom_margin=30
    def set_events(self,events,duration,original_bpm):
        self.events=list(events or []); self.duration=max(.1,float(duration)); self.original_bpm=max(1.,float(original_bpm)); self.position=0.; self.update()
    def set_position(self,seconds): self.position=float(seconds); self.update()
    def _time_to_x(self,t,w): return self.left_margin+max(0.,min(1.,t/self.duration))*(w-self.left_margin-20)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); w,h=self.width(),self.height(); grad=QLinearGradient(0,0,0,h); grad.setColorAt(0,QColor(248,250,253)); grad.setColorAt(1,QColor(230,235,242)); p.fillRect(self.rect(),QBrush(grad))
        if not self.events:
            p.setPen(QColor(120,126,140)); p.setFont(QFont("Segoe UI",14)); p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,"No notes loaded."); p.end(); return
        beat=60./self.original_bpm; t=0.; p.setPen(QPen(QColor(200,208,220),1))
        while t<=self.duration:
            x=self._time_to_x(t,w); p.drawLine(QPointF(x,self.top_margin),QPointF(x,h-self.bottom_margin)); t+=beat*4
        parts=sorted(set(getattr(e,"part",0) for e in self.events)); top=self.top_margin; bottom=h-self.bottom_margin; band_h=(bottom-top)/max(1,len(parts))
        p.setPen(QPen(QColor(180,188,200,120),1,Qt.PenStyle.DashLine))
        for i in range(1,len(parts)): p.drawLine(QPointF(0,top+i*band_h),QPointF(w,top+i*band_h))
        all_notes=[m for e in self.events for m in e.notes]; lo=min(all_notes) if all_notes else 40; hi=max(all_notes) if all_notes else 80
        if hi<=lo: hi=lo+1
        for ev in self.events:
            part=getattr(ev,"part",0); bi=parts.index(part) if part in parts else 0; bt=top+bi*band_h; bb=bt+band_h; x1=self._time_to_x(ev.time_seconds,w); x2=max(x1+2,self._time_to_x(ev.time_seconds+ev.duration,w)); p.setBrush(QBrush(PALETTE[part%len(PALETTE)])); p.setPen(Qt.PenStyle.NoPen)
            for midi in ev.notes:
                frac=max(0.,min(1.,(midi-lo)/(hi-lo))); y=bb-frac*(bb-bt)-3; p.drawRoundedRect(QRectF(x1,y,x2-x1,6),2,2)
        cx=self._time_to_x(self.position,w); p.setPen(QPen(QColor(220,40,40,220),2)); p.drawLine(QPointF(cx,self.top_margin),QPointF(cx,h-self.bottom_margin)); p.setPen(QPen(QColor(180,188,200),1)); p.drawRect(self.rect().adjusted(0,0,-1,-1)); p.end()
