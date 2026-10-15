# -*- coding: utf-8 -*-
# --- Fix stdout/stderr encoding on Windows ---
try:
    import sys as _sys_enc
    if _sys_enc.stdout is not None and hasattr(_sys_enc.stdout, "reconfigure"):
        _sys_enc.stdout.reconfigure(encoding="utf-8", errors="replace")
    if _sys_enc.stderr is not None and hasattr(_sys_enc.stderr, "reconfigure"):
        _sys_enc.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
"""qt_audio.py - Р В°РЎС“Р Т‘Р С‘Р С•, MusicXML, Audiveris. Р вЂР ВµР В· UI."""

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
# --- Р вЂќР С•Р В±Р В°Р Р†Р В»РЎРЏР ВµР С DLL-Р Т‘Р С‘РЎР‚Р ВµР С”РЎвЂљР С•РЎР‚Р С‘РЎР‹ FluidSynth (РЎР‚РЎРЏР Т‘Р С•Р С РЎРѓ exe Р С‘Р В»Р С‘ Р Р† Р С—РЎР‚Р С•Р ВµР С”РЎвЂљР Вµ) ---
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
    # --- Р СџР С•Р Р†РЎвЂљР С•РЎР‚Р Р…РЎвЂ№Р в„– РЎвЂћР С‘Р С”РЎРѓ: fluidsynth Р СР С•Р С– РЎРѓР В±РЎР‚Р С•РЎРѓР С‘РЎвЂљРЎРЉ sys.stdout ---
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


# ---------- Р СњР В°РЎРѓРЎвЂљРЎР‚Р С•Р в„–Р С”Р С‘ ----------
def _find_soundfont():
    import sys as _sys
    candidates = []
    name = "Arachno_SoundFont_Version_1.0.sf2"
    alt  = "FluidR3_GM.sf2"
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    # 1. {Р С—РЎР‚Р С•Р ВµР С”РЎвЂљ}/soundfonts/ (dev)
    candidates.append(os.path.join(proj, "soundfonts", name))
    candidates.append(os.path.join(proj, "soundfonts", alt))
    # 2. Р В РЎРЏР Т‘Р С•Р С РЎРѓ .exe (Р Т‘Р В»РЎРЏ РЎС“РЎРѓРЎвЂљР В°Р Р…Р С•Р Р†Р В»Р ВµР Р…Р Р…Р С•Р в„– Р Р†Р ВµРЎР‚РЎРѓР С‘Р С‘)
    if getattr(_sys, "frozen", False):
        exe_dir = os.path.dirname(_sys.executable)
        candidates.append(os.path.join(exe_dir, "soundfonts", name))
        candidates.append(os.path.join(exe_dir, "soundfonts", alt))
        candidates.append(os.path.join(exe_dir, "_internal", "soundfonts", name))
        candidates.append(os.path.join(exe_dir, "SoundFonts", name))
        candidates.append(os.path.join(exe_dir, name))
    # 3. Р СџР С•Р В»РЎРЉР В·Р С•Р Р†Р В°РЎвЂљР ВµР В»РЎРЉРЎРѓР С”Р С‘Р Вµ Р СР ВµРЎРѓРЎвЂљР В° (fallback)
    candidates.append(r"C:\tools\fluidsynth\soundfonts\Arachno_SoundFont_Version_1.0.sf2")
    candidates.append(os.path.join(os.path.expanduser("~"),
                                   ".aldakit", "soundfonts", name))
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

SOUNDFONT_PATH = _find_soundfont()
FLUID_DRIVER = "waveout"
# Р СњР В° РЎР‚Р В°Р В·Р Р…РЎвЂ№РЎвЂ¦ РЎРѓР В±Р С•РЎР‚Р С”Р В°РЎвЂ¦ FluidSynth Windows Р С—Р С•Р Т‘Р Т‘Р ВµРЎР‚Р В¶Р С‘Р Р†Р В°РЎР‹РЎвЂљРЎРѓРЎРЏ РЎР‚Р В°Р В·Р Р…РЎвЂ№Р Вµ Р Т‘РЎР‚Р В°Р в„–Р Р†Р ВµРЎР‚РЎвЂ№.
FLUID_DRIVERS = ("waveout", "dsound", "winmm", "wasapi")
FLUID_GAIN = 0.8
NOTE_TAIL = 1.35
RIGHT_VEL = 100
LEFT_VEL = 70

