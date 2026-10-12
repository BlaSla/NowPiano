import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# 1. Импорт: добавить run_homr, run_homr_image, _image_to_pdf
old_imp = "AudioEngine, run_audiveris, musicxml_to_events,"
new_imp = "AudioEngine, run_audiveris, run_homr, run_homr_image, _image_to_pdf, musicxml_to_events,"
if new_imp not in src and old_imp in src:
    src = src.replace(old_imp, new_imp, 1)
    print("[piano_qt] import patched")
else:
    print("[piano_qt] import already patched or not found")

# 2. Заменить блок распознавания (текущий, старый — только Audiveris)
old_block = """            # 2. Audiveris
            self.sig_status.emit("Шаг 2/3: Audiveris распознаёт (может занять минуту)...")
            try:
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

new_block = """            # 2. Распознавание: PDF -> Audiveris -> homr; картинка -> homr -> PDF -> Audiveris
            _ext = os.path.splitext(path)[1].lower()
            mxl = None
            e_aud = None
            e_homr = None
            e_homr_img = None
            e_conv = None

            if _ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"):
                self.sig_status.emit("Картинка — распознаю через homr...")
                try:
                    mxl = run_homr_image(path)
                except Exception as e_img:
                    e_homr_img = e_img
                    print("[homr-img] ошибка:", e_img, flush=True)

                if (not mxl) or (not os.path.exists(mxl)):
                    self.sig_status.emit("homr не справился — конвертирую в PDF и пробую Audiveris...")
                    pdf_tmp = None
                    try:
                        pdf_tmp = _image_to_pdf(path)
                        try:
                            mxl = run_audiveris(pdf_tmp)
                        except Exception as e_a:
                            e_aud = e_a
                            print("[audiveris] ошибка:", e_a, flush=True)
                        if (not mxl) or (not os.path.exists(mxl)):
                            try:
                                mxl = run_homr(pdf_tmp)
                            except Exception as e_h:
                                e_homr = e_h
                                print("[homr-pdf] ошибка:", e_h, flush=True)
                    except Exception as e_c:
                        e_conv = e_c
                        print("[conv] ошибка конвертации:", e_c, flush=True)
                    finally:
                        if pdf_tmp and os.path.isfile(pdf_tmp):
                            try:
                                os.remove(pdf_tmp)
                            except OSError:
                                pass

                if (not mxl) or (not os.path.exists(mxl)):
                    msg = ("Не удалось распознать картинку.\\n"
                           "homr(img): " + str(e_homr_img) + "\\n"
                           "conv: " + str(e_conv) + "\\n"
                           "Audiveris: " + str(e_aud) + "\\n"
                           "homr(pdf): " + str(e_homr))
                    print("[omr-img]", msg, flush=True)
                    if gen != self._load_gen:
                        return
                    self.sig_load_done.emit(None, MANUAL_BPM, msg)
                    return
            else:
                self.sig_status.emit("Шаг 2/3: Audiveris распознаёт (может занять минуту)...")
                try:
                    mxl = run_audiveris(path)
                except Exception as e:
                    e_aud = e
                    print("[audiveris] ошибка:", e, flush=True)

                if (not mxl) or (not os.path.exists(mxl)):
                    self.sig_status.emit("Audiveris не справился — пробую homr...")
                    try:
                        mxl = run_homr(path)
                    except Exception as e_h:
                        e_homr = e_h
                        print("[homr] ошибка:", e_h, flush=True)

                if (not mxl) or (not os.path.exists(mxl)):
                    msg = ("Ни Audiveris, ни homr не смогли распознать ноты.\\n"
                           "Audiveris: " + str(e_aud) + "\\n"
                           "homr: " + str(e_homr))
                    print("[omr]", msg, flush=True)
                    if gen != self._load_gen:
                        return
                    self.sig_load_done.emit(None, MANUAL_BPM, msg)
                    return"""

if old_block in src:
    src = src.replace(old_block, new_block, 1)
    print("[piano_qt] recognition block patched")
else:
    print("[piano_qt] WARNING: old block not found")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
