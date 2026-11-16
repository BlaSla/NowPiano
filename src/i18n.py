# -*- coding: utf-8 -*-
"""Локализация NowPiano: ru (реализован), en, zh."""
from PyQt6.QtCore import QSettings

TRANSLATIONS = {
    "ru": {
        "settings": "Настройки", "language": "Язык", "bpm": "Темп (BPM)...",
        "keyboard_size": "Размер клавиатуры...", "training": "Тренировка",
        "midi_training": "MIDI-тренировка", "help": "Справка",
        "about": "О программе NowPiano", "player": "Проигрыватель",
        "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
        "file": "Файл", "score": "Партитура", "view": "Вид", "midi": "MIDI",
        "left_hand": "ЛЕВАЯ РУКА: —", "right_hand": "ПРАВАЯ РУКА: —",
        "recognition": "Распознавание: —", 
        "no_file": "Файл не загружен.\nНажми «Открыть файл».",
        "about_title": "О программе NowPiano", "midi_in_title": "Настройка MIDI-входа",
        "midi_out_title": "Настройка MIDI OUT", "recognition_pdf": "Распознавание PDF",
        "recognition_error": "Распознавание: ошибка", "recognition_notes": "Распознавание нот",
        "loading": "Идёт загрузка и распознавание файла.\nПожалуйста, подождите...",
        "recognizing": "Идёт распознавание нот",
    },
    "en": {
        "settings": "Settings", "language": "Language", "bpm": "Tempo (BPM)...",
        "keyboard_size": "Keyboard size...", "training": "Training",
        "midi_training": "MIDI training", "help": "Help",
        "about": "About NowPiano", "player": "Player",
        "lang_ru": "Russian", "lang_en": "English", "lang_zh": "Chinese",
        "file": "File", "score": "Score", "view": "View", "midi": "MIDI",
        "left_hand": "LEFT HAND: —", "right_hand": "RIGHT HAND: —",
        "recognition": "Recognition: —", 
        "no_file": "No file loaded.\nClick «Open file».",
        "about_title": "About NowPiano", "midi_in_title": "MIDI Input Settings",
        "midi_out_title": "MIDI OUT Settings", "recognition_pdf": "PDF Recognition",
        "recognition_error": "Recognition: error", "recognition_notes": "Note Recognition",
        "loading": "Loading and recognizing file.\nPlease wait...",
        "recognizing": "Recognizing notes",
    },
    "zh": {
        "settings": "设置", "language": "语言", "bpm": "速度 (BPM)...",
        "keyboard_size": "键盘尺寸...", "training": "训练",
        "midi_training": "MIDI 训练", "help": "帮助",
        "about": "关于 NowPiano", "player": "播放器",
        "lang_ru": "俄语", "lang_en": "英语", "lang_zh": "中文",
        "file": "文件", "score": "乐谱", "view": "视图", "midi": "MIDI",
        "left_hand": "左手: —", "right_hand": "右手: —",
        "recognition": "识别: —", 
        "no_file": "未加载文件。\n点击«打开文件»。",
        "about_title": "关于 NowPiano", "midi_in_title": "MIDI 输入设置",
        "midi_out_title": "MIDI OUT 设置", "recognition_pdf": "PDF 识别",
        "recognition_error": "识别: 错误", "recognition_notes": "音符识别",
        "loading": "正在加载并识别文件。\n请稍候...",
        "recognizing": "正在识别音符",
    },
}

_current = "ru"

def set_language(code: str):
    global _current
    if code in TRANSLATIONS:
        _current = code
        QSettings("NowPiano", "NowPiano").setValue("ui/language", code)

def get_language() -> str:
    return _current

def load_language():
    global _current
    s = QSettings("NowPiano", "NowPiano")
    code = s.value("ui/language", "ru", type=str)
    if code in TRANSLATIONS:
        _current = code

def tr(key: str) -> str:
    return TRANSLATIONS.get(_current, {}).get(key, key)
