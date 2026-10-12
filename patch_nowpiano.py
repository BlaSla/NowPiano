# patch_nowpiano.py
import io, os

QT_AUDIO = r"C:\NowPiano\src\qt_audio.py"
PIANO_QT = r"C:\NowPiano\src\piano_qt.py"

with io.open(QT_AUDIO, "r", encoding="utf-8") as f:
    src = f.read()

marker1 = "AUDIVERIS_EXE = _find_audiveris()"
if "HOMR_EXE = _find_homr()" not in src:
    insert1 = """

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
"""
    src = src.replace(marker1, marker1 + insert1, 1)
    print("[qt_audio] inserted constants")
else:
    print("[qt_audio] constants already present")

marker2 = "# ---------- MusicXML"
if "def run_homr(" not in src:
    insert2 = '''# ---------- homr fallback ----------
def run_homr(pdf_path):
    """Fallback: конвертирует PDF в PNG (первая страница) и запускает homr."""
    if not os.path.isfile(pdf_path):
        raise RuntimeError("PDF-файл не найден: " + pdf_path)
    if not HOMR_EXE or (os.path.isabs(HOMR_EXE) and not os.path.isfile(HOMR_EXE)):
        raise RuntimeError("homr не найден: " + str(HOMR_EXE))
    if not PDFTOPPM_EXE or not os.path.isfile(PDFTOPPM_EXE):
        raise RuntimeError("pdftoppm.exe не найден: " + str(PDFTOPPM_EXE))

    os.makedirs(OMR_OUTPUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]

    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="homr_")
    png_base = os.path.join(tmpdir, "page")

    try:
        subprocess.run(
            [PDFTOPPM_EXE, "-png", "-r", "300", "-f", "1", "-l", "1",
             pdf_path, png_base],
            check=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("pdftoppm не завершил конвертацию за 3 минуты.") from exc
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()[-2000:]
        raise RuntimeError("pdftoppm упал: " + details) from exc
    except OSError as exc:
        raise RuntimeError("Не удалось запустить pdftoppm: " + str(exc)) from exc

    png_path = None
    for f in sorted(os.listdir(tmpdir)):
        if f.lower().endswith(".png"):
            png_path = os.path.join(tmpdir, f)
            break
    if not png_path:
        raise RuntimeError("pdftoppm не создал PNG.")

    env = os.environ.copy()
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    venv_scripts = os.path.join(proj, "venv", "Scripts")
    if os.path.isdir(venv_scripts):
        env["PATH"] = venv_scripts + os.pathsep + env.get("PATH", "")

    try:
        result = subprocess.run(
            [HOMR_EXE, png_path],
            check=False, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=900, env=env,
            cwd=tmpdir
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("homr не завершил распознавание за 15 минут.") from exc
    except OSError as exc:
        raise RuntimeError("Не удалось запустить homr: " + str(exc)) from exc

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "homr не вывел подробностей").strip()
        details = details[-3000:]
        raise RuntimeError(
            "homr завершился с кодом " + str(result.returncode) + ".\\n"
            "Команда: " + subprocess.list2cmdline([HOMR_EXE, png_path]) + "\\n"
            "Вывод homr:\\n" + details
        )

    created = os.path.splitext(png_path)[0] + ".musicxml"
    if not os.path.isfile(created):
        for f in os.listdir(tmpdir):
            if f.lower().endswith((".musicxml", ".xml")):
                created = os.path.join(tmpdir, f)
                break
    if not os.path.isfile(created):
        raise RuntimeError("homr не создал MusicXML.")

    final_path = os.path.join(OMR_OUTPUT_DIR, base + ".musicxml")
    if os.path.isfile(final_path):
        try:
            os.remove(final_path)
        except OSError:
            pass
    os.replace(created, final_path)

    try:
        import shutil as _sh
        _sh.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass

    return final_path


'''
    src = src.replace(marker2, insert2 + marker2, 1)
    print("[qt_audio] inserted run_homr")
else:
    print("[qt_audio] run_homr already present")

with io.open(QT_AUDIO, "w", encoding="utf-8") as f:
    f.write(src)

with io.open(PIANO_QT, "r", encoding="utf-8") as f:
    src = f.read()

old_import = "AudioEngine, run_audiveris, musicxml_to_events,"
new_import = "AudioEngine, run_audiveris, run_homr, musicxml_to_events,"
if new_import not in src and old_import in src:
    src = src.replace(old_import, new_import, 1)
    print("[piano_qt] patched import")
else:
    print("[piano_qt] import already patched or not found")

old_block = """            try:
                mxl = run_audiveris(path)
            except Exception as e:
                msg = f"Audiveris не смог распознать ноты: {e}"
                print("[audiveris]", msg, flush=True)
                if gen != self._load_gen:
                    return
                self.sig_load_done.emit(None, MANUAL_BPM, msg)
                return
            if not mxl or not os.path.exists(mxl):
                if gen != self._load_gen:
                    return
                self.sig_load_done.emit(None, MANUAL_BPM,
                    "Audiveris не вернул MXL. Попробуйте другой PDF.")
                return"""

new_block = '''            mxl = None
            e_aud = None
            try:
                mxl = run_audiveris(path)
            except Exception as e:
                e_aud = e
                print("[audiveris] ошибка:", e, flush=True)

            if (not mxl) or (not os.path.exists(mxl)):
                self.sig_status.emit("Audiveris не справился — пробую homr...")
                try:
                    mxl = run_homr(path)
                except Exception as e_homr:
                    msg = ("Ни Audiveris, ни homr не смогли распознать ноты.\\n"
                           "Audiveris: " + str(e_aud) + "\\n"
                           "homr: " + str(e_homr))
                    print("[homr]", msg, flush=True)
                    if gen != self._load_gen:
                        return
                    self.sig_load_done.emit(None, MANUAL_BPM, msg)
                    return

            if not mxl or not os.path.exists(mxl):
                if gen != self._load_gen:
                    return
                self.sig_load_done.emit(None, MANUAL_BPM,
                    "Ни Audiveris, ни homr не вернули MXL. Попробуйте другой PDF.")
                return'''

if old_block in src:
    src = src.replace(old_block, new_block, 1)
    print("[piano_qt] patched recognition block")
else:
    print("[piano_qt] WARNING: old block not found — проверьте вручную")

with io.open(PIANO_QT, "w", encoding="utf-8") as f:
    f.write(src)

print("DONE")
