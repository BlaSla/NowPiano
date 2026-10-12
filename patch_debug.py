import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# 1. Отладка в начале _tick
old1 = """    def _tick(self):
        if not self.is_playing:
            return"""
new1 = """    def _tick(self):
        print("[tick] pos=%.2f dur=%.2f playing=%s loop=%s" % (self.position, self.duration, self.is_playing, self.loop_enabled), flush=True)
        if not self.is_playing:
            return"""
if old1 in src:
    src = src.replace(old1, new1, 1)
    print("[debug] _tick instrumented")
else:
    print("[debug] WARNING: _tick start not found")

# 2. Отладка в loop-блоке
old2 = """            if self.loop_enabled:
                self.position = 0.0"""
new2 = """            if self.loop_enabled:
                print("[loop] Restarting playback", flush=True)
                self.position = 0.0"""
if old2 in src:
    src = src.replace(old2, new2, 1)
    print("[debug] loop block instrumented")
else:
    print("[debug] WARNING: loop block not found")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
