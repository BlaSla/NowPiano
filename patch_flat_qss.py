import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# 1. ать кнопкам objectName (используем id-селектор #name — он самый сильный)
for name in ("btn_rewind", "btn_play", "btn_stop", "btn_loop"):
    marker = f"self.{name} = QPushButton"
    objname_line = f'self.{name}.setObjectName("{name}")'
    if objname_line in src:
        print(f"[piano_qt] {name}: objectName уже стоит")
        continue
    idx = src.find(marker)
    if idx < 0:
        print(f"[piano_qt] {name}: не найден")
        continue
    end_of_line = src.find("\n", idx)
    if end_of_line < 0:
        continue
    src = src[:end_of_line+1] + f'        {objname_line}\n' + src[end_of_line+1:]
    print(f"[piano_qt] {name}: objectName set")

# 2. ставить QSS-правила для этих кнопок в существующий setStyleSheet.
# щем конец первого self.setStyleSheet(...) и вставляем после.
marker = "self.setStyleSheet("
idx = src.find(marker)
if idx < 0:
    print("[piano_qt] WARNING: self.setStyleSheet не найден")
else:
    depth = 0
    end = -1
    for i in range(idx, len(src)):
        ch = src[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        print("[piano_qt] WARNING: не нашёл конец setStyleSheet")
    else:
        block = '''

        # лоский стиль для кнопок управления в тулбаре
        self.setStyleSheet(self.styleSheet() + """
        QPushButton#btn_rewind, QPushButton#btn_play,
        QPushButton#btn_stop, QPushButton#btn_loop {
            background: transparent;
            border: none;
            outline: none;
            padding: 2px 6px;
            border-radius: 6px;
            font-size: 18px;
        }
        QPushButton#btn_rewind:hover, QPushButton#btn_play:hover,
        QPushButton#btn_stop:hover, QPushButton#btn_loop:hover {
            background: rgba(40, 120, 208, 60);
        }
        QPushButton#btn_rewind:pressed, QPushButton#btn_play:pressed,
        QPushButton#btn_stop:pressed, QPushButton#btn_loop:pressed {
            background: rgba(40, 120, 208, 120);
        }
        """)
'''
        src = src[:end+1] + block + src[end+1:]
        print("[piano_qt] QSS for control buttons inserted")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
