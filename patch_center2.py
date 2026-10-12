import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

old = "        top = 40; line_gap = max(9, min(13, (h - 100) / 12)); staff_h = 4 * line_gap"
new = """        line_gap = max(9, min(13, (h - 100) / 12)); staff_h = 4 * line_gap
        # Центрирование по вертикали: два нотоносца + отступ между ними
        _gap_between = 52  # вертикальный промежуток между верхним и нижним станом
        _used = staff_h * 2 + _gap_between + 16  # +16 запас снизу/сверху
        top = max(20, int((h - _used) / 2))"""

if old in src:
    src = src.replace(old, new, 1)
    print("[piano_qt] top -> center formula applied")
else:
    print("[piano_qt] WARNING: не нашёл строку с top = 40")

# На всякий случай — если строка 261-263 с пересчётом мешает центрированию, посмотрим:
old2 = """        if bass_y + staff_h > h - 18:
            line_gap = max(7, (h - top - 80) / 12); staff_h = 4 * line_gap
            treble_y = top + 8; bass_y = top + staff_h + 48"""
new2 = """        if bass_y + staff_h > h - 18:
            line_gap = max(7, (h - top - 80) / 12); staff_h = 4 * line_gap
            treble_y = top + 8; bass_y = top + staff_h + 48
        # Если после пересчёта снизу осталось много места — сдвинуть блок вниз
        _bottom_used = bass_y + staff_h + 8
        _extra = h - _bottom_used - top
        if _extra > 20:
            _shift = _extra // 2
            treble_y += _shift
            bass_y += _shift"""

if old2 in src:
    src = src.replace(old2, new2, 1)
    print("[piano_qt] дополнительное центрирование добавлено")
else:
    print("[piano_qt] блок пересчёта не найден (возможно, не нужен)")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
