# -*- coding: utf-8 -*-
"""Диагностика звука FluidSynth для NowPiano. Запуск: python NowPiano_audio_test.py"""
import os, sys, time

here = os.path.dirname(os.path.abspath(__file__))
proj = os.path.abspath(os.path.join(here, os.pardir))
for cand in (os.path.join(proj, 'tools', 'fluidsynth', 'bin'),
             os.path.join(proj, 'tools', 'fluidsynth')):
    if os.path.isdir(cand):
        try: os.add_dll_directory(cand)
        except Exception: pass
        os.environ['PATH'] = cand + os.pathsep + os.environ.get('PATH', '')
        print('DLL dir:', cand)
        break

try:
    import fluidsynth
    print('pyfluidsynth import: OK')
except Exception as e:
    print('ERROR: cannot import fluidsynth:', repr(e))
    input('Enter для выхода...'); raise SystemExit(1)

candidates = [
    os.path.join(proj, 'soundfonts', 'Arachno_SoundFont_Version_1.0.sf2'),
    os.path.join(proj, 'soundfonts', 'FluidR3_GM.sf2'),
    r'C:\tools\fluidsynth\soundfonts\Arachno_SoundFont_Version_1.0.sf2',
    os.path.join(os.path.expanduser('~'), '.aldakit', 'soundfonts', 'Arachno_SoundFont_Version_1.0.sf2'),
]
sf = next((p for p in candidates if os.path.isfile(p)), None)
print('SoundFont:', sf or 'NOT FOUND')
if not sf:
    print('Положите .sf2 в папку C:\\NowPiano\\soundfonts\\ или укажите путь в этом скрипте.')
    input('Enter для выхода...'); raise SystemExit(2)

for driver in ('waveout', 'dsound', 'winmm', 'wasapi', None):
    synth = None
    label = driver or '(default)'
    print('\n=== TEST DRIVER:', label, '===', flush=True)
    try:
        synth = fluidsynth.Synth(gain=0.8)
        if driver is None:
            synth.start()
        else:
            synth.start(driver=driver)
        sfid = synth.sfload(sf)
        print('sfload result:', sfid, flush=True)
        if sfid is None or int(sfid) < 0:
            raise RuntimeError('SoundFont failed to load')
        synth.program_select(0, int(sfid), 0, 0)
        print('Сейчас должна прозвучать нота ЛЯ (A4) 3 секунды...', flush=True)
        synth.noteon(0, 69, 110)
        time.sleep(3)
        synth.noteoff(0, 69)
        time.sleep(0.5)
        print('Драйвер запущен. Если нота слышна — запомните драйвер.', flush=True)
    except Exception as e:
        print('ERROR:', repr(e), flush=True)
    finally:
        if synth is not None:
            try: synth.delete()
            except Exception: pass
print('\nПроверка завершена. Если не было звука ни на одном драйвере, пришлите весь текст окна.')
input('Enter для выхода...')
