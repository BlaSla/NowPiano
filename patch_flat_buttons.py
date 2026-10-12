import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# 1. обавить setFlat(True) и убрать рамку/фон для кнопок навигации
old = '''        self.btn_rewind = QPushButton("⏪")'''
new = '''        self.btn_rewind = QPushButton("⏪")
        self.btn_rewind.setFlat(True)'''
if old in src and "self.btn_rewind.setFlat(True)" not in src:
    src = src.replace(old, new, 1)
    print("[piano_qt] btn_rewind setFlat")
else:
    print("[piano_qt] btn_rewind skip или уже пропатчено")

old = '''        self.btn_play = QPushButton("▶")'''
new = '''        self.btn_play = QPushButton("▶")
        self.btn_play.setFlat(True)'''
if old in src and "self.btn_play.setFlat(True)" not in src:
    src = src.replace(old, new, 1)
    print("[piano_qt] btn_play setFlat")
else:
    print("[piano_qt] btn_play skip или уже пропатчено")

old = '''        self.btn_stop = QPushButton("⏹")'''
new = '''        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setFlat(True)'''
if old in src and "self.btn_stop.setFlat(True)" not in src:
    src = src.replace(old, new, 1)
    print("[piano_qt] btn_stop setFlat")
else:
    print("[piano_qt] btn_stop skip или уже пропатчено")

old = '''        self.btn_loop = QPushButton("🔁")'''
new = '''        self.btn_loop = QPushButton("🔁")
        self.btn_loop.setFlat(True)'''
if old in src and "self.btn_loop.setFlat(True)" not in src:
    src = src.replace(old, new, 1)
    print("[piano_qt] btn_loop setFlat")
else:
    print("[piano_qt] btn_loop skip или уже пропатчено")

# 2. Также сделать "Open" и "MIDI" плоскими? ет, оставим их как есть —
# они должны выглядеть как обычные кнопки, чтобы пользователь их видел.

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
