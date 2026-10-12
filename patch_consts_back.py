import io
PATH = r"C:\NowPiano\src\qt_audio.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

if "HOMR_EXE = _find_homr()" in src and "PDFTOPPM_EXE = _find_pdftoppm()" in src:
    print("[qt_audio] HOMR_EXE и PDFTOPPM_EXE уже есть, пропуск")
else:
    insert = '''
# ---------- homr (fallback OMR) ----------
def _find_homr():
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    candidates = [os.path.join(proj, "venv", "Scripts", "homr.exe")]
    if getattr(_sys, "frozen", False):
        exe_dir = os.path.dirname(_sys.executable)
        candidates.append(os.path.join(exe_dir, "homr.exe"))
        candidates.append(os.path.join(exe_dir, "_internal", "homr.exe"))
    from shutil import which
    w = which("homr")
    if w:
        candidates.append(w)
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return "homr"

def _find_pdftoppm():
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    candidates = [
        os.path.join(proj, "tools", "poppler", "Library", "bin", "pdftoppm.exe"),
        os.path.join(proj, "tools", "poppler", "bin", "pdftoppm.exe"),
    ]
    if getattr(_sys, "frozen", False):
        exe_dir = os.path.dirname(_sys.executable)
        candidates.append(os.path.join(exe_dir, "_internal", "tools", "poppler", "Library", "bin", "pdftoppm.exe"))
        candidates.append(os.path.join(exe_dir, "_internal", "poppler", "Library", "bin", "pdftoppm.exe"))
        candidates.append(os.path.join(exe_dir, "tools", "poppler", "Library", "bin", "pdftoppm.exe"))
    from shutil import which
    w = which("pdftoppm")
    if w:
        candidates.append(w)
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None

HOMR_EXE = _find_homr()
PDFTOPPM_EXE = _find_pdftoppm()

'''
    # Вставляем после AUDIVERIS_EXE
    marker = "AUDIVERIS_EXE = _find_audiveris()"
    if marker in src:
        src = src.replace(marker, marker + "\n" + insert, 1)
        print("[qt_audio] inserted HOMR_EXE/PDFTOPPM_EXE and helpers")
    else:
        # Fallback: перед # ---------- Audiveris
        marker2 = "# ---------- Audiveris"
        if marker2 in src:
            src = src.replace(marker2, insert + marker2, 1)
            print("[qt_audio] inserted constants (before Audiveris)")
        else:
            print("[qt_audio] WARNING: не нашёл куда вставить")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
