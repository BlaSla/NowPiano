import io
PATH = r"C:\NowPiano\src\qt_audio.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

changes = 0

old1 = '[sys.executable, "-m", "homr", png_path],'
new1 = '[HOMR_EXE, png_path],'
if old1 in src:
    src = src.replace(old1, new1, 1)
    print("[rollback] run_homr")
    changes += 1

old2 = '[sys.executable, "-m", "homr", local_img],'
new2 = '[HOMR_EXE, local_img],'
if old2 in src:
    src = src.replace(old2, new2, 1)
    print("[rollback] run_homr_image")
    changes += 1

src = src.replace(
    'print("[homr] запускаю: " + sys.executable + " -m homr " + png_path, flush=True)',
    'print("[homr] запускаю: " + HOMR_EXE + " " + png_path, flush=True)', 1)
src = src.replace(
    'print("[homr-img] запускаю: " + sys.executable + " -m homr " + local_img, flush=True)',
    'print("[homr-img] запускаю: " + HOMR_EXE + " " + local_img, flush=True)', 1)
src = src.replace(
    'subprocess.list2cmdline([sys.executable, "-m", "homr", png_path])',
    'subprocess.list2cmdline([HOMR_EXE, png_path])', 1)
src = src.replace(
    'subprocess.list2cmdline([sys.executable, "-m", "homr", local_img])',
    'subprocess.list2cmdline([HOMR_EXE, local_img])', 1)

print(f"[rollback] {changes} замен")
with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