# --- Дополнительные ключи для интерфейса ---
EXTRA_KEYS = {
    "ru": {
        "digital_score": "ЦИФРОВАЯ ПАРТИТУРА", "load_pdf_midi": "Загрузите PDF или MIDI-файл",
        "error_processing": "Не удалось обработать файл.\nВыберите другой файл.",
        "error_image": "Не удалось распознать картинку.\nПопробуйте другой файл.",
        "error_notes": "Ни Audiveris, ни homr не смогли распознать ноты.\nПопробуйте другой файл.",
        "status_ready": "Готов. Нажми «Открыть».",
        "status_loading": "Загрузка: {name}",
        "status_kar": "KAR: загрузка караоке", "status_midi": "MIDI: загрузка",
        "status_pdf_render": "Шаг 1/3: рендер PDF...", "status_image_homr": "Картинка — распознаю через homr...",
        "status_homr_fail": "homr не справился — конвертирую в PDF и пробую Audiveris...",
        "status_audiveris": "Шаг 2/3: Audiveris распознаёт (может занять минуты)...",
        "status_audiveris_fail": "Audiveris не справился — пробую homr...",
        "status_musicxml": "Шаг 3/3: разбор MusicXML...",
        "tooltip_record": "Начать запись", "tooltip_bpm": "Темп воспроизведения",
        "tooltip_bpm_song": "Темп песни (BPM)",
        "file_dialog_open": "Открыть", "file_filter_all": "Все файлы (*.*)",
        "warning_soundfont": "Внимание: звук не инициализирован. Проверь SoundFont: {path}",
    },
    "en": {
        "digital_score": "DIGITAL SCORE", "load_pdf_midi": "Load PDF or MIDI file",
        "error_processing": "Failed to process file.\nChoose another file.",
        "error_image": "Failed to recognize image.\nTry another file.",
        "error_notes": "Neither Audiveris nor homr could recognize notes.\nTry another file.",
        "status_ready": "Ready. Click «Open».",
        "status_loading": "Loading: {name}",
        "status_kar": "KAR: loading karaoke", "status_midi": "MIDI: loading",
        "status_pdf_render": "Step 1/3: rendering PDF...", "status_image_homr": "Image — recognizing via homr...",
        "status_homr_fail": "homr failed — converting to PDF and trying Audiveris...",
        "status_audiveris": "Step 2/3: Audiveris recognizing (may take minutes)...",
        "status_audiveris_fail": "Audiveris failed — trying homr...",
        "status_musicxml": "Step 3/3: parsing MusicXML...",
        "tooltip_record": "Start recording", "tooltip_bpm": "Playback tempo",
        "tooltip_bpm_song": "Song tempo (BPM)",
        "file_dialog_open": "Open", "file_filter_all": "All files (*.*)",
        "warning_soundfont": "Warning: audio not initialized. Check SoundFont: {path}",
    },
    "zh": {
        "digital_score": "数字乐谱", "load_pdf_midi": "加载 PDF 或 MIDI 文件",
        "error_processing": "处理文件失败。\n请选择其他文件。",
        "error_image": "无法识别图片。\n请尝试其他文件。",
        "error_notes": "Audiveris 和 homr 均无法识别音符。\n请尝试其他文件。",
        "status_ready": "就绪。点击«打开»。",
        "status_loading": "加载中: {name}",
        "status_kar": "KAR: 加载卡拉OK", "status_midi": "MIDI: 加载中",
        "status_pdf_render": "步骤 1/3: 渲染 PDF...", "status_image_homr": "图片 — 通过 homr 识别...",
        "status_homr_fail": "homr 失败 — 转换为 PDF 并尝试 Audiveris...",
        "status_audiveris": "步骤 2/3: Audiveris 识别中（可能需要几分钟）...",
        "status_audiveris_fail": "Audiveris 失败 — 尝试 homr...",
        "status_musicxml": "步骤 3/3: 解析 MusicXML...",
        "tooltip_record": "开始录制", "tooltip_bpm": "播放速度",
        "tooltip_bpm_song": "歌曲速度 (BPM)",
        "file_dialog_open": "打开", "file_filter_all": "所有文件 (*.*)",
        "warning_soundfont": "警告: 音频未初始化。请检查 SoundFont: {path}",
    },
}