def _find_audiveris():
    """Р ВРЎвЂ°Р ВµРЎвЂљ Audiveris РЎР‚РЎРЏР Т‘Р С•Р С РЎРѓ exe, Р Р† Р С—РЎР‚Р С•Р ВµР С”РЎвЂљР Вµ Р С‘Р В»Р С‘ Р Р† РЎРѓРЎвЂљР В°Р Р…Р Т‘Р В°РЎР‚РЎвЂљР Р…РЎвЂ№РЎвЂ¦ Р С—РЎС“РЎвЂљРЎРЏРЎвЂ¦."""
    import sys as _sys
    candidates = []
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    # 1. {Р С—РЎР‚Р С•Р ВµР С”РЎвЂљ}/tools/audiveris/Audiveris.exe (dev)
    candidates.append(os.path.join(proj, "tools", "audiveris", "Audiveris.exe"))
    # 2. Р В РЎРЏР Т‘Р С•Р С РЎРѓ .exe (Р Т‘Р В»РЎРЏ РЎС“РЎРѓРЎвЂљР В°Р Р…Р С•Р Р†Р В»Р ВµР Р…Р Р…Р С•Р в„– Р Р†Р ВµРЎР‚РЎРѓР С‘Р С‘)
    if getattr(_sys, "frozen", False):
        exe_dir = os.path.dirname(_sys.executable)
        candidates.append(os.path.join(exe_dir, "tools", "audiveris", "Audiveris.exe"))
        candidates.append(os.path.join(exe_dir, "audiveris", "Audiveris.exe"))
        candidates.append(os.path.join(exe_dir, "_internal", "tools", "audiveris", "Audiveris.exe"))
    # 3. Р СџР С•Р В»РЎРЉР В·Р С•Р Р†Р В°РЎвЂљР ВµР В»РЎРЉРЎРѓР С”Р С‘Р Вµ (fallback)
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
        candidates += [
            os.path.join(exe_dir, "homr", "homr.exe"),
            os.path.join(exe_dir, "_internal", "homr", "homr.exe"),
            os.path.join(exe_dir, "tools", "homr", "homr.exe"),
            os.path.join(exe_dir, "_internal", "tools", "homr", "homr.exe"),
        ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None

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

def _find_homr_python():
    """Путь к python.exe для homr."""
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    candidates = []
    if getattr(_sys, "frozen", False):
        exe_dir = os.path.dirname(_sys.executable)
        candidates += [
            os.path.join(exe_dir, "tools", "python", "python.exe"),
            os.path.join(exe_dir, "_internal", "tools", "python", "python.exe"),
        ]
    candidates.append(os.path.join(proj, "venv", "Scripts", "python.exe"))
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _homr_env():
    """env с PYTHONPATH для homr."""
    env = os.environ.copy()
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    if getattr(_sys, "frozen", False):
        exe_dir = os.path.dirname(_sys.executable)
        sp = os.path.join(exe_dir, "tools", "python", "Lib", "site-packages")
        internal = os.path.join(exe_dir, "_internal")
    else:
        sp = os.path.join(proj, "venv", "Lib", "site-packages")
        internal = os.path.join(proj, "src")
    paths = []
    if os.path.isdir(sp): paths.append(sp)
    if os.path.isdir(internal): paths.append(internal)
    if paths:
        env["PYTHONPATH"] = os.pathsep.join(paths) + os.pathsep + env.get("PYTHONPATH", "")
    return env

HOMR_PY = _find_homr_python()
HOMR_EXE = HOMR_PY  # backward compat
PDFTOPPM_EXE = _find_pdftoppm()


# Р вЂ™РЎвЂ№РЎвЂ¦Р С•Р Т‘ OMR Р Т‘Р С•Р В»Р В¶Р ВµР Р… Р В±РЎвЂ№РЎвЂљРЎРЉ Р Т‘Р С•РЎРѓРЎвЂљРЎС“Р С—Р ВµР Р… Р Т‘Р В»РЎРЏ Р В·Р В°Р С—Р С‘РЎРѓР С‘ Р Т‘Р В°Р В¶Р Вµ Р С—РЎР‚Р С‘ РЎС“РЎРѓРЎвЂљР В°Р Р…Р С•Р Р†Р С”Р Вµ Р Р† Program Files.
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
    """Р С›Р Т‘Р Р…Р С• РЎРѓР С•Р В±РЎвЂ№РЎвЂљР С‘Р Вµ: Р Р…Р С•РЎвЂљР В° Р С‘Р В»Р С‘ Р В°Р С”Р С”Р С•РЎР‚Р Т‘ Р Р† Р СР С•Р СР ВµР Р…РЎвЂљ Р Р†РЎР‚Р ВµР СР ВµР Р…Р С‘."""
    bar: int
    offset_q: float
    time_seconds: float
    notes: List[int]
    duration: float
    hand: str = "R"   # R - Р С—РЎР‚Р В°Р Р†, L - Р В»Р ВµР Р†
    part: int = 0
    note_names: dict = field(default_factory=dict)


class AudioEngine:
    """Р С›Р В±РЎвЂРЎР‚РЎвЂљР С”Р В° Р Р…Р В°Р Т‘ FluidSynth: play/stop Р Р…Р С•РЎвЂљ, Р С–РЎР‚Р С•Р СР С”Р С•РЎРѓРЎвЂљРЎРЉ."""

    def __init__(self):
        self.fs = None
        self.sfid = None
        self.available = False
        self.active_notes = set()
        self._lock = threading.Lock()

    def init(self) -> bool:
        if not FLUID_IMPORT_OK:
            print("[audio] pyfluidsynth Р Р…Р Вµ РЎС“РЎРѓРЎвЂљР В°Р Р…Р С•Р Р†Р В»Р ВµР Р…")
            return False
        if not os.path.exists(SOUNDFONT_PATH):
            print("[audio] SoundFont Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…:", SOUNDFONT_PATH)
            return False
        last_error = None
        for driver in FLUID_DRIVERS:
            synth = None
            try:
                synth = fluidsynth.Synth(gain=FLUID_GAIN)
                # Р СџР ВµРЎР‚Р ВµР Т‘Р В°РЎвЂР С Р Т‘РЎР‚Р В°Р в„–Р Р†Р ВµРЎР‚ РЎРЏР Р†Р Р…Р С• Р Р† start(): Р Р…Р В°РЎРѓРЎвЂљРЎР‚Р С•Р в„–Р С”Р В° Р С—Р С•РЎРѓР В»Р Вµ РЎРѓР С•Р В·Р Т‘Р В°Р Р…Р С‘РЎРЏ
                # Synth Р Р…Р Вµ Р Р†РЎРѓР ВµР С–Р Т‘Р В° Р С—РЎР‚Р С‘Р СР ВµР Р…РЎРЏР ВµРЎвЂљРЎРѓРЎРЏ Р С•Р Т‘Р С‘Р Р…Р В°Р С”Р С•Р Р†Р С• Р Р† Windows-РЎРѓР В±Р С•РЎР‚Р С”Р В°РЎвЂ¦.
                synth.start(driver=driver)
                sfid = synth.sfload(SOUNDFONT_PATH)
                if sfid is None or int(sfid) < 0:
                    raise RuntimeError(f"SoundFont Р Р…Р Вµ Р В·Р В°Р С–РЎР‚РЎС“Р В·Р С‘Р В»РЎРѓРЎРЏ: {SOUNDFONT_PATH} (sfid={sfid})")
                synth.program_select(0, int(sfid), 0, 0)
                self.fs = synth
                self.sfid = int(sfid)
                self.available = True
                print(f"[audio] FluidSynth ready: driver={driver}, SoundFont={SOUNDFONT_PATH}", flush=True)
                return True
            except Exception as e:
                last_error = e
                print(f"[audio] Р Т‘РЎР‚Р В°Р в„–Р Р†Р ВµРЎР‚ {driver} Р Р…Р Вµ Р В·Р В°Р С—РЎС“РЎРѓРЎвЂљР С‘Р В»РЎРѓРЎРЏ: {e}", flush=True)
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
    """Р вЂ”Р В°Р С—РЎС“РЎРѓР С”Р В°Р ВµРЎвЂљ Audiveris Р С‘ Р Р†Р С•Р В·Р Р†РЎР‚Р В°РЎвЂ°Р В°Р ВµРЎвЂљ РЎРѓР С•Р В·Р Т‘Р В°Р Р…Р Р…РЎвЂ№Р в„– MusicXML/MXL.

    Р СњР Вµ Р С‘РЎРѓР С—Р С•Р В»РЎРЉР В·РЎС“Р ВµРЎвЂљ РЎР‚Р В°Р В·Р Т‘Р ВµР В»Р С‘РЎвЂљР ВµР В»РЎРЉ '--': Р Р† Р Р…Р ВµР С”Р С•РЎвЂљР С•РЎР‚РЎвЂ№РЎвЂ¦ РЎРѓР В±Р С•РЎР‚Р С”Р В°РЎвЂ¦ Audiveris Р С•Р Р… Р С—РЎР‚Р С‘Р Р†Р С•Р Т‘Р С‘РЎвЂљ
    Р С” Р Р…Р ВµР Р†Р ВµРЎР‚Р Р…Р С•Р СРЎС“ РЎР‚Р В°Р В·Р В±Р С•РЎР‚РЎС“ Р С—РЎС“РЎвЂљР С‘ Р С” PDF. Р СџРЎР‚Р С‘ Р С•РЎв‚¬Р С‘Р В±Р С”Р Вµ Р Р†Р С•Р В·Р Р†РЎР‚Р В°РЎвЂ°Р В°Р ВµРЎвЂљ РЎвЂљР ВµР С”РЎРѓРЎвЂљ stdout/stderr.
    """
    if not os.path.isfile(pdf_path):
        raise RuntimeError(f"PDF-РЎвЂћР В°Р в„–Р В» Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…: {pdf_path}")
    if not os.path.isfile(AUDIVERIS_EXE):
        raise RuntimeError(f"Audiveris Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…: {AUDIVERIS_EXE}")

    os.makedirs(OMR_OUTPUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]

    # Р РЋРЎвЂљР В°РЎР‚РЎвЂ№Р Вµ РЎР‚Р ВµР В·РЎС“Р В»РЎРЉРЎвЂљР В°РЎвЂљРЎвЂ№ Р Р…Р ВµР В»РЎРЉР В·РЎРЏ Р В°Р Р†РЎвЂљР С•Р СР В°РЎвЂљР С‘РЎвЂЎР ВµРЎРѓР С”Р С‘ Р С—РЎР‚Р С‘Р Р…Р С‘Р СР В°РЎвЂљРЎРЉ Р В·Р В° РЎР‚Р ВµР В·РЎС“Р В»РЎРЉРЎвЂљР В°РЎвЂљ РЎвЂљР ВµР С”РЎС“РЎвЂ°Р ВµР С–Р С• Р В·Р В°Р С—РЎС“РЎРѓР С”Р В°.
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
        for jh in (os.path.join(exe_dir, "tools", "audiveris", "runtime"),
                   os.path.join(exe_dir, "tools", "java"),
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
        raise RuntimeError("Audiveris Р Р…Р Вµ Р В·Р В°Р Р†Р ВµРЎР‚РЎв‚¬Р С‘Р В» РЎР‚Р В°РЎРѓР С—Р С•Р В·Р Р…Р В°Р Р†Р В°Р Р…Р С‘Р Вµ Р В·Р В° 15 Р СР С‘Р Р…РЎС“РЎвЂљ.") from exc
    except OSError as exc:
        raise RuntimeError(f"Р СњР Вµ РЎС“Р Т‘Р В°Р В»Р С•РЎРѓРЎРЉ Р В·Р В°Р С—РЎС“РЎРѓРЎвЂљР С‘РЎвЂљРЎРЉ Audiveris: {exc}") from exc

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "Audiveris Р Р…Р Вµ Р Р†РЎвЂ№Р Р†Р ВµР В» Р С—Р С•Р Т‘РЎР‚Р С•Р В±Р Р…Р С•РЎРѓРЎвЂљР ВµР в„– Р С•РЎв‚¬Р С‘Р В±Р С”Р С‘").strip()
        details = details[-5000:]
        raise RuntimeError(
            f"Audiveris Р В·Р В°Р Р†Р ВµРЎР‚РЎв‚¬Р С‘Р В»РЎРѓРЎРЏ РЎРѓ Р С”Р С•Р Т‘Р С•Р С {result.returncode}.\n"
            f"Р С™Р С•Р СР В°Р Р…Р Т‘Р В°: {subprocess.list2cmdline(cmd)}\n"
            f"Р вЂ™РЎвЂ№Р Р†Р С•Р Т‘ Audiveris:\n{details}"
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
        f"Audiveris Р В·Р В°Р Р†Р ВµРЎР‚РЎв‚¬Р С‘Р В»РЎРѓРЎРЏ Р В±Р ВµР В· Р С•РЎв‚¬Р С‘Р В±Р С”Р С‘, Р Р…Р С• Р Р…Р Вµ РЎРѓР С•Р В·Р Т‘Р В°Р В» MusicXML Р Р† {OMR_OUTPUT_DIR}.\n{details}"
    )

# ---------- homr Р Т‘Р В»РЎРЏ Р С”Р В°РЎР‚РЎвЂљР С‘Р Р…Р С•Р С” ----------
def run_homr(pdf_path):
    """Fallback: Р С”Р С•Р Р…Р Р†Р ВµРЎР‚РЎвЂљР С‘РЎР‚РЎС“Р ВµРЎвЂљ PDF Р Р† PNG (Р С—Р ВµРЎР‚Р Р†Р В°РЎРЏ РЎРѓРЎвЂљРЎР‚Р В°Р Р…Р С‘РЎвЂ Р В°) Р С‘ Р В·Р В°Р С—РЎС“РЎРѓР С”Р В°Р ВµРЎвЂљ homr."""
    if not os.path.isfile(pdf_path):
        raise RuntimeError("PDF-РЎвЂћР В°Р в„–Р В» Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…: " + pdf_path)
    # homr Р В·Р В°Р С—РЎС“РЎРѓР С”Р В°Р ВµРЎвЂљРЎРѓРЎРЏ РЎвЂЎР ВµРЎР‚Р ВµР В· sys.executable -m homr, Р С•РЎвЂљР Т‘Р ВµР В»РЎРЉР Р…РЎвЂ№Р в„– exe Р Р…Р Вµ Р Р…РЎС“Р В¶Р ВµР Р…
    if not PDFTOPPM_EXE or not os.path.isfile(PDFTOPPM_EXE):
        raise RuntimeError("pdftoppm.exe Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…: " + str(PDFTOPPM_EXE))

    os.makedirs(OMR_OUTPUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]

    import tempfile, shutil
    tmpdir = tempfile.mkdtemp(prefix="homr_")
    png_base = os.path.join(tmpdir, "page")

    print("[homr] Р С”Р С•Р Р…Р Р†Р ВµРЎР‚РЎвЂљР С‘РЎР‚РЎС“РЎР‹ PDF Р Р† PNG: " + pdf_path, flush=True)
    try:
        subprocess.run(
            [PDFTOPPM_EXE, "-png", "-r", "300", "-f", "1", "-l", "1",
             pdf_path, png_base],
            check=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("pdftoppm Р Р…Р Вµ Р В·Р В°Р Р†Р ВµРЎР‚РЎв‚¬Р С‘Р В» Р С”Р С•Р Р…Р Р†Р ВµРЎР‚РЎвЂљР В°РЎвЂ Р С‘РЎР‹ Р В·Р В° 3 Р СР С‘Р Р…РЎС“РЎвЂљРЎвЂ№.") from exc
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()[-2000:]
        raise RuntimeError("pdftoppm РЎС“Р С—Р В°Р В»: " + details) from exc
    except OSError as exc:
        raise RuntimeError("Р СњР Вµ РЎС“Р Т‘Р В°Р В»Р С•РЎРѓРЎРЉ Р В·Р В°Р С—РЎС“РЎРѓРЎвЂљР С‘РЎвЂљРЎРЉ pdftoppm: " + str(exc)) from exc

    png_path = None
    for f in sorted(os.listdir(tmpdir)):
        if f.lower().endswith(".png"):
            png_path = os.path.join(tmpdir, f)
            break
    if not png_path:
        raise RuntimeError("pdftoppm Р Р…Р Вµ РЎРѓР С•Р В·Р Т‘Р В°Р В» PNG.")

    env = _homr_env()
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    venv_scripts = os.path.join(proj, "venv", "Scripts")
    if os.path.isdir(venv_scripts):
        env["PATH"] = venv_scripts + os.pathsep + env.get("PATH", "")

    print("[homr] Р В·Р В°Р С—РЎС“РЎРѓР С”Р В°РЎР‹: " + HOMR_EXE + " " + png_path, flush=True)
    try:
        result = subprocess.run(
            [HOMR_PY, "-m", "homr.main", png_path],
            check=False, text=True,
            encoding="utf-8", errors="replace", timeout=900, env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("homr Р Р…Р Вµ Р В·Р В°Р Р†Р ВµРЎР‚РЎв‚¬Р С‘Р В» РЎР‚Р В°РЎРѓР С—Р С•Р В·Р Р…Р В°Р Р†Р В°Р Р…Р С‘Р Вµ Р В·Р В° 15 Р СР С‘Р Р…РЎС“РЎвЂљ.") from exc
    except OSError as exc:
        raise RuntimeError("Р СњР Вµ РЎС“Р Т‘Р В°Р В»Р С•РЎРѓРЎРЉ Р В·Р В°Р С—РЎС“РЎРѓРЎвЂљР С‘РЎвЂљРЎРЉ homr: " + str(exc)) from exc

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "homr Р Р…Р Вµ Р Р†РЎвЂ№Р Р†Р ВµР В» Р С—Р С•Р Т‘РЎР‚Р С•Р В±Р Р…Р С•РЎРѓРЎвЂљР ВµР в„–").strip()
        details = details[-3000:]
        raise RuntimeError(
            "homr Р В·Р В°Р Р†Р ВµРЎР‚РЎв‚¬Р С‘Р В»РЎРѓРЎРЏ РЎРѓ Р С”Р С•Р Т‘Р С•Р С " + str(result.returncode) + ".\n"
            "Р С™Р С•Р СР В°Р Р…Р Т‘Р В°: " + subprocess.list2cmdline([HOMR_PY, "-m", "homr.main", png_path]) + "\n"
            "Р вЂ™РЎвЂ№Р Р†Р С•Р Т‘ homr:\n" + details
        )

    created = os.path.splitext(png_path)[0] + ".musicxml"
    if not os.path.isfile(created):
        for f in os.listdir(tmpdir):
            if f.lower().endswith((".musicxml", ".xml")):
                created = os.path.join(tmpdir, f)
                break
    if not os.path.isfile(created):
        raise RuntimeError("homr Р Р…Р Вµ РЎРѓР С•Р В·Р Т‘Р В°Р В» MusicXML.")

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
    """Р С™Р С•Р Р…Р Р†Р ВµРЎР‚РЎвЂљР С‘РЎР‚РЎС“Р ВµРЎвЂљ Р С”Р В°РЎР‚РЎвЂљР С‘Р Р…Р С”РЎС“ Р Р† PDF (Р Т‘Р В»РЎРЏ fallback Р Р…Р В° Audiveris)."""
    from PIL import Image
    pdf_path = os.path.splitext(img_path)[0] + ".__conv.pdf"
    img = Image.open(img_path).convert("RGB")
    img.save(pdf_path, "PDF", resolution=300.0)
    return pdf_path


def run_homr_image(image_path):
    """Р В Р В°РЎРѓР С—Р С•Р В·Р Р…Р В°РЎвЂРЎвЂљ JPG/PNG/TIFF/BMP. Р вЂўРЎРѓР В»Р С‘ Р С•РЎР‚Р С‘Р С–Р С‘Р Р…Р В°Р В» Р Р…Р Вµ РЎР‚Р В°РЎРѓР С—Р С•Р В·Р Р…Р В°Р Р…, Р С—РЎР‚Р С•Р В±РЎС“Р ВµРЎвЂљ Р С—Р С•Р Т‘Р С–Р С•РЎвЂљР С•Р Р†Р В»Р ВµР Р…Р Р…РЎвЂ№Р Вµ Р Р†Р В°РЎР‚Р С‘Р В°Р Р…РЎвЂљРЎвЂ№."""
    if not os.path.isfile(image_path):
        raise RuntimeError("Р С™Р В°РЎР‚РЎвЂљР С‘Р Р…Р С”Р В° Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…Р В°: " + image_path)

    from PIL import Image, ImageOps, ImageFilter, ImageEnhance
    import shutil, tempfile

    os.makedirs(OMR_OUTPUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(image_path))[0]
    env = _homr_env()
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.abspath(os.path.join(here, os.pardir))
    venv_scripts = os.path.join(proj, "venv", "Scripts")
    if os.path.isdir(venv_scripts):
        env["PATH"] = venv_scripts + os.pathsep + env.get("PATH", "")

    tmpdir = tempfile.mkdtemp(prefix="homr_img_")
    attempts = []
    errors = []
    try:
        # Р вЂ™РЎРѓР ВµР С–Р Т‘Р В° Р С—РЎР‚Р С•Р В±РЎС“Р ВµР С Р С‘РЎРѓРЎвЂ¦Р С•Р Т‘Р Р…Р С‘Р С” Р С—Р ВµРЎР‚Р Р†РЎвЂ№Р С. TIFF Р С‘ JPEG РЎвЂљР В°Р С”Р В¶Р Вµ Р С—Р С•Р Т‘Р Т‘Р ВµРЎР‚Р В¶Р С‘Р Р†Р В°РЎР‹РЎвЂљРЎРѓРЎРЏ Pillow.
        with Image.open(image_path) as src:
            src.seek(0)
            _img = ImageOps.exif_transpose(src)
            if _img.mode in ("RGBA", "LA", "P"):
                _img = _img.convert("RGBA")
                _bg = Image.new("RGB", _img.size, (255, 255, 255))
                _bg.paste(_img, mask=_img.split()[-1])
                original = _bg
            else:
                original = _img.convert("RGB")
        original_path = os.path.join(tmpdir, "00_original.png")
        original.save(original_path, "PNG")
        attempts.append(("Р С•РЎР‚Р С‘Р С–Р С‘Р Р…Р В°Р В»", original_path))

        # Р СџР С•Р Т‘Р С–Р С•РЎвЂљР С•Р Р†Р В»Р ВµР Р…Р Р…РЎвЂ№Р Вµ Р Р†Р В°РЎР‚Р С‘Р В°Р Р…РЎвЂљРЎвЂ№ РЎРѓР С•Р В·Р Т‘Р В°РЎР‹РЎвЂљРЎРѓРЎРЏ РЎвЂљР С•Р В»РЎРЉР С”Р С• Р Т‘Р В»РЎРЏ РЎР‚Р В°РЎРѓР С—Р С•Р В·Р Р…Р В°Р Р†Р В°Р Р…Р С‘РЎРЏ; Р С‘РЎРѓРЎвЂ¦Р С•Р Т‘Р Р…Р С‘Р С” Р Р…Р Вµ Р СР ВµР Р…РЎРЏР ВµРЎвЂљРЎРѓРЎРЏ.
        gray = ImageOps.grayscale(original)
        gray = ImageOps.autocontrast(gray, cutoff=1)
        scale = 2 if max(gray.size) < 3000 else 1
        if scale > 1:
            gray = gray.resize((gray.width * scale, gray.height * scale), Image.Resampling.LANCZOS)
        contrast_path = os.path.join(tmpdir, "01_gray_contrast.png")
        gray.save(contrast_path)
        attempts.append(("РЎвЂЎРЎвЂРЎР‚Р Р…Р С•-Р В±Р ВµР В»РЎвЂ№Р в„– РЎРѓ Р В°Р Р†РЎвЂљР С•Р С”Р С•Р Р…РЎвЂљРЎР‚Р В°РЎРѓРЎвЂљР С•Р С Р С‘ РЎС“Р Р†Р ВµР В»Р С‘РЎвЂЎР ВµР Р…Р С‘Р ВµР С", contrast_path))

        # Р Р€Р В±Р С‘РЎР‚Р В°Р ВµР С Р СР ВµР В»Р С”Р С‘Р в„– РЎв‚¬РЎС“Р С, Р В·Р В°РЎвЂљР ВµР С РЎРѓРЎвЂљРЎР‚Р С•Р С‘Р С РЎвЂЎРЎвЂРЎвЂљР С”Р С‘Р в„– Р Р†Р В°РЎР‚Р С‘Р В°Р Р…РЎвЂљ РЎРѓ Р С—Р С•РЎР‚Р С•Р С–Р С•Р С Otsu (Р ВµРЎРѓР В»Р С‘ Р Т‘Р С•РЎРѓРЎвЂљРЎС“Р С—Р ВµР Р… OpenCV).
        try:
            import cv2
            import numpy as np
            arr = np.array(gray)
            arr = cv2.medianBlur(arr, 3)
            _, otsu = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            otsu_path = os.path.join(tmpdir, "02_otsu.png")
            Image.fromarray(otsu).save(otsu_path)
            attempts.append(("Р С—Р С•РЎР‚Р С•Р С–Р С•Р Р†Р В°РЎРЏ Р С•Р В±РЎР‚Р В°Р В±Р С•РЎвЂљР С”Р В° Otsu", otsu_path))
            adaptive = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                             cv2.THRESH_BINARY, 35, 11)
            adaptive_path = os.path.join(tmpdir, "03_adaptive.png")
            Image.fromarray(adaptive).save(adaptive_path)
            attempts.append(("Р В°Р Т‘Р В°Р С—РЎвЂљР С‘Р Р†Р Р…Р В°РЎРЏ Р С—Р С•РЎР‚Р С•Р С–Р С•Р Р†Р В°РЎРЏ Р С•Р В±РЎР‚Р В°Р В±Р С•РЎвЂљР С”Р В°", adaptive_path))
        except Exception as prep_error:
            print("[homr-img] OpenCV Р Р…Р ВµР Т‘Р С•РЎРѓРЎвЂљРЎС“Р С—Р ВµР Р…, Р С—РЎР‚Р С•Р С—РЎС“РЎРѓР С”Р В°РЎР‹ Р С—Р С•РЎР‚Р С•Р С–Р С•Р Р†РЎвЂ№Р Вµ Р Р†Р В°РЎР‚Р С‘Р В°Р Р…РЎвЂљРЎвЂ№:", prep_error, flush=True)

        # Р ВР Р…Р Р†Р ВµРЎР‚РЎРѓР С‘РЎРЏ Р В±РЎвЂ№Р Р†Р В°Р ВµРЎвЂљ Р С—Р С•Р В»Р ВµР В·Р Р…Р В° Р Т‘Р В»РЎРЏ РЎРѓР С”Р В°Р Р…Р С•Р Р† РЎРѓ РЎвЂљРЎвЂР СР Р…РЎвЂ№Р С РЎвЂћР С•Р Р…Р С•Р С.
        inverted_path = os.path.join(tmpdir, "04_inverted.png")
        ImageOps.invert(gray).save(inverted_path)
        attempts.append(("Р С‘Р Р…Р Р†Р ВµРЎР‚РЎРѓР С‘РЎРЏ", inverted_path))

        for label, candidate in attempts:
            print(f"[homr-img] Р С—Р С•Р С—РЎвЂ№РЎвЂљР С”Р В°: {label}: {candidate}", flush=True)
            before_files = set(os.listdir(tmpdir))
            try:
                result = subprocess.run(
                    [HOMR_PY, "-m", "homr.main", candidate], check=False, capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=240,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                errors.append(f"{label}: Р С—РЎР‚Р ВµР Р†РЎвЂ№РЎв‚¬Р ВµР Р…Р С• Р Р†РЎР‚Р ВµР СРЎРЏ Р С•Р В¶Р С‘Р Т‘Р В°Р Р…Р С‘РЎРЏ 4 Р СР С‘Р Р…РЎС“РЎвЂљРЎвЂ№")
                continue
            except OSError as exc:
                raise RuntimeError("Р СњР Вµ РЎС“Р Т‘Р В°Р В»Р С•РЎРѓРЎРЉ Р В·Р В°Р С—РЎС“РЎРѓРЎвЂљР С‘РЎвЂљРЎРЉ homr: " + str(exc)) from exc

            created_candidates = [os.path.splitext(candidate)[0] + ".musicxml"]
            try:
                created_candidates.extend(
                    os.path.join(tmpdir, f) for f in os.listdir(tmpdir)
                    if f not in before_files and f.lower().endswith((".musicxml", ".xml"))
                )
            except OSError:
                pass
            created = next((f for f in created_candidates if os.path.isfile(f)), None)
            if result.returncode == 0 and created:
                final_path = os.path.join(OMR_OUTPUT_DIR, base + ".musicxml")
                if os.path.isfile(final_path):
                    try:
                        os.remove(final_path)
                    except OSError:
                        pass
                shutil.copy2(created, final_path)
                print(f"[homr-img] РЎС“РЎРѓР С—Р ВµРЎв‚¬Р Р…Р С• РЎР‚Р В°РЎРѓР С—Р С•Р В·Р Р…Р В°Р Р…Р С•: {label}", flush=True)
                return final_path

            details = (result.stderr or result.stdout or "MusicXML Р Р…Р Вµ РЎРѓР С•Р В·Р Т‘Р В°Р Р…").strip()[-1200:]
            errors.append(f"{label}: Р С”Р С•Р Т‘ {result.returncode}; {details}")
            print(f"[homr-img] Р Р…Р ВµРЎС“Р Т‘Р В°РЎвЂЎР В° ({label}): {details}", flush=True)

        raise RuntimeError("Р СњР Вµ РЎС“Р Т‘Р В°Р В»Р С•РЎРѓРЎРЉ РЎР‚Р В°РЎРѓР С—Р С•Р В·Р Р…Р В°РЎвЂљРЎРЉ Р С‘Р В·Р С•Р В±РЎР‚Р В°Р В¶Р ВµР Р…Р С‘Р Вµ Р Р…Р С‘ Р Р† Р С•Р Т‘Р Р…Р С•Р С Р Р†Р В°РЎР‚Р С‘Р В°Р Р…РЎвЂљР Вµ.\n" + "\n".join(errors[-5:]))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------- MusicXML -> РЎРѓР С•Р В±РЎвЂ№РЎвЂљР С‘РЎРЏ ----------
def recognize_tempo_from_image(image_path: str):
    """Recognize an explicit tempo marking in a score image."""
    import json
    import re
    import subprocess

    try:
        app_dir = (
            os.path.dirname(os.path.abspath(sys.executable))
            if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        candidates = [
            os.path.join(app_dir, "tools", "python", "python.exe"),
            os.path.join(app_dir, "dist", "NowPiano", "tools", "python", "python.exe"),
        ]

        python_path = next((p for p in candidates if os.path.isfile(p)), None)
        if not python_path:
            return None

        bundle_root = os.path.dirname(
            os.path.dirname(os.path.dirname(python_path))
        )
        site_packages = os.path.join(
            bundle_root, "tools", "python", "Lib", "site-packages"
        )
        internal_dir = os.path.join(bundle_root, "_internal")

        env = os.environ.copy()
        extra_paths = [site_packages, internal_dir]
        existing = env.get("PYTHONPATH", "")
        if existing:
            extra_paths.append(existing)
        env["PYTHONPATH"] = os.pathsep.join(extra_paths)

        ocr_script = (
            "import json,sys; from rapidocr import RapidOCR; "
            "r=RapidOCR()(sys.argv[1]); "
            "print('NOWPIANO_OCR_JSON:'+json.dumps("
            "{'txts':list(r.txts or []),"
            "'scores':[float(x) for x in (r.scores or [])]}))"
        )

        result = subprocess.run(
            [python_path, "-c", ocr_script, os.path.abspath(image_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        marker = "NOWPIANO_OCR_JSON:"
        payload = next(
            (line.split(marker, 1)[1]
             for line in reversed(result.stdout.splitlines())
             if marker in line),
            None,
        )
        if result.returncode != 0 or payload is None:
            print("[tempo-ocr] OCR unavailable; using MusicXML/default tempo.")
            return None

        data = json.loads(payload)
        texts = data.get("txts", [])
        scores = data.get("scores", [])
        matches = []

        # Require a tempo-like marker, such as OCR's "J=134".
        pattern = re.compile(
            r"(?:[jil|!]|[♩♪])\s*(?:=|:)?\s*(\d{2,3})",
            re.IGNORECASE,
        )

        for index, text in enumerate(texts):
            confidence = float(scores[index]) if index < len(scores) else 0.0
            if confidence < 0.60:
                continue

            match = pattern.search(str(text))
            if not match:
                continue

            bpm = int(match.group(1))
            if 20 < bpm < 400:
                matches.append((confidence, bpm, str(text)))

        if not matches:
            return None

        confidence, bpm, text = max(matches, key=lambda item: item[0])
        print(
            f"[tempo-ocr] Recognized tempo: {bpm} BPM "
            f"(text={text!r}, confidence={confidence:.2f})",
            flush=True,
        )
        return float(bpm)

    except Exception as exc:
        print(f"[tempo-ocr] Recognition skipped: {exc}", flush=True)
        return None

def musicxml_to_events(mxl_path: str, bpm_override=None):
    """Р СџР В°РЎР‚РЎРѓР С‘РЎвЂљ MusicXML Р С‘ РЎРѓР С•РЎвЂ¦РЎР‚Р В°Р Р…РЎРЏР ВµРЎвЂљ РЎР‚Р В°Р В·Р Т‘Р ВµР В»Р ВµР Р…Р С‘Р Вµ Р С—РЎР‚Р В°Р Р†Р С•Р в„–/Р В»Р ВµР Р†Р С•Р в„– РЎР‚РЎС“Р С”Р С‘.

    Р вЂ™Р В°Р В¶Р Р…РЎвЂ№Р в„– Р С—РЎР‚Р С‘Р Р…РЎвЂ Р С‘Р С—: Р Р…Р ВµР В»РЎРЉР В·РЎРЏ Р С•Р В±РЎР‰Р ВµР Т‘Р С‘Р Р…РЎРЏРЎвЂљРЎРЉ Р С•Р Т‘Р Р…Р С•Р Р†РЎР‚Р ВµР СР ВµР Р…Р Р…РЎвЂ№Р Вµ Р Р…Р С•РЎвЂљРЎвЂ№ РЎР‚Р В°Р В·Р Р…РЎвЂ№РЎвЂ¦ РЎР‚РЎС“Р С” Р Р† Р С•Р Т‘Р Р…Р С•
    РЎРѓР С•Р В±РЎвЂ№РЎвЂљР С‘Р Вµ РІР‚вЂќ Р С‘Р Р…Р В°РЎвЂЎР Вµ Р С—РЎР‚Р С•Р С‘Р С–РЎР‚РЎвЂ№Р Р†Р В°РЎвЂљР ВµР В»РЎРЉ Р С‘ РЎвЂ Р С‘РЎвЂћРЎР‚Р С•Р Р†Р В°РЎРЏ Р С—Р В°РЎР‚РЎвЂљР С‘РЎвЂљРЎС“РЎР‚Р В° Р Р…Р В°Р В·Р Р…Р В°РЎвЂЎР В°РЎР‹РЎвЂљ Р Р†Р ВµРЎРѓРЎРЉ Р В°Р С”Р С”Р С•РЎР‚Р Т‘
    Р С•Р Т‘Р Р…Р С•Р в„– РЎР‚РЎС“Р С”Р Вµ. Р вЂўРЎРѓР В»Р С‘ MusicXML РЎРѓР С•Р Т‘Р ВµРЎР‚Р В¶Р С‘РЎвЂљ Р С•РЎвЂљР Т‘Р ВµР В»РЎРЉР Р…РЎвЂ№Р Вµ Р С—Р В°РЎР‚РЎвЂљР С‘Р С‘/РЎРѓРЎвЂљР В°Р Р…РЎвЂ№, Р С‘РЎРѓР С—Р С•Р В»РЎРЉР В·РЎС“Р ВµР С Р С‘РЎвЂ¦;
    Р ВµРЎРѓР В»Р С‘ РЎРЊРЎвЂљР С• Р С•Р Т‘Р С‘Р Р… Р С•Р В±РЎвЂ°Р С‘Р в„– Р С—Р С•РЎвЂљР С•Р С”, РЎР‚Р В°Р В·Р Т‘Р ВµР В»РЎРЏР ВµР С Р Р…Р С•РЎвЂљРЎвЂ№ Р В°Р С”Р С”Р С•РЎР‚Р Т‘Р В° Р С—Р С• Р Р†РЎвЂ№РЎРѓР С•РЎвЂљР Вµ Р Р†Р С•Р С”РЎР‚РЎС“Р С– C4.
    """
    if not MUSIC21_OK:
        raise RuntimeError("music21 Р Р…Р Вµ РЎС“РЎРѓРЎвЂљР В°Р Р…Р С•Р Р†Р В»Р ВµР Р…")

    score = converter.parse(mxl_path)
    def _find_bpm(sc, default=MANUAL_BPM, xml_path=None):
        # 1) Сначала читаем СЫРОЙ XML: ищем <sound tempo=>, <metronome><per-minute>, <words>=134
        #    (music21 всегда подставляет свой MetronomeMark=120, если темпа в XML нет —
        #     поэтому доверять sc.metronomeMarkBoundaries() без проверки исходника нельзя).
        if xml_path:
            try:
                import zipfile, re as _re2
                raw = None
                if str(xml_path).lower().endswith('.mxl'):
                    with zipfile.ZipFile(xml_path, 'r') as z:
                        for n in z.namelist():
                            if n.lower().endswith('.xml') and 'META-INF' not in n:
                                raw = z.read(n).decode('utf-8', 'ignore'); break
                else:
                    with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
                        raw = f.read()
                if raw:
                    m = _re2.search(r'<sound[^>]*tempo\s*=\s*[\"](\d{2,3})[\"]', raw)
                    if m:
                        v = float(m.group(1))
                        if 20 < v < 400: return v
                    m = _re2.search(r'<per-minute>\s*(\d{2,3})\s*</per-minute>', raw)
                    if m:
                        v = float(m.group(1))
                        if 20 < v < 400: return v
                    m = _re2.search(r'=\s*(\d{2,3})', raw)
                    if m:
                        v = float(m.group(1))
                        if 20 < v < 400: return v
            except Exception:
                pass
        # 2) Если в XML темпа нет — возвращаем default (MANUAL_BPM),
        #    НЕ доверяя metronomeMarkBoundaries (он даёт 120 по умолчанию).
        return default

    bpm = _find_bpm(score, MANUAL_BPM, mxl_path)
    if bpm_override is not None:
        try:
            override = float(bpm_override)
            if 20 < override < 400:
                bpm = override
        except (TypeError, ValueError):
            pass
    spq = 60.0 / bpm
    used_parts = [p for p in score.parts if len(list(p.flatten().notes)) > 0]
    if not used_parts:
        raise RuntimeError("Р вЂ™ Р С—Р В°РЎР‚РЎвЂљР С‘РЎвЂљРЎС“РЎР‚Р Вµ Р Р…Р ВµРЎвЂљ Р Р…Р С•РЎвЂљ")

    events = []
    for part_idx, part in enumerate(used_parts):
        for el in part.flatten().notesAndRests:
            dur_q = float(el.quarterLength)
            if dur_q <= 0 or not (hasattr(el, "pitches") and len(el.pitches) > 0):
                continue
            offset_q = float(el.offset)
            try:
                bar = int(el.measureNumber) if el.measureNumber else 0
            except Exception:
                bar = 0

            spelling_by_midi = {
                int(p.midi): str(p.name)
                for p in el.pitches
                if START_NOTE <= int(p.midi) <= START_NOTE + NUM_KEYS - 1
            }
            midis = sorted(spelling_by_midi)
            if not midis:
                continue

            # MusicXML Р С•Р В±РЎвЂ№РЎвЂЎР Р…Р С• РЎвЂ¦РЎР‚Р В°Р Р…Р С‘РЎвЂљ РЎР‚РЎС“Р С”Р С‘ Р С•РЎвЂљР Т‘Р ВµР В»РЎРЉР Р…РЎвЂ№Р СР С‘ Part/PartStaff.
            # Р вЂќР В»РЎРЏ Р ВµР Т‘Р С‘Р Р…РЎРѓРЎвЂљР Р†Р ВµР Р…Р Р…Р С•Р в„– РЎвЂћР С•РЎР‚РЎвЂљР ВµР С—Р С‘Р В°Р Р…Р Р…Р С•Р в„– Р С—Р В°РЎР‚РЎвЂљР С‘Р С‘ Р Т‘Р ВµР В»Р С‘Р С Р В°Р С”Р С”Р С•РЎР‚Р Т‘ Р С—Р С• Р Р…Р С•РЎвЂљР В°Р С,
            # РЎвЂЎРЎвЂљР С•Р В±РЎвЂ№ Р Р…Р С‘Р В·Р С”Р С‘Р Вµ Р Р…Р С•РЎвЂљРЎвЂ№ Р Р…Р Вµ Р С•Р С”РЎР‚Р В°РЎв‚¬Р С‘Р Р†Р В°Р В»Р С‘РЎРѓРЎРЉ Р С‘ Р Р…Р Вµ Р Р†Р С•РЎРѓР С—РЎР‚Р С•Р С‘Р В·Р Р†Р С•Р Т‘Р С‘Р В»Р С‘РЎРѓРЎРЉ Р С”Р В°Р С” Р С—РЎР‚Р В°Р Р†Р В°РЎРЏ РЎР‚РЎС“Р С”Р В°.
            groups = {"R": [], "L": []}

            # ?????????? ???? ?? ????? ??????, ? ?? ?? ?? ??????.
            clef_names = {
                obj.__class__.__name__
                for obj in part.recurse()
                if "Clef" in obj.__class__.__name__
            }

            has_treble = "TrebleClef" in clef_names
            has_bass = "BassClef" in clef_names

            if has_treble and not has_bass:
                groups["R"] = midis
            elif has_bass and not has_treble:
                groups["L"] = midis
            else:
                # ????????? ?????? (????????, ????? ? ????? ???????):
                # ???????????? ???? ?? ??????, ?? ????????? ????.
                for midi in midis:
                    groups["R" if midi >= 60 else "L"].append(midi)

            for hand, hand_midis in groups.items():
                if not hand_midis:
                    continue
                events.append(NoteEvent(
                    bar=bar,
                    offset_q=offset_q,
                    time_seconds=offset_q * spq,
                    notes=hand_midis,
                    duration=max(0.05, dur_q * spq),
                    hand=hand,
                    part=part_idx,
                    note_names={m: spelling_by_midi[m] for m in hand_midis if m in spelling_by_midi},
                ))

    events.sort(key=lambda e: (e.time_seconds, 0 if e.hand == "R" else 1))

    # Р РЋР С”Р В»Р ВµР С‘Р Р†Р В°Р ВµР С РЎвЂљР С•Р В»РЎРЉР С”Р С• РЎРѓР С•Р В±РЎвЂ№РЎвЂљР С‘РЎРЏ Р С•Р Т‘Р Р…Р С•Р в„– РЎР‚РЎС“Р С”Р С‘ Р Р† Р С•Р Т‘Р С‘Р Р… Р СР С•Р СР ВµР Р…РЎвЂљ Р Р†РЎР‚Р ВµР СР ВµР Р…Р С‘.
    # Р РЋР С•Р В±РЎвЂ№РЎвЂљР С‘РЎРЏ R Р С‘ L Р С•РЎРѓРЎвЂљР В°РЎР‹РЎвЂљРЎРѓРЎРЏ РЎР‚Р В°Р В·Р Т‘Р ВµР В»РЎРЉР Р…РЎвЂ№Р СР С‘ Р Т‘Р В»РЎРЏ Р Р†Р ВµРЎР‚Р Р…РЎвЂ№РЎвЂ¦ РЎвЂ Р Р†Р ВµРЎвЂљР С•Р Р†, Р С—Р С•Р Т‘Р С—Р С‘РЎРѓР ВµР в„– Р С‘ Р С—Р С•Р Т‘РЎРѓР Р†Р ВµРЎвЂљР С”Р С‘.
    merged: List[NoteEvent] = []
    for ev in events:
        match = None
        for last in reversed(merged):
            if ev.time_seconds - last.time_seconds > 0.02:
                break
            if abs(ev.time_seconds - last.time_seconds) < 0.02 and ev.hand == last.hand:
                match = last
                break
        if match is not None:
            match.notes = sorted(set(match.notes) | set(ev.notes))
            match.note_names.update(ev.note_names)
            match.duration = max(match.duration, ev.duration)
        else:
            merged.append(NoteEvent(
                bar=ev.bar,
                offset_q=ev.offset_q,
                time_seconds=ev.time_seconds,
                notes=list(ev.notes),
                duration=ev.duration,
                hand=ev.hand,
                part=ev.part,
                note_names=dict(ev.note_names),
            ))

    if merged:
        t0 = merged[0].time_seconds
        o0 = merged[0].offset_q
        if t0 > 0.05:
            for ev in merged:
                ev.time_seconds -= t0
                ev.offset_q -= o0

    right_count = sum(1 for ev in merged if ev.hand == "R")
    left_count = sum(1 for ev in merged if ev.hand == "L")
    print(f"[audio] MusicXML parsed: {len(merged)} events, right={right_count}, left={left_count}, BPM={bpm:.1f}")
    return merged, bpm, len(used_parts)


def total_duration(events: List[NoteEvent]) -> float:
    if not events:
        return 0.0
    last = events[-1]
    return float(last.time_seconds) + float(last.duration)


# ---------- Р СћР ВµРЎРѓРЎвЂљ Р СР С•Р Т‘РЎС“Р В»РЎРЏ ----------
# ---------- Р В­Р С”РЎРѓР С—Р С•РЎР‚РЎвЂљ Р Р† MIDI ----------
def export_midi(mxl_path: str, out_path: str) -> bool:
    """Р С™Р С•Р Р…Р Р†Р ВµРЎР‚РЎвЂљР С‘РЎР‚РЎС“Р ВµРЎвЂљ MusicXML/MXL Р Р† MIDI РЎвЂЎР ВµРЎР‚Р ВµР В· music21.
    Р вЂ™Р С•Р В·Р Р†РЎР‚Р В°РЎвЂ°Р В°Р ВµРЎвЂљ True Р С—РЎР‚Р С‘ РЎС“РЎРѓР С—Р ВµРЎвЂ¦Р Вµ."""
    if not MUSIC21_OK:
        print("[midi] music21 Р Р…Р ВµР Т‘Р С•РЎРѓРЎвЂљРЎС“Р С—Р ВµР Р…")
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
    """Р РЋР Т‘Р Р†Р С‘Р С–Р В°Р ВµРЎвЂљ Р Р…Р С•РЎвЂљРЎС“ Р С•Р С”РЎвЂљР В°Р Р†Р В°Р СР С‘, Р С—Р С•Р С”Р В° Р С•Р Р…Р В° Р Р…Р Вµ Р С—Р С•Р С—Р В°Р Т‘РЎвЂРЎвЂљ Р Р† Р Т‘Р С‘Р В°Р С—Р В°Р В·Р С•Р Р… Р С”Р В»Р В°Р Р†Р С‘Р В°РЎвЂљРЎС“РЎР‚РЎвЂ№."""
    lo = START_NOTE
    hi = START_NOTE + NUM_KEYS - 1
    while midi < lo:
        midi += 12
    while midi > hi:
        midi -= 12
    return midi


def load_midi_events(midi_path: str):
    """Р В§Р С‘РЎвЂљР В°Р ВµРЎвЂљ MIDI Р С‘ Р Р†Р С•Р В·Р Р†РЎР‚Р В°РЎвЂ°Р В°Р ВµРЎвЂљ (events, bpm). events РІР‚вЂќ РЎРѓР С—Р С‘РЎРѓР С•Р С” NoteEvent.
    Р Р€РЎвЂЎР С‘РЎвЂљРЎвЂ№Р Р†Р В°Р ВµРЎвЂљ Р С”Р В°Р Р…Р В°Р В»РЎвЂ№: ch0 -> R, ch1 -> L, Р С•РЎРѓРЎвЂљР В°Р В»РЎРЉР Р…РЎвЂ№Р Вµ РІР‚вЂќ Р С—Р С• Р Р†РЎвЂ№РЎРѓР С•РЎвЂљР Вµ.
    BPM: Р С‘Р В· Р СР ВµРЎвЂљРЎР‚Р С•Р Р…Р С•Р СР В°, Р С‘Р Р…Р В°РЎвЂЎР Вµ 120 (РЎРѓРЎвЂљР В°Р Р…Р Т‘Р В°РЎР‚РЎвЂљ MIDI)."""
    if not MUSIC21_OK:
        raise RuntimeError("music21 Р Р…Р ВµР Т‘Р С•РЎРѓРЎвЂљРЎС“Р С—Р ВµР Р…")
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

    # music21 Р СР С•Р В¶Р ВµРЎвЂљ РЎР‚Р В°Р В·Р В»Р С•Р В¶Р С‘РЎвЂљРЎРЉ MIDI Р Р…Р В° Р С—Р В°РЎР‚РЎвЂљР С‘Р С‘ Р С—Р С• Р С”Р В°Р Р…Р В°Р В»Р В°Р С
    parts = list(score.parts) if score.parts else [score]
    if len(parts) == 1:
        # Р С›Р Т‘Р С‘Р Р… Р С—Р С•РЎвЂљР С•Р С” РІР‚вЂќ РЎР‚Р В°Р В·Р Т‘Р ВµР В»Р С‘Р С Р С—Р С• Р Р†РЎвЂ№РЎРѓР С•РЎвЂљР Вµ
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
        # Р СљР Р…Р С•Р С–Р С• Р С—Р В°РЎР‚РЎвЂљР С‘Р в„– РІР‚вЂќ Р С—Р ВµРЎР‚Р Р†Р В°РЎРЏ R, Р Р†РЎвЂљР С•РЎР‚Р В°РЎРЏ L (Р С‘Р В»Р С‘ Р С—Р С• Р С”Р В°Р Р…Р В°Р В»РЎС“)
        for p_idx, part in enumerate(parts):
            hand = "R"  # Р Р†РЎР‚Р ВµР СР ВµР Р…Р Р…Р С•, РЎС“РЎвЂљР С•РЎвЂЎР Р…Р С‘Р С Р С—Р С• Р Р†РЎвЂ№РЎРѓР С•РЎвЂљР Вµ Р Р…Р С‘Р В¶Р Вµ
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
        print("Р ВР С–РЎР‚Р В°РЎР‹ Р С–Р В°Р СР СРЎС“ Р Т‘Р С•-Р СР В°Р В¶Р С•РЎР‚...")
        notes = [60, 62, 64, 65, 67, 69, 71, 72]
        for i, n in enumerate(notes):
            engine.note_on(n, 100)
            engine.note_off_later(n, 0.4)
            time.sleep(0.3)
        time.sleep(1.0)
        engine.shutdown()
        print("Р вЂњР С•РЎвЂљР С•Р Р†Р С•.")
    else:
        print("AudioEngine Р Р…Р Вµ Р В·Р В°Р С—РЎС“РЎРѓРЎвЂљР С‘Р В»РЎРѓРЎРЏ.")


# ---------- Р В Р ВµР Р…Р Т‘Р ВµРЎР‚ MIDI/MusicXML Р Р† PNG РЎвЂЎР ВµРЎР‚Р ВµР В· MuseScore ----------
def render_score_to_pngs(source_path: str, out_dir: str = None, max_pages: int = 10):
    """Р В Р ВµР Р…Р Т‘Р ВµРЎР‚Р С‘РЎвЂљ MIDI Р С‘Р В»Р С‘ MusicXML Р Р† PNG РЎвЂЎР ВµРЎР‚Р ВµР В· music21 + MuseScore.
    Р вЂ™Р С•Р В·Р Р†РЎР‚Р В°РЎвЂ°Р В°Р ВµРЎвЂљ РЎРѓР С—Р С‘РЎРѓР С•Р С” Р С—РЎС“РЎвЂљР ВµР в„– Р С” PNG (Р С—Р С• Р С•Р Т‘Р Р…Р С•Р в„– Р Р…Р В° РЎРѓРЎвЂљРЎР‚Р В°Р Р…Р С‘РЎвЂ РЎС“)."""
    if not MUSIC21_OK:
        print("[render] music21 Р Р…Р ВµР Т‘Р С•РЎРѓРЎвЂљРЎС“Р С—Р ВµР Р…")
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




