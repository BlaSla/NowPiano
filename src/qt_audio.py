# -*- coding: utf-8 -*-
"""qt_audio.py - аудио, MusicXML, Audiveris. Без UI."""

import os
import sys
import sys as _sys
if getattr(_sys, "frozen", False):
    if _sys.stdout is None:
        _sys.stdout = open(os.devnull, "w")
    if _sys.stderr is None:
        _sys.stderr = open(os.devnull, "w")
import time
import threading
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional
# --- Добавляем DLL-директорию FluidSynth (рядом с exe или в проекте) ---
_here = os.path.dirname(os.path.abspath(__file__))
_proj = os.path.abspath(os.path.join(_here, os.pardir))
_fs_cands = []
if getattr(_sys, "frozen", False):
    _exe_dir = os.path.dirname(_sys.executable)
    _fs_cands += [
        os.path.join(_exe_dir, "_internal", "tools", "fluidsynth", "bin"),
        os.path.join(_exe_dir, "tools", "fluidsynth", "bin"),
        os.path.join(_exe_dir, "tools", "fluidsynth"),
        os.path.join(_exe_dir, "fluidsynth"),
    ]
else:
    _fs_cands += [
        os.path.join(_proj, "tools", "fluidsynth", "bin"),
        os.path.join(_proj, "tools", "fluidsynth"),
    ]
for _cand in _fs_cands:
    if os.path.exists(_cand):
        try:
            os.add_dll_directory(_cand)
        except Exception:
            pass
        os.environ["PATH"] = _cand + os.pathsep + os.environ.get("PATH", "")
        print("[audio] FluidSynth DLL dir:", _cand, flush=True)
        break

try:
    import fluidsynth
    FLUID_IMPORT_OK = True
    print("[audio] pyfluidsynth OK", flush=True)
except Exception as _e:
    FLUID_IMPORT_OK = False
    print("[audio] pyfluidsynth FAILED:", repr(_e), flush=True)

try:
    # --- Повторный фикс: fluidsynth мог сбросить sys.stdout ---
    if getattr(_sys, "frozen", False):
        if _sys.stdout is None:
            _sys.stdout = open(os.devnull, "w")
        if _sys.stderr is None:
            _sys.stderr = open(os.devnull, "w")
    from music21 import converter
    MUSIC21_OK = True
except Exception as _e:
    MUSIC21_OK = False
    print("[audio] music21 FAILED:", repr(_e), flush=True)
    import traceback
    traceback.print_exc()


# ---------- Настройки ----------
def _find_soundfont():
    import sys as _sys
    candidates = []
    name = "Arachno_SoundFont_Version_1.0.sf2"
    alt  = "FluidR3_GM.sf2"
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    # 1. {проект}/soundfonts/ (dev)
    candidates.append(os.path.join(proj, "soundfonts", name))
    candidates.append(os.path.join(proj, "soundfonts", alt))
    # 2. Рядом с .exe (для установленной версии)
    if getattr(_sys, "frozen", False):
        exe_dir = os.path.dirname(_sys.executable)
        candidates.append(os.path.join(exe_dir, "soundfonts", name))
        candidates.append(os.path.join(exe_dir, "soundfonts", alt))
        candidates.append(os.path.join(exe_dir, "_internal", "soundfonts", name))
        candidates.append(os.path.join(exe_dir, "SoundFonts", name))
        candidates.append(os.path.join(exe_dir, name))
    # 3. Пользовательские места (fallback)
    candidates.append(r"C:\tools\fluidsynth\soundfonts\Arachno_SoundFont_Version_1.0.sf2")
    candidates.append(os.path.join(os.path.expanduser("~"),
                                   ".aldakit", "soundfonts", name))
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

SOUNDFONT_PATH = _find_soundfont()
FLUID_DRIVER = "waveout"
# На разных сборках FluidSynth Windows поддерживаются разные драйверы.
FLUID_DRIVERS = ("waveout", "dsound", "winmm", "wasapi")
FLUID_GAIN = 0.8
NOTE_TAIL = 1.35
RIGHT_VEL = 100
LEFT_VEL = 70

