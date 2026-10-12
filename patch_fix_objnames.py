import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

removed = 0

# Удаляем строку self.btn_play.setObjectName("play")
line1 = '        self.btn_play.setObjectName("play")\n'
if line1 in src:
    src = src.replace(line1, "", 1)
    print("[piano_qt] removed btn_play.setObjectName(\"play\")")
    removed += 1

# Удаляем строку self.btn_stop.setObjectName("stop")
line2 = '        self.btn_stop.setObjectName("stop")\n'
if line2 in src:
    src = src.replace(line2, "", 1)
    print("[piano_qt] removed btn_stop.setObjectName(\"stop\")")
    removed += 1

if removed == 0:
    print("[piano_qt] ничего удалять не пришлось — возможно, уже чисто")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
