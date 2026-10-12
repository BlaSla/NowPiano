import io
PATH = r"C:\NowPiano\src\qt_audio.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

if "def run_homr(" in src:
    print("[qt_audio] run_homr уже есть, пропуск")
else:
    insert = '''def run_homr(pdf_path):
    """Fallback: конвертирует PDF в PNG (первая страница) и запускает homr."""
    if not os.path.isfile(pdf_path):
        raise RuntimeError("PDF-файл не найден: " + pdf_path)
    if not HOMR_EXE or (os.path.isabs(HOMR_EXE) and not os.path.isfile(HOMR_EXE)):
        raise RuntimeError("homr не найден: " + str(HOMR_EXE))
    if not PDFTOPPM_EXE or not os.path.isfile(PDFTOPPM_EXE):
        raise RuntimeError("pdftoppm.exe не найден: " + str(PDFTOPPM_EXE))

    os.makedirs(OMR_OUTPUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]

    import tempfile, shutil
    tmpdir = tempfile.mkdtemp(prefix="homr_")
    png_base = os.path.join(tmpdir, "page")

    print("[homr] конвертирую PDF в PNG: " + pdf_path, flush=True)
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

    print("[homr] запускаю: " + HOMR_EXE + " " + png_path, flush=True)
    try:
        result = subprocess.run(
            [HOMR_EXE, png_path],
            check=False, text=True,
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
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass

    return final_path


'''
    marker = "def _image_to_pdf("
    if marker in src:
        src = src.replace(marker, insert + marker, 1)
        print("[qt_audio] inserted run_homr")
    else:
        marker2 = "def run_homr_image("
        if marker2 in src:
            src = src.replace(marker2, insert + marker2, 1)
            print("[qt_audio] inserted run_homr (before run_homr_image)")
        else:
            print("[qt_audio] WARNING: не нашёл куда вставить")

    with io.open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
print("DONE")
