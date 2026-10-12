import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# справляем лишний отступ у _icon_qss: 16 пробелов -> 8
bad = "                _icon_qss = \"\"\""
good = "        _icon_qss = \"\"\""
if bad in src:
    src = src.replace(bad, good, 1)
    print("[fix] убрал лишний отступ у _icon_qss")
else:
    print("[fix] паттерн не найден, пропуск")

# а всякий случай — то же для _play_qss (если вдруг тоже с отступом)
bad2 = "                _play_qss = \"\"\""
good2 = "        _play_qss = \"\"\""
if bad2 in src:
    src = src.replace(bad2, good2, 1)
    print("[fix] убрал лишний отступ у _play_qss")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
