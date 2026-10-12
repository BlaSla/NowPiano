import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# 1. Найти в paintEvent (класс StaffView) блок с вычислением vertical layout.
# Ищем паттерн вида: treble_y = ... ; bass_y = ...
import re

# Проверим, есть ли уже центрирование
if "# CENTER STAVES" in src:
    print("[piano_qt] центрирование уже добавлено, пропуск")
else:
    # Найти строку с "treble_y =" и "bass_y ="
    pat = re.compile(r'(\n\s*)treble_y\s*=\s*([^\n]+)\n(\s*)bass_y\s*=\s*([^\n]+)')
    m = pat.search(src)
    if m:
        indent = m.group(1) + "    "
        old_block = m.group(0)
        # Вставляем центрирование: отступ сверху = (h - used) / 2
        new_block = (
            m.group(1) + "treble_y = " + m.group(2) + "\n"
            + m.group(3) + "bass_y = " + m.group(4) + "\n"
            + indent + "# CENTER STAVES: сдвинуть нотоносцы к середине по вертикали\n"
            + indent + "try:\n"
            + indent + "    _h = self.height()\n"
            + indent + "    _top = min(treble_y, bass_y)\n"
            + indent + "    _bot = max(treble_y, bass_y) + line_gap * 12\n"
            + indent + "    _used = _bot - _top\n"
            + indent + "    _offset = max(0, (_h - _used) // 2 - _top)\n"
            + indent + "    if _offset > 0:\n"
            + indent + "        treble_y += _offset\n"
            + indent + "        bass_y += _offset\n"
            + indent + "except Exception:\n"
            + indent + "    pass"
        )
        src = src.replace(old_block, new_block, 1)
        print("[piano_qt] центрирование нотоносцев добавлено")
    else:
        print("[piano_qt] WARNING: не нашёл treble_y / bass_y")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
