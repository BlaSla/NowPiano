import io
PATH = r"C:\NowPiano\src\qt_audio.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

if "def _image_to_pdf(" in src:
    print("[qt_audio] _image_to_pdf уже есть, пропуск")
else:
    helper = '''def _image_to_pdf(img_path):
    """Конвертирует картинку в PDF (для fallback на Audiveris)."""
    from PIL import Image
    pdf_path = os.path.splitext(img_path)[0] + ".__conv.pdf"
    img = Image.open(img_path).convert("RGB")
    img.save(pdf_path, "PDF", resolution=300.0)
    return pdf_path


'''
    # Вставляем _image_to_pdf перед run_homr_image
    marker = "def run_homr_image("
    if marker in src:
        src = src.replace(marker, helper + marker, 1)
        print("[qt_audio] inserted _image_to_pdf")
    else:
        # fallback: вставить перед "# ---------- MusicXML"
        marker2 = "# ---------- MusicXML"
        if marker2 in src:
            src = src.replace(marker2, helper + marker2, 1)
            print("[qt_audio] inserted _image_to_pdf (before MusicXML marker)")
        else:
            print("[qt_audio] WARNING: не нашёл куда вставить")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
