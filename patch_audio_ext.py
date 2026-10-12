import io
PATH = r"C:\NowPiano\src\qt_audio.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# 1. Добавить _image_to_pdf перед run_homr_image
helper = '''

def _image_to_pdf(img_path):
    """Конвертирует картинку в PDF (для fallback на Audiveris)."""
    from PIL import Image
    pdf_path = os.path.splitext(img_path)[0] + ".__conv.pdf"
    img = Image.open(img_path).convert("RGB")
    img.save(pdf_path, "PDF", resolution=300.0)
    return pdf_path

'''
if "def _image_to_pdf(" not in src:
    marker = "def run_homr_image("
    if marker in src:
        src = src.replace(marker, helper.lstrip("\n") + marker, 1)
        print("[qt_audio] inserted _image_to_pdf")
    else:
        print("[qt_audio] WARNING: run_homr_image not found")
else:
    print("[qt_audio] _image_to_pdf already exists")

# 2. Добавить run_homr_image перед маркером MusicXML
if "def run_homr_image(" not in src:
    insert = '''# ---------- homr для картинок ----------
def run_homr_image(image_path):
    """homr для картинки (PNG/JPG) — без конвертации PDF."""
    if not os.path.isfile(image_path):
        raise RuntimeError("Картинка не найдена: " + image_path)
    if not HOMR_EXE or (os.path.isabs(HOMR_EXE) and not os.path.isfile(HOMR_EXE)):
        raise RuntimeError("homr не найден: " + str(HOMR_EXE))

    os.makedirs(OMR_OUTPUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(image_path))[0]

    env = os.environ.copy()
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    venv_scripts = os.path.join(proj, "venv", "Scripts")
    if os.path.isdir(venv_scripts):
        env["PATH"] = venv_scripts + os.pathsep + env.get("PATH", "")

    import shutil, tempfile
    tmpdir = tempfile.mkdtemp(prefix="homr_img_")
    local_img = os.path.join(tmpdir, os.path.basename(image_path))
    shutil.copy2(image_path, local_img)

    print("[homr-img] запускаю: " + HOMR_EXE + " " + local_img, flush=True)
    try:
        result = subprocess.run(
            [HOMR_EXE, local_img],
            check=False, text=True,
            encoding="utf-8", errors="replace", timeout=900, env=env,
            cwd=tmpdir
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("homr не завершил распознавание за 15 минут.") from exc
    except OSError as exc:
        raise RuntimeError("Не удалось запустить homr: " + str(exc)) from exc

    if result.returncode != 0:
        raise RuntimeError(
            "homr завершился с кодом " + str(result.returncode) + ".\\n"
            "Команда: " + subprocess.list2cmdline([HOMR_EXE, local_img])
        )

    created = os.path.splitext(local_img)[0] + ".musicxml"
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
    marker = "# ---------- MusicXML"
    if marker in src:
        src = src.replace(marker, insert + marker, 1)
        print("[qt_audio] inserted run_homr_image")
    else:
        print("[qt_audio] WARNING: MusicXML marker not found")
else:
    print("[qt_audio] run_homr_image already exists")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
