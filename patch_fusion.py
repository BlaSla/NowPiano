import io, re
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

if 'setStyle("Fusion")' in src:
    print("[piano_qt] Fusion уже установлен")
else:
    m = re.search(r'(\s*)(\w+)\s*=\s*QApplication\(sys\.argv\)', src)
    if m:
        indent = m.group(1)
        varname = m.group(2)
        old = m.group(0)
        new = old + f'\n{indent}{varname}.setStyle("Fusion")'
        src = src.replace(old, new, 1)
        print(f"[piano_qt] setStyle(Fusion) добавлен после {varname} = QApplication(...)")
    else:
        print("[piano_qt] WARNING: QApplication(...) не найден")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
