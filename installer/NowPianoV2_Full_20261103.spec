# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SRC = os.path.join(ROOT, "src")
block_cipher = None

datas = []
binaries = []
hiddenimports = []

# Python packages used by NowPianoV2
for package_name in [
    "PyQt6", "fluidsynth", "pdf2image", "PIL", "music21",
    "homr", "cv2", "onnxruntime", "rapidocr", "shapely",
    "musicxml", "numpy", "requests", "typing_extensions",
    "mido", "rtmidi"
]:
    try:
        d, b, h = collect_all(package_name)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:
        print("Optional collection warning:", package_name, repr(exc))

hiddenimports += [
    "qt_audio", "qt_render", "qt_pianoroll",
    "mido", "mido.backends.rtmidi",
    "mido.backends.rtmidi_python",
    "rtmidi", "rtmidi._rtmidi"
]

# App resources
for name in ("app_icon.ico", "app_icon.png", "donate_qr.png"):
    path = os.path.join(ROOT, "resources", name)
    if os.path.isfile(path):
        datas.append((path, "resources"))

# FluidSynth runtime
fs_dir = os.path.join(ROOT, "tools", "fluidsynth", "bin")
if os.path.isdir(fs_dir):
    for name in os.listdir(fs_dir):
        path = os.path.join(fs_dir, name)
        if os.path.isfile(path):
            target = "tools/fluidsynth/bin"
            if name.lower().endswith(".dll"):
                binaries.append((path, target))
            else:
                datas.append((path, target))

# SoundFonts
for name in ("Arachno_SoundFont_Version_1.0.sf2", "FluidR3_GM.sf2"):
    path = os.path.join(ROOT, "soundfonts", name)
    if not os.path.isfile(path):
        raise FileNotFoundError("SoundFont not found: " + path)
    datas.append((path, "soundfonts"))

# Standalone HOMR including its _internal directory
homr_dir = os.path.join(
    ROOT, "release_stage_allinone_20261015", "NowPiano",
    "_internal", "tools", "homr_standalone"
)
if not os.path.isfile(os.path.join(homr_dir, "homr.exe")):
    raise FileNotFoundError("Verified HOMR executable not found: " + homr_dir)
datas.append((homr_dir, "tools/homr_standalone"))

# External OMR and PDF tools
for _tool in ("audiveris", "poppler"):
    _src = os.path.join(ROOT, "tools", _tool)
    if not os.path.isdir(_src):
        raise FileNotFoundError("Required tool directory not found: " + _src)
    datas.append((_src, "tools/" + _tool))


# Complete portable MuseScore Studio 4.7.5 application
musescore_dir = os.path.join(
    ROOT, "musescore_portable_test_20261103", "MuseScore 4"
)
musescore_exe = os.path.join(
    musescore_dir, "bin", "MuseScore4.exe"
)
if not os.path.isfile(musescore_exe):
    raise FileNotFoundError("MuseScore 4 executable not found: " + musescore_exe)

# Copy the entire application directory, not only the executable.
datas.append((musescore_dir, "MuseScore 4"))

# Preserve the MuseScore license notice in the installed application.
musescore_license = os.path.join(
    ROOT, "musescore_source_4.7.5_20261103", "LICENSE.txt"
)
if not os.path.isfile(musescore_license):
    raise FileNotFoundError("MuseScore LICENSE.txt not found")
datas.append((musescore_license, "licenses/MuseScore"))

excludes = [
    "matplotlib", "scipy", "pandas", "IPython", "jupyter", "notebook",
    "pygame", "numba", "llvmlite", "tkinter"
]

a = Analysis(
    [os.path.join(SRC, "piano_qt.py")],
    pathex=[SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="NowPianoV2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(ROOT, "resources", "app_icon.ico"),
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, upx_exclude=[],
    name="NowPianoV2",
)
