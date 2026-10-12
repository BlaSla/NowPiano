import io
PATH = r"C:\NowPiano\src\qt_audio.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

changes = 0

# 1. Диагностические print
old1 = 'print("[homr] запускаю: " + HOMR_EXE + " " + png_path, flush=True)'
new1 = 'print("[homr] запускаю: " + sys.executable + " -m homr " + png_path, flush=True)'
if old1 in src:
    src = src.replace(old1, new1, 1)
    print("[fix] print в run_homr")
    changes += 1

old2 = 'print("[homr-img] запускаю: " + HOMR_EXE + " " + local_img, flush=True)'
new2 = 'print("[homr-img] запускаю: " + sys.executable + " -m homr " + local_img, flush=True)'
if old2 in src:
    src = src.replace(old2, new2, 1)
    print("[fix] print в run_homr_image")
    changes += 1

# 2. list2cmdline в сообщениях об ошибках
old3 = 'subprocess.list2cmdline([HOMR_EXE, png_path])'
new3 = 'subprocess.list2cmdline([sys.executable, "-m", "homr", png_path])'
if old3 in src:
    src = src.replace(old3, new3, 1)
    print("[fix] list2cmdline в run_homr")
    changes += 1

old4 = 'subprocess.list2cmdline([HOMR_EXE, local_img])'
new4 = 'subprocess.list2cmdline([sys.executable, "-m", "homr", local_img])'
if old4 in src:
    src = src.replace(old4, new4, 1)
    print("[fix] list2cmdline в run_homr_image")
    changes += 1

# 3. Проверки "homr не найден" — заменить на проверку модуля, а не exe
# (для простоты оставляем, но поменяем сообщение)
old5 = '    if not HOMR_EXE or (os.path.isabs(HOMR_EXE) and not os.path.isfile(HOMR_EXE)):\n        raise RuntimeError("homr не найден: " + str(HOMR_EXE))\n'
new5 = '    # homr запускается через sys.executable -m homr, отдельный exe не нужен\n'
count5 = src.count(old5)
if count5 > 0:
    src = src.replace(old5, new5)
    print(f"[fix] удалено {count5} проверок HOMR_EXE")
    changes += count5

print(f"[qt_audio] {changes} замен")
with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
