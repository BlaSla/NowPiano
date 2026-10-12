import io
PATH = r"C:\NowPiano\src\qt_audio.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

changes = 0

# 1. run_homr — заменить вызов
old1 = "            [HOMR_EXE, png_path],"
new1 = '            [sys.executable, "-m", "homr", png_path],'
if old1 in src:
    src = src.replace(old1, new1, 1)
    print("[qt_audio] run_homr: -> python -m homr")
    changes += 1
else:
    print("[qt_audio] run_homr: вызов не найден (уже пропатчен?)")

# 2. run_homr_image — заменить вызов
old2 = "            [HOMR_EXE, local_img],"
new2 = '            [sys.executable, "-m", "homr", local_img],'
if old2 in src:
    src = src.replace(old2, new2, 1)
    print("[qt_audio] run_homr_image: -> python -m homr")
    changes += 1
else:
    print("[qt_audio] run_homr_image: вызов не найден (уже пропатчен?)")

# 3. Проверим, что 'import sys' есть
if "import sys" not in src:
    # добавим в начало
    src = "import sys\n" + src
    print("[qt_audio] added 'import sys'")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print(f"DONE ({changes} замен)")
