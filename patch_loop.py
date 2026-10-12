import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

old = """        if self.position >= self.duration:
            if self.loop_enabled:
                self.position = 0.0
                self._next_event_idx = 0
                self._elapsed.restart()
                self.audio.all_off()
            else:"""

new = """        if self.position >= self.duration:
            if self.loop_enabled:
                self.position = 0.0
                self._next_event_idx = 0
                self._elapsed.restart()
                self.audio.all_off()
                self.is_playing = True
                self.btn_play.setText("\u23f8")
                self.keyboard.set_active_notes(set(), set(), set())
                try:
                    self.staff_view.set_position(0.0, set())
                except Exception:
                    pass
                self.chord_label.clear()
                self._update_time_label()
            else:"""

if old in src:
    src = src.replace(old, new, 1)
    print("[piano_qt] loop block patched")
else:
    print("[piano_qt] WARNING: old block not found — проверьте вручную")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