for lang in ("ru", "en", "zh"):
    if lang in TRANSLATIONS:
        TRANSLATIONS[lang].update(EXTRA_KEYS[lang])
# --- Финальные ключи для интерфейса ---
FINAL_KEYS = {
    "ru": {
        "central_no_file": "Файл не загружен.\nНажми «Открыть файл».",
        "menu_open": "Открыть...", "menu_export_midi": "Экспорт MIDI",
        "menu_export_pdf": "Сохранить партитуру PDF...",
        "recognized_events": "Ноты распознаны: {n} событий",
        "midi_events": "MIDI: {n} событий",
        "pdf_preparing": "PDF: подготовка", "parsing_notes": "Разбор нот",
        "tooltip_pause": "Пауза", "tooltip_play": "Воспроизвести",
        "midi_connected": "Подключено: {name}",
        "midi_connect_fail": "Не удалось подключить MIDI",
        "midi_not_connected": "MIDI не подключён",
    },
    "en": {
        "central_no_file": "No file loaded.\nClick «Open file».",
        "menu_open": "Open...", "menu_export_midi": "Export MIDI",
        "menu_export_pdf": "Save score as PDF...",
        "recognized_events": "Notes recognized: {n} events",
        "midi_events": "MIDI: {n} events",
        "pdf_preparing": "PDF: preparing", "parsing_notes": "Parsing notes",
        "tooltip_pause": "Pause", "tooltip_play": "Play",
        "midi_connected": "Connected: {name}",
        "midi_connect_fail": "Failed to connect MIDI",
        "midi_not_connected": "MIDI not connected",
    },
    "zh": {
        "central_no_file": "未加载文件。\n点击«打开文件»。",
        "menu_open": "打开...", "menu_export_midi": "导出 MIDI",
        "menu_export_pdf": "将乐谱保存为 PDF...",
        "recognized_events": "音符已识别: {n} 个事件",
        "midi_events": "MIDI: {n} 个事件",
        "pdf_preparing": "PDF: 准备中", "parsing_notes": "解析音符",
        "tooltip_pause": "暂停", "tooltip_play": "播放",
        "midi_connected": "已连接: {name}",
        "midi_connect_fail": "MIDI 连接失败",
        "midi_not_connected": "MIDI 未连接",
    },
}

for lang in ("ru", "en", "zh"):
    if lang in TRANSLATIONS:
        TRANSLATIONS[lang].update(FINAL_KEYS[lang])
# --- Пункты меню MIDI ---
MIDI_KEYS = {
    "ru": {
        "midi_in_connecting": "MIDI IN: подключение...",
        "midi_out_connecting": "MIDI OUT: подключение...",
        "midi_start_recording": "Начать запись исполнения",
        "midi_pause_resume": "Пауза / продолжить запись",
        "midi_stop_recording": "Завершить запись",
        "midi_save_recording": "Сохранить MIDI-запись...",
    },
    "en": {
        "midi_in_connecting": "MIDI IN: connecting...",
        "midi_out_connecting": "MIDI OUT: connecting...",
        "midi_start_recording": "Start recording performance",
        "midi_pause_resume": "Pause / resume recording",
        "midi_stop_recording": "Stop recording",
        "midi_save_recording": "Save MIDI recording...",
    },
    "zh": {
        "midi_in_connecting": "MIDI IN: 连接中...",
        "midi_out_connecting": "MIDI OUT: 连接中...",
        "midi_start_recording": "开始录制演奏",
        "midi_pause_resume": "暂停 / 继续录制",
        "midi_stop_recording": "停止录制",
        "midi_save_recording": "保存 MIDI 录音...",
    },
}

for lang in ("ru", "en", "zh"):
    if lang in TRANSLATIONS:
        TRANSLATIONS[lang].update(MIDI_KEYS[lang])