def _find_audiveris():
    """Ищет Audiveris рядом с exe, в проекте или в стандартных путях."""
    import sys as _sys
    candidates = []
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    # 1. {проект}/tools/audiveris/Audiveris.exe (dev)
    candidates.append(os.path.join(proj, "tools", "audiveris", "Audiveris.exe"))
    # 2. Рядом с .exe (для установленной версии)
    if getattr(_sys, "frozen", False):
        exe_dir = os.path.dirname(_sys.executable)
        candidates.append(os.path.join(exe_dir, "tools", "audiveris", "Audiveris.exe"))
        candidates.append(os.path.join(exe_dir, "audiveris", "Audiveris.exe"))
        candidates.append(os.path.join(exe_dir, "_internal", "tools", "audiveris", "Audiveris.exe"))
    # 3. Пользовательские (fallback)
    candidates.append(r"C:\Program Files\Audiveris\Audiveris.exe")
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[-1]


AUDIVERIS_EXE = _find_audiveris()

# ---------- homr (fallback OMR) ----------
def _find_homr():
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    candidates = [os.path.join(proj, "venv", "Scripts", "homr.exe")]
    if getattr(_sys, "frozen", False):
        exe_dir = os.path.dirname(_sys.executable)
        candidates.append(os.path.join(exe_dir, "homr.exe"))
        candidates.append(os.path.join(exe_dir, "_internal", "homr.exe"))
        candidates.append(os.path.join(exe_dir, "venv", "Scripts", "homr.exe"))
        candidates.append(os.path.join(exe_dir, "_internal", "venv", "Scripts", "homr.exe"))
        candidates.append(os.path.join(exe_dir, "venv", "Scripts", "homr"))
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


# Выход OMR должен быть доступен для записи даже при установке в Program Files.
if getattr(_sys, "frozen", False):
    _local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    OMR_OUTPUT_DIR = os.path.join(_local_appdata, "NowPiano", "out_omr")
else:
    OMR_OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "out_omr"))
MANUAL_BPM = 72.0

START_NOTE = 21
NUM_KEYS = 88


@dataclass
class NoteEvent:
    """Одно событие: нота или аккорд в момент времени."""
    bar: int
    offset_q: float
    time_seconds: float
    notes: List[int]
    duration: float
    hand: str = "R"   # R - прав, L - лев
    part: int = 0


class AudioEngine:
    """Обёртка над FluidSynth: play/stop нот, громкость."""

    def __init__(self):
        self.fs = None
        self.sfid = None
        self.available = False
        self.active_notes = set()
        self._lock = threading.Lock()

    def init(self) -> bool:
        if not FLUID_IMPORT_OK:
            print("[audio] pyfluidsynth не установлен")
            return False
        if not os.path.exists(SOUNDFONT_PATH):
            print("[audio] SoundFont не найден:", SOUNDFONT_PATH)
            return False
        last_error = None
        for driver in FLUID_DRIVERS:
            synth = None
            try:
                synth = fluidsynth.Synth(gain=FLUID_GAIN)
                # Передаём драйвер явно в start(): настройка после создания
                # Synth не всегда применяется одинаково в Windows-сборках.
                synth.start(driver=driver)
                sfid = synth.sfload(SOUNDFONT_PATH)
                if sfid is None or int(sfid) < 0:
                    raise RuntimeError(f"SoundFont не загрузился: {SOUNDFONT_PATH} (sfid={sfid})")
                synth.program_select(0, int(sfid), 0, 0)
                self.fs = synth
                self.sfid = int(sfid)
                self.available = True
                print(f"[audio] FluidSynth ready: driver={driver}, SoundFont={SOUNDFONT_PATH}", flush=True)
                return True
            except Exception as e:
                last_error = e
                print(f"[audio] драйвер {driver} не запустился: {e}", flush=True)
                if synth is not None:
                    try:
                        synth.delete()
                    except Exception:
                        pass
        self.available = False
        print("[audio] FluidSynth failed on all drivers:", repr(last_error), flush=True)
        return False

    def note_on(self, midi: int, velocity: int = 100):
        if not self.available:
            return
        with self._lock:
            try:
                self.fs.noteon(0, midi, velocity)
                self.active_notes.add(midi)
            except Exception as e:
                print("[audio] note_on error:", e)

    def note_off(self, midi: int):
        if not self.available:
            return
        with self._lock:
            try:
                self.fs.noteoff(0, midi)
            except Exception:
                pass
            self.active_notes.discard(midi)

    def note_off_later(self, midi: int, delay: float):
        def _off():
            time.sleep(delay)
            self.note_off(midi)
        threading.Thread(target=_off, daemon=True).start()

    def all_off(self):
        if not self.available:
            return
        with self._lock:
            for n in list(self.active_notes):
                try:
                    self.fs.noteoff(0, n)
                except Exception:
                    pass
            self.active_notes.clear()

    def shutdown(self):
        self.all_off()
        if self.fs is not None:
            try:
                self.fs.delete()
            except Exception:
                pass
            self.fs = None
            self.available = False


