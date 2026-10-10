# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

datas = []
binaries = []
hiddenimports = []

# --- PyQt6 ---
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# --- pygame ---
tmp_ret = collect_all('pygame')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# --- music21: все подмодули ---
tmp_ret = collect_all('music21')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
hiddenimports += collect_submodules('music21')

hiddenimports += [
    'music21.converter', 'music21.stream', 'music21.note', 'music21.chord',
    'music21.meter', 'music21.tempo', 'music21.metadata', 'music21.duration',
    'music21.key', 'music21.clef', 'music21.instrument',
    'music21.musicxml', 'music21.musicxml.xmlToM21', 'music21.musicxml.m21ToXml',
    'music21.midi', 'music21.midi.translate', 'music21.midi.base',
    'music21.environment', 'music21.common',
    'music21.harmony', 'music21.roman', 'music21.scale',
    'music21.tie', 'music21.pitch', 'music21.layout',
    'music21.beam', 'music21.expressions', 'music21.articulations',
    'music21.dynamics', 'music21.spanner',
    'music21.figuredBass', 'music21.figuredBass.realizer',
    'music21.tree', 'music21.tree.spanner', 'music21.tree.trees',
]

# --- cv2 ---
tmp_ret = collect_all('cv2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# --- numpy ---
tmp_ret = collect_all('numpy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# --- PIL ---
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# --- pdf2image ---
tmp_ret = collect_all('pdf2image')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# --- fluidsynth ---
try:
    tmp_ret = collect_all('fluidsynth')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except Exception:
    hiddenimports += ['fluidsynth']

datas += [(r'C:\NowPiano\assets\back.jpg', 'assets')]
hiddenimports += ['qt_audio', 'qt_render', 'qt_pianoroll', 'unittest', 'unittest.mock']

a = Analysis(
    [r'C:\NowPiano\src\piano_qt.py'],
    pathex=[r'C:\NowPiano\src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas', 'IPython', 'jupyter', 'notebook'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NowPiano',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NowPiano',
)
