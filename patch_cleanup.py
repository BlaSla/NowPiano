import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# 1. Убрать print из _tick
old1 = """    def _tick(self):
        print("[tick] pos=%.2f dur=%.2f playing=%s loop=%s" % (self.position, self.duration, self.is_playing, self.loop_enabled), flush=True)
        if not self.is_playing:
            return"""
new1 = """    def _tick(self):
        if not self.is_playing:
            return"""
if old1 in src:
    src = src.replace(old1, new1, 1)
    print("[debug] _tick print removed")
else:
    print("[debug] WARNING: _tick print not found (уже убран?)")

# 2. Убрать print из loop-блока
old2 = """            if self.loop_enabled:
                print("[loop] Restarting playback", flush=True)
                self.position = 0.0"""
new2 = """            if self.loop_enabled:
                self.position = 0.0"""
if old2 in src:
    src = src.replace(old2, new2, 1)
    print("[debug] loop print removed")
else:
    print("[debug] WARNING: loop print not found (уже убран?)")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
