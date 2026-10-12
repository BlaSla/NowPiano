import io
PATH = r"C:\NowPiano\src\qt_audio.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

if "\nimport sys\n" in src or src.startswith("import sys\n"):
    print("[qt_audio] обычный 'import sys' уже есть")
else:
    # Добавим 'import sys' прямо перед 'import sys as _sys'
    old = "import sys as _sys"
    if old in src:
        src = src.replace(old, "import sys\nimport sys as _sys", 1)
        print("[qt_audio] добавлен 'import sys' перед 'import sys as _sys'")
    else:
        # если и этого нет — добавим в начало
        src = "import sys\n" + src
        print("[qt_audio] добавлен 'import sys' в начало файла")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
