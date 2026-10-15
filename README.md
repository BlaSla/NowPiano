# NowPiano

**PDF/MIDI sheet music player with real piano sound.**

Приложение для распознавания и воспроизведения нот из PDF и MIDI-файлов — всё в одном Setup, без внешних зависимостей.

• Распознавание нот (OMR): Преобразование партитур из форматов PDF и JPG в цифровой вид с помощью движка Audiveris.
• Синтез и воспроизведение: Проигрывание MIDI-данных через FluidSynth с использованием встроенного банка звуков Arachno SoundFont.
• Управление плеером: Стандартные функции воспроизведения (Play, Pause, Stop), перемотка (Rewind), цикличный повтор (Loop), а также остановка и позиционирование с помощью ползунка таймлайна (индикатора прогресса).
• Регулировка темпа: Изменение BPM в диапазоне от 30 до 200. (Примечание: при распознавании из PDF/JPG темп может сбрасываться до 72 BPM; для решения проблемы экспортируйте трек в MIDI и откройте сохраненный файл).
• Интерактивная визуализация: Нотный стан для отображения текущей партитуры и подсветка клавиш на виртуальном пианино при воспроизведении MIDI.
• Интерактивная клавиатура: Виртуальная экранная клавиатура с возможностью интерактивного исполнения и ввода нот кликом мыши или нажатием клавиш.
• Экспорт: Сохранение распознанных или измененных композиций в стандартный формат MIDI.
• Современный интерфейс: Графическая оболочка на базе Qt с фирменной иконкой пианино.
• Всё включено (All-in-One): Программа поставляется со всеми необходимыми встроенными компонентами и зависимостями (SoundFont, Audiveris с JRE, poppler, FluidSynth, music21).


## Установка
1. Скачайте NowPiano_Setup_AllInOne_Final.exe (~850 MB) со страницы Releases.
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

Результат: NowPiano_Setup_AllInOne_Final.exe

## Лицензия
MIT License — см. LICENSE.txt

## Автор
Вячеслав Блажков Viacheslav Blazhkov
GitHub: https://github.com/BlaSla
Email: blazhkov1971@gmail.com