# --- Последние ключи для меню Score/View ---
LAST_KEYS = {
    "ru": {
        "export_score_pdf": "Экспорт открытой партитуры в PDF...",
        "digital_score_view": "Цифровая партитура",
        "pdf_image_view": "PDF/изображение",
    },
    "en": {
        "export_score_pdf": "Export open score to PDF...",
        "digital_score_view": "Digital score",
        "pdf_image_view": "PDF/Image",
    },
    "zh": {
        "export_score_pdf": "导出当前乐谱为 PDF...",
        "digital_score_view": "数字乐谱",
        "pdf_image_view": "PDF/图片",
    },
}

for lang in ("ru", "en", "zh"):
    if lang in TRANSLATIONS:
        TRANSLATIONS[lang].update(LAST_KEYS[lang])
# --- MIDI OUT: не выбран выход ---
TRANSLATIONS["ru"]["midi_out_not_selected"] = "Не выбран MIDI-выход."
TRANSLATIONS["en"]["midi_out_not_selected"] = "No MIDI output selected."
TRANSLATIONS["zh"]["midi_out_not_selected"] = "未选择 MIDI 输出。"
# --- Принудительное добавление ключей MIDI (OUT и кнопки) ---
TRANSLATIONS["ru"]["midi_out_not_connected"] = "MIDI OUT не подключён"
TRANSLATIONS["en"]["midi_out_not_connected"] = "MIDI OUT not connected"
TRANSLATIONS["zh"]["midi_out_not_connected"] = "MIDI OUT 未连接"

TRANSLATIONS["ru"]["midi_connect_btn"] = "Подключить"
TRANSLATIONS["en"]["midi_connect_btn"] = "Connect"
TRANSLATIONS["zh"]["midi_connect_btn"] = "连接"

TRANSLATIONS["ru"]["midi_disconnect_btn"] = "Отключить"
TRANSLATIONS["en"]["midi_disconnect_btn"] = "Disconnect"
TRANSLATIONS["zh"]["midi_disconnect_btn"] = "断开"

TRANSLATIONS["ru"]["midi_close_btn"] = "Закрыть"
TRANSLATIONS["en"]["midi_close_btn"] = "Close"
TRANSLATIONS["zh"]["midi_close_btn"] = "关闭"

TRANSLATIONS["ru"]["midi_out_select_device"] = "Выберите MIDI-устройство для вывода:"
TRANSLATIONS["en"]["midi_out_select_device"] = "Select MIDI output device:"
TRANSLATIONS["zh"]["midi_out_select_device"] = "选择 MIDI 输出设备:"

TRANSLATIONS["ru"]["midi_out_not_selected"] = "Не выбран MIDI-выход."
TRANSLATIONS["en"]["midi_out_not_selected"] = "No MIDI output selected."
TRANSLATIONS["zh"]["midi_out_not_selected"] = "未选择 MIDI 输出。"
# --- Принудительное обновление ключей MIDI OUT ---
TRANSLATIONS["ru"]["midi_out_select_device"] = "Выберите MIDI-устройство для вывода:"
TRANSLATIONS["en"]["midi_out_select_device"] = "Select MIDI output device:"
TRANSLATIONS["zh"]["midi_out_select_device"] = "选择 MIDI 输出设备:"

TRANSLATIONS["ru"]["midi_out_not_connected"] = "MIDI OUT не подключён"
TRANSLATIONS["en"]["midi_out_not_connected"] = "MIDI OUT not connected"
TRANSLATIONS["zh"]["midi_out_not_connected"] = "MIDI OUT 未连接"

TRANSLATIONS["ru"]["midi_connect_btn"] = "Подключить"
TRANSLATIONS["en"]["midi_connect_btn"] = "Connect"
TRANSLATIONS["zh"]["midi_connect_btn"] = "连接"

TRANSLATIONS["ru"]["midi_disconnect_btn"] = "Отключить"
TRANSLATIONS["en"]["midi_disconnect_btn"] = "Disconnect"
TRANSLATIONS["zh"]["midi_disconnect_btn"] = "断开"

TRANSLATIONS["ru"]["midi_close_btn"] = "Закрыть"
TRANSLATIONS["en"]["midi_close_btn"] = "Close"
TRANSLATIONS["zh"]["midi_close_btn"] = "关闭"