# ---------- Audiveris ----------
def run_audiveris(pdf_path: str) -> str:
    """Запускает Audiveris и возвращает созданный MusicXML/MXL.

    Не использует разделитель '--': в некоторых сборках Audiveris он приводит
    к неверному разбору пути к PDF. При ошибке возвращает текст stdout/stderr.
    """
    if not os.path.isfile(pdf_path):
        raise RuntimeError(f"PDF-файл не найден: {pdf_path}")
    if not os.path.isfile(AUDIVERIS_EXE):
        raise RuntimeError(f"Audiveris не найден: {AUDIVERIS_EXE}")

    os.makedirs(OMR_OUTPUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]

    # Старые результаты нельзя автоматически принимать за результат текущего запуска.
    for ext in (".mxl", ".xml", ".musicxml"):
        old = os.path.join(OMR_OUTPUT_DIR, base + ext)
        if os.path.isfile(old):
            try:
                os.remove(old)
            except OSError:
                pass

    cmd = [
        AUDIVERIS_EXE, "-batch", "-transcribe", "-export",
        "-output", OMR_OUTPUT_DIR, pdf_path
    ]
    env = os.environ.copy()
    java_home = None
    if getattr(_sys, "frozen", False):
        exe_dir = os.path.dirname(_sys.executable)
        for jh in (os.path.join(exe_dir, "tools", "java"),
                   os.path.join(exe_dir, "java")):
            if os.path.isfile(os.path.join(jh, "bin", "java.exe")):
                java_home = jh
                break
    if java_home:
        env["JAVA_HOME"] = java_home
        env["PATH"] = os.path.join(java_home, "bin") + os.pathsep + env.get("PATH", "")

    try:
        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=900, env=env,
            cwd=os.path.dirname(AUDIVERIS_EXE) or None
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Audiveris не завершил распознавание за 15 минут.") from exc
    except OSError as exc:
        raise RuntimeError(f"Не удалось запустить Audiveris: {exc}") from exc

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "Audiveris не вывел подробностей ошибки").strip()
        details = details[-5000:]
        raise RuntimeError(
            f"Audiveris завершился с кодом {result.returncode}.\n"
            f"Команда: {subprocess.list2cmdline(cmd)}\n"
            f"Вывод Audiveris:\n{details}"
        )

    for ext in (".mxl", ".xml", ".musicxml"):
        candidate = os.path.join(OMR_OUTPUT_DIR, base + ext)
        if os.path.isfile(candidate):
            return candidate

    for filename in os.listdir(OMR_OUTPUT_DIR):
        if filename.startswith(base) and filename.lower().endswith((".mxl", ".xml", ".musicxml")):
            return os.path.join(OMR_OUTPUT_DIR, filename)

    details = (result.stdout or result.stderr or "").strip()[-3000:]
    raise RuntimeError(
        f"Audiveris завершился без ошибки, но не создал MusicXML в {OMR_OUTPUT_DIR}.\n{details}"
    )

# ---------- homr для картинок ----------
def run_homr(pdf_path):
    """Fallback: конвертирует PDF в PNG (первая страница) и запускает homr."""
    if not os.path.isfile(pdf_path):
        raise RuntimeError("PDF-файл не найден: " + pdf_path)
    # homr запускается через sys.executable -m homr, отдельный exe не нужен
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
            "homr завершился с кодом " + str(result.returncode) + ".\n"
            "Команда: " + subprocess.list2cmdline([HOMR_EXE, png_path]) + "\n"
            "Вывод homr:\n" + details
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


def _image_to_pdf(img_path):
    """Конвертирует картинку в PDF (для fallback на Audiveris)."""
    from PIL import Image
    pdf_path = os.path.splitext(img_path)[0] + ".__conv.pdf"
    img = Image.open(img_path).convert("RGB")
    img.save(pdf_path, "PDF", resolution=300.0)
    return pdf_path


def run_homr_image(image_path):
    """homr для картинки (PNG/JPG) — без конвертации PDF."""
    if not os.path.isfile(image_path):
        raise RuntimeError("Картинка не найдена: " + image_path)
    # homr запускается через sys.executable -m homr, отдельный exe не нужен

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
            "homr завершился с кодом " + str(result.returncode) + ".\n"
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


