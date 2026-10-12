import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

old = '''        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть", "Ноты (*.pdf *.jpg *.jpeg *.png *.tif *.tiff *.bmp *.mid *.midi *.mxl *.musicxml *.xml);;PDF (*.pdf);;Картинки (*.jpg *.jpeg *.png *.tif *.tiff *.bmp);;MIDI (*.mid *.midi);;MusicXML (*.mxl *.musicxml *.xml);;Все файлы (*.*)", "Музыка (*.pdf *.mid *.midi);;PDF (*.pdf);;MIDI (*.mid *.midi);;Все файлы (*.*)"
        )'''

new = '''        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть",
            "",
            "Ноты (*.pdf *.jpg *.jpeg *.png *.tif *.tiff *.bmp *.mid *.midi *.mxl *.musicxml *.xml);;"
            "PDF (*.pdf);;"
            "Картинки (*.jpg *.jpeg *.png *.tif *.tiff *.bmp);;"
            "MIDI (*.mid *.midi);;"
            "MusicXML (*.mxl *.musicxml *.xml);;"
            "Все файлы (*.*)"
        )'''

if old in src:
    src = src.replace(old, new, 1)
    print("[piano_qt] getOpenFileName patched (правильный порядок аргументов)")
else:
    print("[piano_qt] WARNING: old block not found")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
