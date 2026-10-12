import io
PATH = r"C:\NowPiano\src\qt_audio.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

old = '''    if getattr(_sys, "frozen", False):
        exe_dir = os.path.dirname(_sys.executable)
        candidates.append(os.path.join(exe_dir, "homr.exe"))
        candidates.append(os.path.join(exe_dir, "_internal", "homr.exe"))'''

new = '''    if getattr(_sys, "frozen", False):
        exe_dir = os.path.dirname(_sys.executable)
        candidates.append(os.path.join(exe_dir, "homr.exe"))
        candidates.append(os.path.join(exe_dir, "_internal", "homr.exe"))
        candidates.append(os.path.join(exe_dir, "venv", "Scripts", "homr.exe"))
        candidates.append(os.path.join(exe_dir, "_internal", "venv", "Scripts", "homr.exe"))
        candidates.append(os.path.join(exe_dir, "venv", "Scripts", "homr"))'''

if old in src:
    src = src.replace(old, new, 1)
    print("[piano_qt] _find_homr: добавлены пути venv\\Scripts для exe")
else:
    print("[piano_qt] WARNING: не нашёл блок _find_homr")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
