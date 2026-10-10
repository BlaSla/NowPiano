# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

HERE = os.path.dirname(os.path.abspath(SPEC))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))

datas = []
binaries = []
hiddenimports = []

# --- PyQt6 ---
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# --- fluidsynth (pyfluidsynth) ---
try:
    tmp_ret = collect_all('fluidsynth')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except Exception:
    hiddenimports += ['fluidsynth']

# --- pdf2image ---
tmp_ret = collect_all('pdf2image')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# --- PIL ---
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# --- music21 (ОБЯЗАТЕЛЬНО — используется для MusicXML и MIDI) ---
tmp_ret = collect_all('music21')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# --- Наши ресурсы ---
datas += [
    (os.path.join(ROOT, 'assets', 'back.jpg'),  'assets'),
    (os.path.join(ROOT, 'soundfonts'),          'soundfonts'),
    (os.path.join(ROOT, 'tools', 'poppler'),    'tools\\poppler'),
    (os.path.join(ROOT, 'tools', 'audiveris'),  'tools\\audiveris'),
    (os.path.join(ROOT, 'tools', 'fluidsynth'), 'tools\\fluidsynth'),
]

hiddenimports += ['qt_audio', 'qt_render', 'qt_pianoroll']

excludes = [
    'matplotlib', 'scipy', 'pandas', 'IPython', 'jupyter', 'notebook',
    'pygame', 'cv2',
    'tkinter',
]

a = Analysis(
    [os.path.join(ROOT, 'src', 'piano_qt.py')],
    pathex=[os.path.join(ROOT, 'src')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='NowPiano', debug=False,
    bootloader_ignore_signals=False, strip=False,
    upx=True, console=False, disable_windowed_traceback=False,
    icon=os.path.join(ROOT, 'assets', 'piano.ico'),
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[], name='NowPiano',
)