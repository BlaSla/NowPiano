import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

changes = 0

# 1. сновное расстояние между станами: 52 -> 85
old1 = "treble_y = top + 8; bass_y = top + staff_h + 52"
new1 = "treble_y = top + 8; bass_y = top + staff_h + 85"
if old1 in src:
    src = src.replace(old1, new1, 1)
    print("[piano_qt] bass_y: 52 -> 85")
    changes += 1

# 2. езервный отступ (в блоке пересчёта, если ширина маленькая): 48 -> 80
old2 = "treble_y = top + 8; bass_y = top + staff_h + 48"
new2 = "treble_y = top + 8; bass_y = top + staff_h + 80"
if old2 in src:
    src = src.replace(old2, new2, 1)
    print("[piano_qt] bass_y (резерв): 48 -> 80")
    changes += 1

# 3.  патче центрирования _gap_between = 52 -> 85 (чтобы формула совпадала)
old3 = "_gap_between = 52"
new3 = "_gap_between = 85"
if old3 in src:
    src = src.replace(old3, new3, 1)
    print("[piano_qt] _gap_between: 52 -> 85")
    changes += 1

if changes == 0:
    print("[piano_qt] не нашёл ни одного места для замены")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