# ---------- MusicXML -> события ----------
def musicxml_to_events(mxl_path: str):
    """Парсит MusicXML, возвращает (events, bpm, n_parts)."""
    if not MUSIC21_OK:
        raise RuntimeError("music21 не установлен")

    score = converter.parse(mxl_path)
    bpm = MANUAL_BPM
    marks = score.metronomeMarkBoundaries()
    if marks:
        try:
            bpm = float(marks[0][2].number)
        except Exception:
            pass
    if bpm > 110 and abs(bpm - MANUAL_BPM) > 20:
        bpm = MANUAL_BPM

    spq = 60.0 / bpm
    used_parts = [p for p in score.parts if len(list(p.flatten().notes)) > 0]
    if not used_parts:
        raise RuntimeError("В партитуре нет нот")

    events = []
    for part_idx, part in enumerate(used_parts):
        hand = "R" if part_idx == 0 else "L"
        for el in part.flatten().notesAndRests:
            dur_q = float(el.quarterLength)
            if dur_q <= 0:
                continue
            offset_q = float(el.offset)
            try:
                bar = int(el.measureNumber) if el.measureNumber else 0
            except Exception:
                bar = 0
            if hasattr(el, "pitches") and len(el.pitches) > 0:
                midis = sorted(p.midi for p in el.pitches)
                midis = [m for m in midis if START_NOTE <= m <= START_NOTE + NUM_KEYS - 1]
                if midis:
                    events.append(NoteEvent(
                        bar=bar,
                        offset_q=offset_q,
                        time_seconds=offset_q * spq,
                        notes=midis,
                        duration=max(0.05, dur_q * spq),
                        hand=hand,
                    ))

    events.sort(key=lambda e: e.time_seconds)

    # Склейка одновременных событий (правая + левая)
    merged: List[NoteEvent] = []
    for ev in events:
        if merged:
            last = merged[-1]
            if abs(ev.time_seconds - last.time_seconds) < 0.02:
                last.notes = sorted(set(last.notes) | set(ev.notes))
                last.duration = max(last.duration, ev.duration)
                continue
        merged.append(NoteEvent(
            bar=ev.bar, offset_q=ev.offset_q,
            time_seconds=ev.time_seconds, notes=list(ev.notes),
            duration=ev.duration, hand=ev.hand,
        ))

    # Нормируем время так, чтобы первая нота была в 0
    if merged:
        t0 = merged[0].time_seconds
        o0 = merged[0].offset_q
        if t0 > 0.05:
            for ev in merged:
                ev.time_seconds -= t0
                ev.offset_q -= o0

    print(f"[audio] MusicXML parsed: {len(merged)} events, BPM={bpm:.1f}")
    return merged, bpm, len(used_parts)


def total_duration(events: List[NoteEvent]) -> float:
    if not events:
        return 0.0
    last = events[-1]
    return float(last.time_seconds) + float(last.duration)


# ---------- Тест модуля ----------
# ---------- Экспорт в MIDI ----------
def export_midi(mxl_path: str, out_path: str) -> bool:
    """Конвертирует MusicXML/MXL в MIDI через music21.
    Возвращает True при успехе."""
    if not MUSIC21_OK:
        print("[midi] music21 недоступен")
        return False
    try:
        score = converter.parse(mxl_path)
        score.write("midi", fp=out_path)
        print(f"[midi] exported: {out_path}")
        return True
    except Exception as e:
        print("[midi] export error:", e)
        return False


def _clamp_octave(midi: int) -> int:
    """Сдвигает ноту октавами, пока она не попадёт в диапазон клавиатуры."""
    lo = START_NOTE
    hi = START_NOTE + NUM_KEYS - 1
    while midi < lo:
        midi += 12
    while midi > hi:
        midi -= 12
    return midi


