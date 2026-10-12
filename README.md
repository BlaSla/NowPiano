# NowPiano

**PDF/MIDI sheet music player with real piano sound.**

Приложение для распознавания и воспроизведения нот из PDF и MIDI-файлов — всё в одном Setup, без внешних зависимостей.

## Возможности
- Распознавание нот из PDF — Audiveris (OMR)
- Воспроизведение MIDI — FluidSynth + SoundFont Arachno
- Qt-интерфейс, иконка пианино
- Play, Pause, Stop, Rewind, Loop
- BPM-регулятор 30..200
- Экспорт в MIDI
- Подсветка клавиш, нотный стан для MIDI
- Всё внутри: SoundFont, Audiveris (+JRE), poppler, FluidSynth, music21

## Установка
1. Скачайте NowPiano_Setup.exe (~427 МБ) со страницы Releases.
2. Запустите установщик (права администратора).
3. Установите в C:\Program Files\NowPiano\ (по умолчанию).
4. Запустите из меню Пуск или с ярлыка.

Ничего дополнительно устанавливать не нужно — Java, Audiveris, FluidSynth, poppler и SoundFont уже внутри.

## Сборка из исходников
Требования: Windows 10/11 x64, Python 3.11+, Inno Setup 6, PyInstaller.

Установка зависимостей:
pip install PyQt6 pyfluidsynth pdf2image Pillow music21 numpy mido

Запуск dev:
python C:\NowPiano\src\piano_qt.py

Сборка Setup:
cd C:\NowPiano
pyinstaller installer\NowPiano.spec --noconfirm --clean
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" C:\NowPiano\installer\NowPiano.iss

Результат: C:\NowPiano\dist\NowPiano_Setup.exe

## Лицензия
MIT License — см. LICENSE.txt

## Автор
Вячеслав Блажков
GitHub: https://github.com/BlaSla
Email: blazhkov1971@gmail.com