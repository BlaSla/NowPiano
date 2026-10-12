import io
PATH = r"C:\NowPiano\src\qt_audio.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

if "import sys" in src:
    print("[qt_audio] import sys уже есть")
else:
    # Добавим import sys в начало файла (после docstring, если он есть)
    lines = src.split("\n")
    insert_at = 0
    # Пропустить docstring
    in_doc = False
    for i, line in enumerate(lines[:20]):
        s = line.strip()
        if s.startswith('"""') or s.startswith("'''"):
            if in_doc:
                in_doc = False
                insert_at = i + 1
                continue
            if s.count('"""') == 1 or s.count("'''") == 1:
                in_doc = True
                continue
            else:
                insert_at = i + 1
                continue
        if not in_doc and s and not s.startswith("#"):
            insert_at = i
            break
    lines.insert(insert_at, "import sys")
    src = "\n".join(lines)
    print(f"[qt_audio] import sys добавлен на строку {insert_at + 1}")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
