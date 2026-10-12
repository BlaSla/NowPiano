import io
PATH = r"C:\NowPiano\src\qt_audio.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# 1. Убрать capture_output из вызова homr, чтобы прогресс шёл в консоль
old = """    try:
        result = subprocess.run(
            [HOMR_EXE, png_path],
            check=False, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=900, env=env,
            cwd=tmpdir
        )"""
new = """    print("[homr] запускаю: " + HOMR_EXE + " " + png_path, flush=True)
    try:
        result = subprocess.run(
            [HOMR_EXE, png_path],
            check=False, text=True,
            encoding="utf-8", errors="replace", timeout=900, env=env,
            cwd=tmpdir
        )"""
if old in src:
    src = src.replace(old, new, 1)
    print("[qt_audio] patched: homr stdout будет виден вживую")
else:
    print("[qt_audio] WARNING: не нашёл блок subprocess.run для homr")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
