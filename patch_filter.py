import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

new_filter = 'Ноты (*.pdf *.jpg *.jpeg *.png *.tif *.tiff *.bmp *.mid *.midi *.mxl *.musicxml *.xml);;PDF (*.pdf);;Картинки (*.jpg *.jpeg *.png *.tif *.tiff *.bmp);;MIDI (*.mid *.midi);;MusicXML (*.mxl *.musicxml *.xml);;Все файлы (*.*)'

import re
pattern = re.compile(r'(getOpenFileName\([^,]+,\s*"[^"]*",\s*)("[^"]*")')
m = pattern.search(src)
if m:
    old = m.group(0)
    new = m.group(1) + '"' + new_filter + '"'
    src = src.replace(old, new, 1)
    print("[piano_qt] filter patched")
else:
    print("[piano_qt] WARNING: getOpenFileName pattern not found")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
