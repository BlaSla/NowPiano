import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

changes = 0

# 1. сновное расстояние: 85 -> 170
old1 = "bass_y = top + staff_h + 85"
new1 = "bass_y = top + staff_h + 170"
if old1 in src:
    src = src.replace(old1, new1, 1)
    print("[piano_qt] bass_y: 85 -> 170")
    changes += 1

# 2. езервный отступ: 80 -> 160
old2 = "bass_y = top + staff_h + 80"
new2 = "bass_y = top + staff_h + 160"
if old2 in src:
    src = src.replace(old2, new2, 1)
    print("[piano_qt] bass_y (резерв): 80 -> 160")
    changes += 1

# 3. _gap_between в формуле центрирования: 85 -> 170
old3 = "_gap_between = 85"
new3 = "_gap_between = 170"
if old3 in src:
    src = src.replace(old3, new3, 1)
    print("[piano_qt] _gap_between: 85 -> 170")
    changes += 1

if changes == 0:
    print("[piano_qt] не нашёл ни одного места для замены")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