def load_midi_events(midi_path: str):
    """Читает MIDI и возвращает (events, bpm). events — список NoteEvent.
    Учитывает каналы: ch0 -> R, ch1 -> L, остальные — по высоте.
    BPM: из метронома, иначе 120 (стандарт MIDI)."""
    if not MUSIC21_OK:
        raise RuntimeError("music21 недоступен")
    score = converter.parse(midi_path)

    bpm = 120.0
    marks = score.metronomeMarkBoundaries()
    if marks:
        try:
            bpm = float(marks[0][2].number)
        except Exception:
            pass
    if not (20 < bpm < 400):
        bpm = 120.0

    spq = 60.0 / bpm
    events = []

    # music21 может разложить MIDI на партии по каналам
    parts = list(score.parts) if score.parts else [score]
    if len(parts) == 1:
        # Один поток — разделим по высоте
        for el in parts[0].flatten().notes:
            dur_q = float(el.quarterLength)
            if dur_q <= 0:
                continue
            offset_q = float(el.offset)
            bar = 0
            try:
                bar = int(el.measureNumber) if el.measureNumber else 0
            except Exception:
                bar = 0
            if hasattr(el, "pitches") and len(el.pitches) > 0:
                midis = sorted(_clamp_octave(p.midi) for p in el.pitches)
                midis = [m for m in midis if START_NOTE <= m <= START_NOTE + NUM_KEYS - 1]
                if midis:
                    hand = "R" if (midis[0] >= 60) else "L"
                    events.append(NoteEvent(
                        bar=bar, offset_q=offset_q,
                        time_seconds=offset_q * spq,
                        notes=midis,
                        duration=max(0.05, dur_q * spq),
                        hand=hand,
                    ))
    else:
        # Много партий — первая R, вторая L (или по каналу)
        for p_idx, part in enumerate(parts):
            hand = "R"  # временно, уточним по высоте ниже
            for el in part.flatten().notes:
                dur_q = float(el.quarterLength)
                if dur_q <= 0:
                    continue
                offset_q = float(el.offset)
                bar = 0
                try:
                    bar = int(el.measureNumber) if el.measureNumber else 0
                except Exception:
                    bar = 0
                if hasattr(el, "pitches") and len(el.pitches) > 0:
                    midis = sorted(_clamp_octave(p.midi) for p in el.pitches)
                    midis = [m for m in midis if START_NOTE <= m <= START_NOTE + NUM_KEYS - 1]
                    if midis:
                        _avg = sum(midis) / len(midis)
                        _hand = "R" if _avg >= 60 else "L"
                        events.append(NoteEvent(
                            bar=bar, offset_q=offset_q,
                            time_seconds=offset_q * spq,
                            notes=midis,
                            duration=max(0.05, dur_q * spq),
                            hand=_hand,
                            part=p_idx,
                        ))

    events.sort(key=lambda e: e.time_seconds)
    if events:
        t0 = events[0].time_seconds
        if t0 > 0.05:
            for ev in events:
                ev.time_seconds -= t0
    print(f"[midi] parsed: {len(events)} events, BPM={bpm:.1f}, parts={len(parts)}")
    return events, bpm

if __name__ == "__main__":
    print("=== qt_audio self-test ===")
    print("fluidsynth import:", FLUID_IMPORT_OK)
    print("music21 import:", MUSIC21_OK)
    print("SoundFont exists:", os.path.exists(SOUNDFONT_PATH))
    print("Audiveris exists:", os.path.exists(AUDIVERIS_EXE))

    engine = AudioEngine()
    if engine.init():
        print("Играю гамму до-мажор...")
        notes = [60, 62, 64, 65, 67, 69, 71, 72]
        for i, n in enumerate(notes):
            engine.note_on(n, 100)
            engine.note_off_later(n, 0.4)
            time.sleep(0.3)
        time.sleep(1.0)
        engine.shutdown()
        print("Готово.")
    else:
        print("AudioEngine не запустился.")


# ---------- Рендер MIDI/MusicXML в PNG через MuseScore ----------
def render_score_to_pngs(source_path: str, out_dir: str = None, max_pages: int = 10):
    """Рендерит MIDI или MusicXML в PNG через music21 + MuseScore.
    Возвращает список путей к PNG (по одной на страницу)."""
    if not MUSIC21_OK:
        print("[render] music21 недоступен")
        return []
    import glob
    if out_dir is None:
        out_dir = os.path.dirname(os.path.abspath(source_path))
    base = os.path.splitext(os.path.basename(source_path))[0]
    out_prefix = os.path.join(out_dir, base + "_render")

    for old in glob.glob(out_prefix + "*.png"):
        try:
            os.remove(old)
        except Exception:
            pass

    try:
        score = converter.parse(source_path)
        score.write("musicxml.png", fp=out_prefix + ".png")
    except Exception as e:
        print("[render] error:", e)
        return []

    pages = []
    for i in range(1, max_pages + 1):
        candidate = f"{out_prefix}-{i}.png"
        if os.path.exists(candidate):
            pages.append(candidate)
    if not pages:
        if os.path.exists(out_prefix + ".png"):
            pages.append(out_prefix + ".png")

    print(f"[render] PNG pages: {len(pages)}")
    return pages
