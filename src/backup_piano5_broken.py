# -*- coding: utf-8 -*-
"""piano5.py - проигрыватель нот из PDF. Все ноты с буквами + звук MuseScore."""

import sys, os
if getattr(sys, 'frozen', False):
    if sys.stdout is None: sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None: sys.stderr = open(os.devnull, 'w')

import threading, time, math, array, subprocess, pygame
from tkinter import Tk, filedialog
from music21 import converter

try:
    import cv2, numpy as np
except ImportError:
    cv2 = None; np = None

try:
    import fluidsynth
    FLUID_IMPORT_OK = True
except ImportError:
    FLUID_IMPORT_OK = False

FLUID_AVAILABLE = False
fs = None
SFID = None
SOUNDFONT_PATH = r"C:\tools\fluidsynth\soundfonts\FluidR3_GM.sf2"
FLUID_DRIVER = "waveout"
FLUID_GAIN = 1.5
NOTE_TAIL = 1.35
RIGHT_VEL = 100
LEFT_VEL = 70

LETTERS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Цвета
LETTER_COLOR_R = (0, 160, 0)
LETTER_COLOR_L = (0, 120, 180)
PLAYING_COLOR_R = (60, 220, 120)
PLAYING_COLOR_L = (80, 200, 230)


def get_short_note_name(midi_pitch):
    return LETTERS[midi_pitch % 12]


def init_fluidsynth():
    global FLUID_AVAILABLE, fs, SFID
    if not FLUID_IMPORT_OK:
        print("pyfluidsynth not installed"); return
    try:
        fs = fluidsynth.Synth()
        fs.setting('audio.driver', FLUID_DRIVER)
        fs.setting('synth.gain', FLUID_GAIN)
        fs.start()
        SFID = fs.sfload(SOUNDFONT_PATH)
        fs.program_select(0, SFID, 0, 0)
        FLUID_AVAILABLE = True
        print("FluidSynth ready:", FLUID_DRIVER)
    except Exception as e:
        FLUID_AVAILABLE = False
        print("FluidSynth failed:", e)


def _piano_wave_samples(freq, duration, sample_rate=44100):
    n = max(1, int(sample_rate * duration))
    buf = array.array('h', [0]) * n
    w = 2.0 * math.pi * freq
    for i in range(n):
        t = i / sample_rate
        buf[i] = int(32767 * math.exp(-4 * t) * math.sin(w * t))
    return buf


_SOUND_CACHE = {}
def _get_sound(midi_note, duration):
    key = (midi_note, round(duration, 2))
    snd = _SOUND_CACHE.get(key)
    if snd is not None: return snd
    freq = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
    buf = _piano_wave_samples(freq, max(0.6, duration + 0.3))
    snd = pygame.mixer.Sound(buffer=buf.tobytes())
    if len(_SOUND_CACHE) > 200: _SOUND_CACHE.clear()
    _SOUND_CACHE[key] = snd
    return snd


AUDIVERIS_EXE = r"C:\Program Files\Audiveris\Audiveris.exe"
OMR_OUTPUT_DIR = r"C:\out_omr"
MANUAL_BPM = 72.0
BPM_MIN, BPM_MAX = 30, 200

WHITE=(255,255,255); BLACK=(0,0,0); GRAY=(220,220,220); DARK_GRAY=(40,40,40)
BLUE=(51,153,255); RED=(255,87,87); GREEN=(46,204,113); YELLOW=(241,196,15)
ORANGE=(230,126,34); CYAN=(60,200,220)
BTN_GREEN=(46,204,113); BTN_YELLOW=(241,196,15); BTN_RED=(231,76,60)
BTN_GRAY=(200,200,200); BTN_BLUE=(52,152,219)

WIN_W, WIN_H = 1400, 800
TOPBAR_H = 60
KEYBOARD_H = 140
MIN_W, MIN_H = 900, 600
START_NOTE, NUM_KEYS = 21, 88

active_notes = set()
is_processing = False
status_text = "Нажмите Открыть PDF"
detected_melody = []
current_playing_note_name = ""
current_bar_display = ""
current_bpm_display = ""
stop_flag = threading.Event()
pause_flag = threading.Event()
play_thread = None
pdf_pages = []
pdf_current_page = 0
pdf_scroll_y = 0
# Карта: (page_idx, event_idx) -> [(x, y, letter, hand)]
note_labels = {}
# Карта: event_idx -> (page_idx, x, y) - центр играющего аккорда
playing_centers = {}
current_event_index = -1
current_bpm = MANUAL_BPM
is_fullscreen = False
screen = None
buttons = []
slider_rect = pygame.Rect(0, 0, 0, 0)
dragging_slider = False


def is_black_key(note):
    return ((note - 12) % 12) in (1, 3, 6, 8, 10)


def get_note_name(midi_pitch):
    names = ["C (До)","C# (До#)","D (Ре)","D# (Ре#)","E (Ми)","F (Фа)",
             "F# (Фа#)","G (Соль)","G# (Соль#)","A (Ля)","A# (Ля#)","B (Си)"]
    return names[midi_pitch % 12]


def _render_pdf_to_surfaces(pdf_path, dpi=150, max_pages=10):
    from pdf2image import convert_from_path
    images = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=max_pages)
    surfaces = []
    for img in images:
        arr = img.convert("RGB")
        surfaces.append(pygame.image.fromstring(arr.tobytes(), arr.size, "RGB"))
    return surfaces


def _run_audiveris(pdf_path):
    os.makedirs(OMR_OUTPUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    for ext in (".mxl", ".xml", ".musicxml"):
        c = os.path.join(OMR_OUTPUT_DIR, base + ext)
        if os.path.exists(c): return c
    cmd = [AUDIVERIS_EXE, "-batch", "-transcribe", "-export",
           "-output", OMR_OUTPUT_DIR, "--", pdf_path]
    subprocess.run(cmd, check=True, capture_output=True, timeout=900)
    for ext in (".mxl", ".xml", ".musicxml"):
        c = os.path.join(OMR_OUTPUT_DIR, base + ext)
        if os.path.exists(c): return c
    for f in os.listdir(OMR_OUTPUT_DIR):
        if f.startswith(base) and f.lower().endswith((".mxl", ".xml", ".musicxml")):
            return os.path.join(OMR_OUTPUT_DIR, f)
    raise RuntimeError("Audiveris did not create MusicXML")


def _musicxml_to_events(mxl_path):
    score = converter.parse(mxl_path)
    bpm = MANUAL_BPM
    marks = score.metronomeMarkBoundaries()
    if marks:
        try: bpm = float(marks[0][2].number)
        except: pass
    if bpm > 110 and abs(bpm - MANUAL_BPM) > 20: bpm = MANUAL_BPM
    spq = 60.0 / bpm
    used_parts = [p for p in score.parts if len(list(p.flatten().notes)) > 0]
    if not used_parts: raise RuntimeError("No notes")
    events = []
    for part_idx, part in enumerate(used_parts):
        hand = "R" if part_idx == 0 else "L"
        for el in part.flatten().notesAndRests:
            dur_q = float(el.quarterLength)
            if dur_q <= 0: continue
            offset_q = float(el.offset)
            try: bar = int(el.measureNumber) if el.measureNumber else 0
            except: bar = 0
            if hasattr(el, "pitches") and len(el.pitches) > 0:
                midis = sorted(p.midi for p in el.pitches)
                midis = [m for m in midis if START_NOTE <= m <= START_NOTE + NUM_KEYS - 1]
                if midis:
                    events.append({"bar": bar, "offset_q": offset_q,
                                   "time_seconds": offset_q * spq,
                                   "notes": midis,
                                   "duration": max(0.05, dur_q * spq),
                                   "hand": hand})
    events.sort(key=lambda e: e["time_seconds"])
    merged = []
    for ev in events:
        if merged:
            last = merged[-1]
            if abs(ev["time_seconds"] - last["time_seconds"]) < 0.02:
                last["notes"] = sorted(set(last["notes"]) | set(ev["notes"]))
                last["duration"] = max(last["duration"], ev["duration"])
                continue
        merged.append(dict(ev))
    if merged:
        t0 = merged[0]["time_seconds"]
        o0 = merged[0]["offset_q"]
        if t0 > 0.05:
            for ev in merged:
                ev["time_seconds"] -= t0
                ev["offset_q"] -= o0
    return merged, bpm, len(used_parts)


def _detect_staves(surf):
    """Возвращает список диапазонов Y для каждого стана (5 линеек)."""
    if cv2 is None or np is None: return []
    w, h = surf.get_size()
    raw = pygame.image.tostring(surf, "RGB")
    img = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Горизонтальные линии
    horiz = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_RECT, (w//10, 1)))
    row_sum = np.sum(horiz > 0, axis=1)
    thresh = max(20, w // 8)
    rows = [y for y in range(h) if row_sum[y] > thresh]
    # Группируем в станы (5 линий, близких друг к другу)
    staves = []
    if not rows: return staves
    group = [rows[0]]
    for y in rows[1:]:
        if y - group[-1] <= 4: group.append(y)
        else:
            if len(group) >= 4:
                staves.append((min(group), max(group)))
            group = [y]
    if len(group) >= 4:
        staves.append((min(group), max(group)))
    return staves


def _detect_barlines_for_staff(surf, staff_top, staff_bottom):
    """Ищет вертикальные тактовые линии внутри стана. Возвращает список X-координат."""
    if cv2 is None or np is None: return []
    w, h = surf.get_size()
    raw = pygame.image.tostring(surf, "RGB")
    img = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Ограничиваем полосой стана
    y0 = max(0, staff_top - 2); y1 = min(h, staff_bottom + 3)
    strip = binary[y0:y1, :]
    height = y1 - y0
    # Вертикальная морфология
    vert = cv2.morphologyEx(strip, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(5, height - 6))))
    col_sum = np.sum(vert > 0, axis=0)
    thr = height * 0.65
    cols = [x for x in range(w) if col_sum[x] > thr]
    # Группируем близкие столбцы
    groups = []
    if not cols: return groups
    g = [cols[0]]
    for x in cols[1:]:
        if x - g[-1] <= 4: g.append(x)
        else:
            groups.append(int(sum(g) / len(g))); g = [x]
    groups.append(int(sum(g) / len(g)))
    return groups


def _build_note_labels(pdf_surfaces):
    """Для каждой страницы находит станы, тактовые линии и распределяет события по тактам."""
    global note_labels, playing_centers
    note_labels = {}
    playing_centers = {}
    if not pdf_surfaces or not detected_melody: return

    # Группируем события по такту
    events_by_bar = {}
    for idx, ev in enumerate(detected_melody):
        bar = ev.get("bar", 0)
        events_by_bar.setdefault(bar, []).append(idx)

    # Проходим по каждой странице, находим станы и бары
    all_bars_sorted = sorted(events_by_bar.keys())
    bars_per_page = max(1, len(all_bars_sorted) // max(1, len(pdf_surfaces)))

    for pg_idx, surf in enumerate(pdf_surfaces):
        pw, ph = surf.get_size()
        staves = _detect_staves(surf)
        if not staves: continue

        # Какие такты на этой странице
        bar_start = pg_idx * bars_per_page
        bar_end = bar_start + bars_per_page
        page_bars = [b for b in all_bars_sorted if bar_start <= b < bar_end]
        if not page_bars:
            # fallback: все такты страницы
            total = len(all_bars_sorted)
            bar_start = int(pg_idx * total / len(pdf_surfaces))
            bar_end = int((pg_idx + 1) * total / len(pdf_surfaces))
            page_bars = all_bars_sorted[bar_start:bar_end]

        # Находим бары в каждом стане
        for staff_top, staff_bottom in staves:
            barlines = _detect_barlines_for_staff(surf, staff_top, staff_bottom)
            if len(barlines) < 2: continue

            # Каждому бару стана - свой X-диапазон
            n_bars_in_staff = len(barlines) - 1
            # Распределяем бары страницы по станам
            staff_share = max(1, len(page_bars) // max(1, len(staves)))
            staff_bars = page_bars[:staff_share]
            page_bars = page_bars[staff_share:]

            for k, bar in enumerate(staff_bars):
                if k >= n_bars_in_staff: break
                x_left = barlines[k]
                x_right = barlines[k + 1]
                y_mid = (staff_top + staff_bottom) // 2

                # События этого бара
                evs = events_by_bar.get(bar, [])
                if not evs: continue
                # Распределяем события внутри такта по X
                n_ev = len(evs)
                for i, ev_idx in enumerate(evs):
                    ev = detected_melody[ev_idx]
                    frac = (i + 0.5) / n_ev
                    x_center = int(x_left + frac * (x_right - x_left))
                    y_center = y_mid
                    # Для каждой ноты события - буква
                    letters = [get_short_note_name(m) for m in ev["notes"]]
                    hand = ev.get("hand", "R")
                    note_labels[(pg_idx, ev_idx)] = (x_center, y_center, letters, hand)
                    playing_centers[ev_idx] = (pg_idx, x_center, y_center)


def _note_off_later(midi_note, delay):
    def _off():
        try:
            if FLUID_AVAILABLE: fs.noteoff(0, midi_note)
        except Exception: pass
        active_notes.discard(midi_note)
    threading.Timer(delay, _off).start()


def play_music_logic():
    global current_playing_note_name, status_text, current_bar_display
    global current_event_index, pdf_current_page
    if not detected_melody:
        status_text = "Нет нот"; return
    status_text = "Воспроизведение..."
    speed = MANUAL_BPM / max(1.0, current_bpm)
    t0 = time.time()
    for idx, ev in enumerate(detected_melody):
        if stop_flag.is_set(): break
        while pause_flag.is_set() and not stop_flag.is_set():
            time.sleep(0.05)
        if stop_flag.is_set(): break
        t_start = t0 + float(ev.get("time_seconds", 0.0)) * speed
        wait = t_start - time.time()
        while wait > 0:
            if stop_flag.is_set(): break
            if pause_flag.is_set():
                time.sleep(0.05); t0 += 0.05
                t_start = t0 + float(ev.get("time_seconds", 0.0)) * speed
                wait = t_start - time.time(); continue
            time.sleep(min(0.02, wait)); wait = t_start - time.time()
        if stop_flag.is_set(): break
        notes = ev.get("notes", [])
        dur = float(ev.get("duration", 0.4)) * speed
        dur_play = dur * NOTE_TAIL
        current_event_index = idx
        if notes:
            names = []
            velocity = RIGHT_VEL if ev.get("hand", "R") == "R" else LEFT_VEL
            for n in notes:
                try:
                    active_notes.add(n)
                    names.append(get_note_name(n))
                    if FLUID_AVAILABLE:
                        fs.noteon(0, n, velocity)
                        _note_off_later(n, dur_play)
                    else:
                        _get_sound(n, dur).play()
                except: pass
            current_playing_note_name = " + ".join(names)
        current_bar_display = "Такт " + str(ev.get("bar", 0))
        # Авто-переключение на страницу играющего события
        if idx in playing_centers:
            pdf_current_page = playing_centers[idx][0]
    time.sleep(1.5)
    current_playing_note_name = ""
    current_bar_display = ""
    current_event_index = -1
    status_text = "Готово!" if not stop_flag.is_set() else "Остановлено."


def _stop_playback_if_any():
    global play_thread
    stop_flag.set(); pause_flag.clear()
    if play_thread is not None and play_thread.is_alive():
        play_thread.join(timeout=2.0)
    stop_flag.clear(); play_thread = None


def _clear_document():
    global detected_melody, pdf_pages, note_labels, playing_centers, pdf_current_page
    global pdf_scroll_y, current_event_index, current_playing_note_name, current_bar_display
    detected_melody = []; pdf_pages = []; note_labels = {}; playing_centers = {}
    pdf_current_page = 0; pdf_scroll_y = 0; current_event_index = -1
    current_playing_note_name = ""; current_bar_display = ""
    active_notes.clear()


def process_pdf_to_notes(pdf_path):
    global is_processing, detected_melody, status_text, current_bpm_display
    global pdf_pages, pdf_current_page, pdf_scroll_y, current_bpm
    _stop_playback_if_any(); _clear_document()
    is_processing = True
    try:
        status_text = "Рендер PDF..."
        try: pdf_pages = _render_pdf_to_surfaces(pdf_path, dpi=150)
        except Exception: pdf_pages = []
        pdf_current_page = 0; pdf_scroll_y = 0
        status_text = "Audiveris распознаёт..."
        mxl_path = _run_audiveris(pdf_path)
        status_text = "Парсинг MusicXML..."
        events, bpm, n_parts = _musicxml_to_events(mxl_path)
        if not events: raise RuntimeError("No events")
        detected_melody = events; current_bpm = bpm
        total_notes = sum(len(e["notes"]) for e in events)
        current_bpm_display = "BPM: " + str(int(bpm))
        status_text = "Поиск тактов и позиций нот..."
        _build_note_labels(pdf_pages)
        status_text = "Готово: " + str(total_notes) + " нот. Нажмите Играть."
        is_processing = False
    except Exception as e:
        status_text = "Ошибка: " + str(e)[:200]; is_processing = False


def open_file_dialog_thread():
    global status_text
    try:
        root = Tk(); root.withdraw(); root.attributes('-topmost', True)
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf"), ("All", "*.*")])
        root.destroy()
        if path:
            threading.Thread(target=process_pdf_to_notes, args=(path,), daemon=True).start()
    except Exception as e:
        status_text = "Ошибка: " + str(e)


class Button:
    def __init__(self, rect, text, color, action):
        self.rect = pygame.Rect(rect); self.text = text; self.color = color
        self.action = action; self.hover = False
    def draw(self, screen, font):
        c = self.color
        if self.hover: c = tuple(min(255, v + 25) for v in c)
        pygame.draw.rect(screen, c, self.rect, border_radius=6)
        pygame.draw.rect(screen, BLACK, self.rect, 2, border_radius=6)
        txt = font.render(self.text, True, BLACK)
        screen.blit(txt, (self.rect.x + (self.rect.w - txt.get_width()) // 2,
                          self.rect.y + (self.rect.h - txt.get_height()) // 2))
    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            self.action(); return True
        return False


def action_open_pdf():
    if is_processing: return
    threading.Thread(target=open_file_dialog_thread, daemon=True).start()

def action_play():
    global play_thread
    if is_processing or not detected_melody: return
    _stop_playback_if_any()
    stop_flag.clear(); pause_flag.clear()
    play_thread = threading.Thread(target=play_music_logic, daemon=True)
    play_thread.start()

def action_pause():
    if pause_flag.is_set(): pause_flag.clear()
    else: pause_flag.set()

def action_stop():
    stop_flag.set(); pause_flag.clear()
    if FLUID_AVAILABLE:
        try:
            for n in list(active_notes): fs.noteoff(0, n)
        except: pass
    active_notes.clear()

def action_toggle_fullscreen():
    global is_fullscreen, screen
    is_fullscreen = not is_fullscreen
    if is_fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
    _rebuild_buttons()


def _rebuild_buttons():
    global buttons, slider_rect
    w, _ = screen.get_size()
    bw, bh = 155, 36; gap = 8
    y = (TOPBAR_H - bh) // 2
    buttons = [
        Button((15, y, bw, bh), "Открыть PDF", BTN_GRAY, action_open_pdf),
        Button((15 + (bw + gap) * 1, y, bw, bh), "Играть", BTN_GREEN, action_play),
        Button((15 + (bw + gap) * 2, y, bw, bh), "Пауза", BTN_YELLOW, action_pause),
        Button((15 + (bw + gap) * 3, y, bw, bh), "Стоп", BTN_RED, action_stop),
        Button((15 + (bw + gap) * 4, y, bw, bh), "Полный экран", BTN_BLUE, action_toggle_fullscreen),
    ]
    sw = 200
    slider_rect = pygame.Rect(w - sw - 140, TOPBAR_H // 2 - 10, sw, 20)


def draw_topbar(screen, font):
    w, _ = screen.get_size()
    pygame.draw.rect(screen, (30, 30, 30), pygame.Rect(0, 0, w, TOPBAR_H))
    pygame.draw.line(screen, GRAY, (0, TOPBAR_H), (w, TOPBAR_H), 2)
    for b in buttons: b.draw(screen, font)
    sy = TOPBAR_H // 2
    pygame.draw.rect(screen, GRAY, pygame.Rect(slider_rect.x, sy - 3, slider_rect.w, 6), border_radius=3)
    frac = (current_bpm - BPM_MIN) / (BPM_MAX - BPM_MIN)
    kx = slider_rect.x + int(frac * slider_rect.w)
    pygame.draw.circle(screen, ORANGE, (kx, sy), 10)
    pygame.draw.circle(screen, BLACK, (kx, sy), 10, 2)
    screen.blit(font.render("BPM: " + str(int(current_bpm)), True, WHITE),
                (slider_rect.x + slider_rect.w + 15, sy - 12))


def draw_pdf(screen, letter_font, big_letter_font):
    w, h = screen.get_size()
    pdf_y0 = TOPBAR_H
    pdf_h = h - TOPBAR_H - KEYBOARD_H
    pygame.draw.rect(screen, (20, 20, 20), pygame.Rect(0, pdf_y0, w, pdf_h))
    if not pdf_pages:
        screen.blit(pygame.font.SysFont("Arial", 22).render("PDF не загружен", True, GRAY),
                    (40, pdf_y0 + 40))
        return
    page = pdf_pages[pdf_current_page]
    pw, ph = page.get_size()
    scale = w / pw
    scaled = pygame.transform.smoothscale(page, (int(pw * scale), int(ph * scale)))
    y_off = pdf_y0 - pdf_scroll_y
    screen.blit(scaled, (0, y_off))

    # --- Рисуем буквы ВСЕХ нот (кроме играющей — её отдельно) ---
    for (pg_idx, ev_idx), (x, y, letters, hand) in note_labels.items():
        if pg_idx != pdf_current_page: continue
        if ev_idx == current_event_index: continue  # играющую рисуем отдельно
        dx = int(x * scale); dy = int(y * scale) + y_off
        color = LETTER_COLOR_R if hand == "R" else LETTER_COLOR_L
        text = "-".join(letters)
        txt = letter_font.render(text, True, color)
        screen.blit(txt, (dx - txt.get_width() // 2, dy - txt.get_height() // 2))

    # --- Играющая нота: кружок + буквы белым ---
    if current_event_index >= 0 and current_event_index in playing_centers:
        pg_idx, x, y = playing_centers[current_event_index]
        if pg_idx == pdf_current_page:
            dx = int(x * scale); dy = int(y * scale) + y_off
            ev = detected_melody[current_event_index]
            hand = ev.get("hand", "R")
            color = PLAYING_COLOR_R if hand == "R" else PLAYING_COLOR_L
            letters = [get_short_note_name(m) for m in ev["notes"]]
            text = "-".join(letters)
            # Кружок
            pygame.draw.circle(screen, color, (dx, dy), 22)
            pygame.draw.circle(screen, WHITE, (dx, dy), 22, 2)
            # Буквы внутри
            txt = big_letter_font.render(text, True, WHITE)
            screen.blit(txt, (dx - txt.get_width() // 2, dy - txt.get_height() // 2))


def draw_keyboard(screen, letter_font):
    w, h = screen.get_size()
    kb_y = h - KEYBOARD_H
    pygame.draw.rect(screen, (25, 25, 25), pygame.Rect(0, kb_y, w, KEYBOARD_H))
    wc = sum(1 for n in range(START_NOTE, START_NOTE + NUM_KEYS) if not is_black_key(n))
    kw = w / wc; kh = KEYBOARD_H - 10
    idx = 0; n2x = {}
    for n in range(START_NOTE, START_NOTE + NUM_KEYS):
        if not is_black_key(n):
            x = idx * kw
            pygame.draw.rect(screen, BLUE if n in active_notes else WHITE,
                             pygame.Rect(x, kb_y + 5, kw - 1, kh))
            if n % 12 == 0:  # подписываем каждую C
                txt = letter_font.render(get_short_note_name(n), True, BLACK)
                screen.blit(txt, (x + kw // 2 - txt.get_width() // 2, kb_y + kh - 18))
            n2x[n] = x; idx += 1
    for n in range(START_NOTE, START_NOTE + NUM_KEYS):
        if is_black_key(n):
            px = n2x.get(n - 1); nx = n2x.get(n + 1)
            x = (px + kw * 0.7) if px is not None else (nx - kw * 0.3)
            pygame.draw.rect(screen, RED if n in active_notes else BLACK,
                             pygame.Rect(x, kb_y + 5, kw * 0.6, kh * 0.6))


def draw_interface(screen, font, large_font, small_font, letter_font, big_letter_font):
    screen.fill(DARK_GRAY)
    draw_topbar(screen, font)
    screen.blit(font.render(status_text, True, WHITE), (20, TOPBAR_H + 6))
    if current_playing_note_name:
        screen.blit(large_font.render("Играет: " + current_playing_note_name, True, GREEN),
                    (20, TOPBAR_H + 36))
    if current_bar_display:
        screen.blit(small_font.render(current_bar_display, True, YELLOW), (20, TOPBAR_H + 74))
    if is_processing:
        w, _ = screen.get_size()
        pygame.draw.circle(screen, ORANGE, (w - 40, TOPBAR_H + 30), 10)
    draw_pdf(screen, letter_font, big_letter_font)
    draw_keyboard(screen, letter_font)


def main():
    global screen, current_bpm, pdf_scroll_y, is_fullscreen
    global WIN_W, WIN_H, dragging_slider
    init_fluidsynth()
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
    pygame.display.set_caption("Piano Reader v8 - все ноты с буквами")
    font = pygame.font.SysFont("Arial", 20)
    large_font = pygame.font.SysFont("Arial", 26, bold=True)
    small_font = pygame.font.SysFont("Arial", 16)
    letter_font = pygame.font.SysFont("Arial", 13, bold=True)
    big_letter_font = pygame.font.SysFont("Arial", 16, bold=True)
    _rebuild_buttons()
    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():

$code = @'
# -*- coding: utf-8 -*-
"""piano5.py - проигрыватель нот из PDF. Все ноты с буквами + звук MuseScore."""

import sys, os
if getattr(sys, 'frozen', False):
    if sys.stdout is None: sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None: sys.stderr = open(os.devnull, 'w')

import threading, time, math, array, subprocess, pygame
from tkinter import Tk, filedialog
from music21 import converter

try:
    import cv2, numpy as np
except ImportError:
    cv2 = None; np = None

try:
    import fluidsynth
    FLUID_IMPORT_OK = True
except ImportError:
    FLUID_IMPORT_OK = False

FLUID_AVAILABLE = False
fs = None
SFID = None
SOUNDFONT_PATH = r"C:\tools\fluidsynth\soundfonts\FluidR3_GM.sf2"
FLUID_DRIVER = "waveout"
FLUID_GAIN = 1.5
NOTE_TAIL = 1.35
RIGHT_VEL = 100
LEFT_VEL = 70

LETTERS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Цвета
LETTER_COLOR_R = (0, 160, 0)
LETTER_COLOR_L = (0, 120, 180)
PLAYING_COLOR_R = (60, 220, 120)
PLAYING_COLOR_L = (80, 200, 230)


def get_short_note_name(midi_pitch):
    return LETTERS[midi_pitch % 12]


def init_fluidsynth():
    global FLUID_AVAILABLE, fs, SFID
    if not FLUID_IMPORT_OK:
        print("pyfluidsynth not installed"); return
    try:
        fs = fluidsynth.Synth()
        fs.setting('audio.driver', FLUID_DRIVER)
        fs.setting('synth.gain', FLUID_GAIN)
        fs.start()
        SFID = fs.sfload(SOUNDFONT_PATH)
        fs.program_select(0, SFID, 0, 0)
        FLUID_AVAILABLE = True
        print("FluidSynth ready:", FLUID_DRIVER)
    except Exception as e:
        FLUID_AVAILABLE = False
        print("FluidSynth failed:", e)


def _piano_wave_samples(freq, duration, sample_rate=44100):
    n = max(1, int(sample_rate * duration))
    buf = array.array('h', [0]) * n
    w = 2.0 * math.pi * freq
    for i in range(n):
        t = i / sample_rate
        buf[i] = int(32767 * math.exp(-4 * t) * math.sin(w * t))
    return buf


_SOUND_CACHE = {}
def _get_sound(midi_note, duration):
    key = (midi_note, round(duration, 2))
    snd = _SOUND_CACHE.get(key)
    if snd is not None: return snd
    freq = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
    buf = _piano_wave_samples(freq, max(0.6, duration + 0.3))
    snd = pygame.mixer.Sound(buffer=buf.tobytes())
    if len(_SOUND_CACHE) > 200: _SOUND_CACHE.clear()
    _SOUND_CACHE[key] = snd
    return snd


AUDIVERIS_EXE = r"C:\Program Files\Audiveris\Audiveris.exe"
OMR_OUTPUT_DIR = r"C:\out_omr"
MANUAL_BPM = 72.0
BPM_MIN, BPM_MAX = 30, 200

WHITE=(255,255,255); BLACK=(0,0,0); GRAY=(220,220,220); DARK_GRAY=(40,40,40)
BLUE=(51,153,255); RED=(255,87,87); GREEN=(46,204,113); YELLOW=(241,196,15)
ORANGE=(230,126,34); CYAN=(60,200,220)
BTN_GREEN=(46,204,113); BTN_YELLOW=(241,196,15); BTN_RED=(231,76,60)
BTN_GRAY=(200,200,200); BTN_BLUE=(52,152,219)

WIN_W, WIN_H = 1400, 800
TOPBAR_H = 60
KEYBOARD_H = 140
MIN_W, MIN_H = 900, 600
START_NOTE, NUM_KEYS = 21, 88

active_notes = set()
is_processing = False
status_text = "Нажмите Открыть PDF"
detected_melody = []
current_playing_note_name = ""
current_bar_display = ""
current_bpm_display = ""
stop_flag = threading.Event()
pause_flag = threading.Event()
play_thread = None
pdf_pages = []
pdf_current_page = 0
pdf_scroll_y = 0
# Карта: (page_idx, event_idx) -> [(x, y, letter, hand)]
note_labels = {}
# Карта: event_idx -> (page_idx, x, y) - центр играющего аккорда
playing_centers = {}
current_event_index = -1
current_bpm = MANUAL_BPM
is_fullscreen = False
screen = None
buttons = []
slider_rect = pygame.Rect(0, 0, 0, 0)
dragging_slider = False


def is_black_key(note):
    return ((note - 12) % 12) in (1, 3, 6, 8, 10)


def get_note_name(midi_pitch):
    names = ["C (До)","C# (До#)","D (Ре)","D# (Ре#)","E (Ми)","F (Фа)",
             "F# (Фа#)","G (Соль)","G# (Соль#)","A (Ля)","A# (Ля#)","B (Си)"]
    return names[midi_pitch % 12]


def _render_pdf_to_surfaces(pdf_path, dpi=150, max_pages=10):
    from pdf2image import convert_from_path
    images = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=max_pages)
    surfaces = []
    for img in images:
        arr = img.convert("RGB")
        surfaces.append(pygame.image.fromstring(arr.tobytes(), arr.size, "RGB"))
    return surfaces


def _run_audiveris(pdf_path):
    os.makedirs(OMR_OUTPUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    for ext in (".mxl", ".xml", ".musicxml"):
        c = os.path.join(OMR_OUTPUT_DIR, base + ext)
        if os.path.exists(c): return c
    cmd = [AUDIVERIS_EXE, "-batch", "-transcribe", "-export",
           "-output", OMR_OUTPUT_DIR, "--", pdf_path]
    subprocess.run(cmd, check=True, capture_output=True, timeout=900)
    for ext in (".mxl", ".xml", ".musicxml"):
        c = os.path.join(OMR_OUTPUT_DIR, base + ext)
        if os.path.exists(c): return c
    for f in os.listdir(OMR_OUTPUT_DIR):
        if f.startswith(base) and f.lower().endswith((".mxl", ".xml", ".musicxml")):
            return os.path.join(OMR_OUTPUT_DIR, f)
    raise RuntimeError("Audiveris did not create MusicXML")


def _musicxml_to_events(mxl_path):
    score = converter.parse(mxl_path)
    bpm = MANUAL_BPM
    marks = score.metronomeMarkBoundaries()
    if marks:
        try: bpm = float(marks[0][2].number)
        except: pass
    if bpm > 110 and abs(bpm - MANUAL_BPM) > 20: bpm = MANUAL_BPM
    spq = 60.0 / bpm
    used_parts = [p for p in score.parts if len(list(p.flatten().notes)) > 0]
    if not used_parts: raise RuntimeError("No notes")
    events = []
    for part_idx, part in enumerate(used_parts):
        hand = "R" if part_idx == 0 else "L"
        for el in part.flatten().notesAndRests:
            dur_q = float(el.quarterLength)
            if dur_q <= 0: continue
            offset_q = float(el.offset)
            try: bar = int(el.measureNumber) if el.measureNumber else 0
            except: bar = 0
            if hasattr(el, "pitches") and len(el.pitches) > 0:
                midis = sorted(p.midi for p in el.pitches)
                midis = [m for m in midis if START_NOTE <= m <= START_NOTE + NUM_KEYS - 1]
                if midis:
                    events.append({"bar": bar, "offset_q": offset_q,
                                   "time_seconds": offset_q * spq,
                                   "notes": midis,
                                   "duration": max(0.05, dur_q * spq),
                                   "hand": hand})
    events.sort(key=lambda e: e["time_seconds"])
    merged = []
    for ev in events:
        if merged:
            last = merged[-1]
            if abs(ev["time_seconds"] - last["time_seconds"]) < 0.02:
                last["notes"] = sorted(set(last["notes"]) | set(ev["notes"]))
                last["duration"] = max(last["duration"], ev["duration"])
                continue
        merged.append(dict(ev))
    if merged:
        t0 = merged[0]["time_seconds"]
        o0 = merged[0]["offset_q"]
        if t0 > 0.05:
            for ev in merged:
                ev["time_seconds"] -= t0
                ev["offset_q"] -= o0
    return merged, bpm, len(used_parts)


def _detect_staves(surf):
    """Возвращает список диапазонов Y для каждого стана (5 линеек)."""
    if cv2 is None or np is None: return []
    w, h = surf.get_size()
    raw = pygame.image.tostring(surf, "RGB")
    img = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Горизонтальные линии
    horiz = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_RECT, (w//10, 1)))
    row_sum = np.sum(horiz > 0, axis=1)
    thresh = max(20, w // 8)
    rows = [y for y in range(h) if row_sum[y] > thresh]
    # Группируем в станы (5 линий, близких друг к другу)
    staves = []
    if not rows: return staves
    group = [rows[0]]
    for y in rows[1:]:
        if y - group[-1] <= 4: group.append(y)
        else:
            if len(group) >= 4:
                staves.append((min(group), max(group)))
            group = [y]
    if len(group) >= 4:
        staves.append((min(group), max(group)))
    return staves


def _detect_barlines_for_staff(surf, staff_top, staff_bottom):
    """Ищет вертикальные тактовые линии внутри стана. Возвращает список X-координат."""
    if cv2 is None or np is None: return []
    w, h = surf.get_size()
    raw = pygame.image.tostring(surf, "RGB")
    img = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Ограничиваем полосой стана
    y0 = max(0, staff_top - 2); y1 = min(h, staff_bottom + 3)
    strip = binary[y0:y1, :]
    height = y1 - y0
    # Вертикальная морфология
    vert = cv2.morphologyEx(strip, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(5, height - 6))))
    col_sum = np.sum(vert > 0, axis=0)
    thr = height * 0.65
    cols = [x for x in range(w) if col_sum[x] > thr]
    # Группируем близкие столбцы
    groups = []
    if not cols: return groups
    g = [cols[0]]
    for x in cols[1:]:
        if x - g[-1] <= 4: g.append(x)
        else:
            groups.append(int(sum(g) / len(g))); g = [x]
    groups.append(int(sum(g) / len(g)))
    return groups


def _build_note_labels(pdf_surfaces):
    """Для каждой страницы находит станы, тактовые линии и распределяет события по тактам."""
    global note_labels, playing_centers
    note_labels = {}
    playing_centers = {}
    if not pdf_surfaces or not detected_melody: return

    # Группируем события по такту
    events_by_bar = {}
    for idx, ev in enumerate(detected_melody):
        bar = ev.get("bar", 0)
        events_by_bar.setdefault(bar, []).append(idx)

    # Проходим по каждой странице, находим станы и бары
    all_bars_sorted = sorted(events_by_bar.keys())
    bars_per_page = max(1, len(all_bars_sorted) // max(1, len(pdf_surfaces)))

    for pg_idx, surf in enumerate(pdf_surfaces):
        pw, ph = surf.get_size()
        staves = _detect_staves(surf)
        if not staves: continue

        # Какие такты на этой странице
        bar_start = pg_idx * bars_per_page
        bar_end = bar_start + bars_per_page
        page_bars = [b for b in all_bars_sorted if bar_start <= b < bar_end]
        if not page_bars:
            # fallback: все такты страницы
            total = len(all_bars_sorted)
            bar_start = int(pg_idx * total / len(pdf_surfaces))
            bar_end = int((pg_idx + 1) * total / len(pdf_surfaces))
            page_bars = all_bars_sorted[bar_start:bar_end]

        # Находим бары в каждом стане
        for staff_top, staff_bottom in staves:
            barlines = _detect_barlines_for_staff(surf, staff_top, staff_bottom)
            if len(barlines) < 2: continue

            # Каждому бару стана - свой X-диапазон
            n_bars_in_staff = len(barlines) - 1
            # Распределяем бары страницы по станам
            staff_share = max(1, len(page_bars) // max(1, len(staves)))
            staff_bars = page_bars[:staff_share]
            page_bars = page_bars[staff_share:]

            for k, bar in enumerate(staff_bars):
                if k >= n_bars_in_staff: break
                x_left = barlines[k]
                x_right = barlines[k + 1]
                y_mid = (staff_top + staff_bottom) // 2

                # События этого бара
                evs = events_by_bar.get(bar, [])
                if not evs: continue
                # Распределяем события внутри такта по X
                n_ev = len(evs)
                for i, ev_idx in enumerate(evs):
                    ev = detected_melody[ev_idx]
                    frac = (i + 0.5) / n_ev
                    x_center = int(x_left + frac * (x_right - x_left))
                    y_center = y_mid
                    # Для каждой ноты события - буква
                    letters = [get_short_note_name(m) for m in ev["notes"]]
                    hand = ev.get("hand", "R")
                    note_labels[(pg_idx, ev_idx)] = (x_center, y_center, letters, hand)
                    playing_centers[ev_idx] = (pg_idx, x_center, y_center)


def _note_off_later(midi_note, delay):
    def _off():
        try:
            if FLUID_AVAILABLE: fs.noteoff(0, midi_note)
        except Exception: pass
        active_notes.discard(midi_note)
    threading.Timer(delay, _off).start()


def play_music_logic():
    global current_playing_note_name, status_text, current_bar_display
    global current_event_index, pdf_current_page
    if not detected_melody:
        status_text = "Нет нот"; return
    status_text = "Воспроизведение..."
    speed = MANUAL_BPM / max(1.0, current_bpm)
    t0 = time.time()
    for idx, ev in enumerate(detected_melody):
        if stop_flag.is_set(): break
        while pause_flag.is_set() and not stop_flag.is_set():
            time.sleep(0.05)
        if stop_flag.is_set(): break
        t_start = t0 + float(ev.get("time_seconds", 0.0)) * speed
        wait = t_start - time.time()
        while wait > 0:
            if stop_flag.is_set(): break
            if pause_flag.is_set():
                time.sleep(0.05); t0 += 0.05
                t_start = t0 + float(ev.get("time_seconds", 0.0)) * speed
                wait = t_start - time.time(); continue
            time.sleep(min(0.02, wait)); wait = t_start - time.time()
        if stop_flag.is_set(): break
        notes = ev.get("notes", [])
        dur = float(ev.get("duration", 0.4)) * speed
        dur_play = dur * NOTE_TAIL
        current_event_index = idx
        if notes:
            names = []
            velocity = RIGHT_VEL if ev.get("hand", "R") == "R" else LEFT_VEL
            for n in notes:
                try:
                    active_notes.add(n)
                    names.append(get_note_name(n))
                    if FLUID_AVAILABLE:
                        fs.noteon(0, n, velocity)
                        _note_off_later(n, dur_play)
                    else:
                        _get_sound(n, dur).play()
                except: pass
            current_playing_note_name = " + ".join(names)
        current_bar_display = "Такт " + str(ev.get("bar", 0))
        # Авто-переключение на страницу играющего события
        if idx in playing_centers:
            pdf_current_page = playing_centers[idx][0]
    time.sleep(1.5)
    current_playing_note_name = ""
    current_bar_display = ""
    current_event_index = -1
    status_text = "Готово!" if not stop_flag.is_set() else "Остановлено."


def _stop_playback_if_any():
    global play_thread
    stop_flag.set(); pause_flag.clear()
    if play_thread is not None and play_thread.is_alive():
        play_thread.join(timeout=2.0)
    stop_flag.clear(); play_thread = None


def _clear_document():
    global detected_melody, pdf_pages, note_labels, playing_centers, pdf_current_page
    global pdf_scroll_y, current_event_index, current_playing_note_name, current_bar_display
    detected_melody = []; pdf_pages = []; note_labels = {}; playing_centers = {}
    pdf_current_page = 0; pdf_scroll_y = 0; current_event_index = -1
    current_playing_note_name = ""; current_bar_display = ""
    active_notes.clear()


def process_pdf_to_notes(pdf_path):
    global is_processing, detected_melody, status_text, current_bpm_display
    global pdf_pages, pdf_current_page, pdf_scroll_y, current_bpm
    _stop_playback_if_any(); _clear_document()
    is_processing = True
    try:
        status_text = "Рендер PDF..."
        try: pdf_pages = _render_pdf_to_surfaces(pdf_path, dpi=150)
        except Exception: pdf_pages = []
        pdf_current_page = 0; pdf_scroll_y = 0
        status_text = "Audiveris распознаёт..."
        mxl_path = _run_audiveris(pdf_path)
        status_text = "Парсинг MusicXML..."
        events, bpm, n_parts = _musicxml_to_events(mxl_path)
        if not events: raise RuntimeError("No events")
        detected_melody = events; current_bpm = bpm
        total_notes = sum(len(e["notes"]) for e in events)
        current_bpm_display = "BPM: " + str(int(bpm))
        status_text = "Поиск тактов и позиций нот..."
        _build_note_labels(pdf_pages)
        status_text = "Готово: " + str(total_notes) + " нот. Нажмите Играть."
        is_processing = False
    except Exception as e:
        status_text = "Ошибка: " + str(e)[:200]; is_processing = False


def open_file_dialog_thread():
    global status_text
    try:
        root = Tk(); root.withdraw(); root.attributes('-topmost', True)
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf"), ("All", "*.*")])
        root.destroy()
        if path:
            threading.Thread(target=process_pdf_to_notes, args=(path,), daemon=True).start()
    except Exception as e:
        status_text = "Ошибка: " + str(e)


class Button:
    def __init__(self, rect, text, color, action):
        self.rect = pygame.Rect(rect); self.text = text; self.color = color
        self.action = action; self.hover = False
    def draw(self, screen, font):
        c = self.color
        if self.hover: c = tuple(min(255, v + 25) for v in c)
        pygame.draw.rect(screen, c, self.rect, border_radius=6)
        pygame.draw.rect(screen, BLACK, self.rect, 2, border_radius=6)
        txt = font.render(self.text, True, BLACK)
        screen.blit(txt, (self.rect.x + (self.rect.w - txt.get_width()) // 2,
                          self.rect.y + (self.rect.h - txt.get_height()) // 2))
    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            self.action(); return True
        return False


def action_open_pdf():
    if is_processing: return
    threading.Thread(target=open_file_dialog_thread, daemon=True).start()

def action_play():
    global play_thread
    if is_processing or not detected_melody: return
    _stop_playback_if_any()
    stop_flag.clear(); pause_flag.clear()
    play_thread = threading.Thread(target=play_music_logic, daemon=True)
    play_thread.start()

def action_pause():
    if pause_flag.is_set(): pause_flag.clear()
    else: pause_flag.set()

def action_stop():
    stop_flag.set(); pause_flag.clear()
    if FLUID_AVAILABLE:
        try:
            for n in list(active_notes): fs.noteoff(0, n)
        except: pass
    active_notes.clear()

def action_toggle_fullscreen():
    global is_fullscreen, screen
    is_fullscreen = not is_fullscreen
    if is_fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
    _rebuild_buttons()


def _rebuild_buttons():
    global buttons, slider_rect
    w, _ = screen.get_size()
    bw, bh = 155, 36; gap = 8
    y = (TOPBAR_H - bh) // 2
    buttons = [
        Button((15, y, bw, bh), "Открыть PDF", BTN_GRAY, action_open_pdf),
        Button((15 + (bw + gap) * 1, y, bw, bh), "Играть", BTN_GREEN, action_play),
        Button((15 + (bw + gap) * 2, y, bw, bh), "Пауза", BTN_YELLOW, action_pause),
        Button((15 + (bw + gap) * 3, y, bw, bh), "Стоп", BTN_RED, action_stop),
        Button((15 + (bw + gap) * 4, y, bw, bh), "Полный экран", BTN_BLUE, action_toggle_fullscreen),
    ]
    sw = 200
    slider_rect = pygame.Rect(w - sw - 140, TOPBAR_H // 2 - 10, sw, 20)


def draw_topbar(screen, font):
    w, _ = screen.get_size()
    pygame.draw.rect(screen, (30, 30, 30), pygame.Rect(0, 0, w, TOPBAR_H))
    pygame.draw.line(screen, GRAY, (0, TOPBAR_H), (w, TOPBAR_H), 2)
    for b in buttons: b.draw(screen, font)
    sy = TOPBAR_H // 2
    pygame.draw.rect(screen, GRAY, pygame.Rect(slider_rect.x, sy - 3, slider_rect.w, 6), border_radius=3)
    frac = (current_bpm - BPM_MIN) / (BPM_MAX - BPM_MIN)
    kx = slider_rect.x + int(frac * slider_rect.w)
    pygame.draw.circle(screen, ORANGE, (kx, sy), 10)
    pygame.draw.circle(screen, BLACK, (kx, sy), 10, 2)
    screen.blit(font.render("BPM: " + str(int(current_bpm)), True, WHITE),
                (slider_rect.x + slider_rect.w + 15, sy - 12))


def draw_pdf(screen, letter_font, big_letter_font):
    w, h = screen.get_size()
    pdf_y0 = TOPBAR_H
    pdf_h = h - TOPBAR_H - KEYBOARD_H
    pygame.draw.rect(screen, (20, 20, 20), pygame.Rect(0, pdf_y0, w, pdf_h))
    if not pdf_pages:
        screen.blit(pygame.font.SysFont("Arial", 22).render("PDF не загружен", True, GRAY),
                    (40, pdf_y0 + 40))
        return
    page = pdf_pages[pdf_current_page]
    pw, ph = page.get_size()
    scale = w / pw
    scaled = pygame.transform.smoothscale(page, (int(pw * scale), int(ph * scale)))
    y_off = pdf_y0 - pdf_scroll_y
    screen.blit(scaled, (0, y_off))

    # --- Рисуем буквы ВСЕХ нот (кроме играющей — её отдельно) ---
    for (pg_idx, ev_idx), (x, y, letters, hand) in note_labels.items():
        if pg_idx != pdf_current_page: continue
        if ev_idx == current_event_index: continue  # играющую рисуем отдельно
        dx = int(x * scale); dy = int(y * scale) + y_off
        color = LETTER_COLOR_R if hand == "R" else LETTER_COLOR_L
        text = "-".join(letters)
        txt = letter_font.render(text, True, color)
        screen.blit(txt, (dx - txt.get_width() // 2, dy - txt.get_height() // 2))

    # --- Играющая нота: кружок + буквы белым ---
    if current_event_index >= 0 and current_event_index in playing_centers:
        pg_idx, x, y = playing_centers[current_event_index]
        if pg_idx == pdf_current_page:
            dx = int(x * scale); dy = int(y * scale) + y_off
            ev = detected_melody[current_event_index]
            hand = ev.get("hand", "R")
            color = PLAYING_COLOR_R if hand == "R" else PLAYING_COLOR_L
            letters = [get_short_note_name(m) for m in ev["notes"]]
            text = "-".join(letters)
            # Кружок
            pygame.draw.circle(screen, color, (dx, dy), 22)
            pygame.draw.circle(screen, WHITE, (dx, dy), 22, 2)
            # Буквы внутри
            txt = big_letter_font.render(text, True, WHITE)
            screen.blit(txt, (dx - txt.get_width() // 2, dy - txt.get_height() // 2))


def draw_keyboard(screen, letter_font):
    w, h = screen.get_size()
    kb_y = h - KEYBOARD_H
    pygame.draw.rect(screen, (25, 25, 25), pygame.Rect(0, kb_y, w, KEYBOARD_H))
    wc = sum(1 for n in range(START_NOTE, START_NOTE + NUM_KEYS) if not is_black_key(n))
    kw = w / wc; kh = KEYBOARD_H - 10
    idx = 0; n2x = {}
    for n in range(START_NOTE, START_NOTE + NUM_KEYS):
        if not is_black_key(n):
            x = idx * kw
            pygame.draw.rect(screen, BLUE if n in active_notes else WHITE,
                             pygame.Rect(x, kb_y + 5, kw - 1, kh))
            if n % 12 == 0:  # подписываем каждую C
                txt = letter_font.render(get_short_note_name(n), True, BLACK)
                screen.blit(txt, (x + kw // 2 - txt.get_width() // 2, kb_y + kh - 18))
            n2x[n] = x; idx += 1
    for n in range(START_NOTE, START_NOTE + NUM_KEYS):
        if is_black_key(n):
            px = n2x.get(n - 1); nx = n2x.get(n + 1)
            x = (px + kw * 0.7) if px is not None else (nx - kw * 0.3)
            pygame.draw.rect(screen, RED if n in active_notes else BLACK,
                             pygame.Rect(x, kb_y + 5, kw * 0.6, kh * 0.6))


def draw_interface(screen, font, large_font, small_font, letter_font, big_letter_font):
    screen.fill(DARK_GRAY)
    draw_topbar(screen, font)
    screen.blit(font.render(status_text, True, WHITE), (20, TOPBAR_H + 6))
    if current_playing_note_name:
        screen.blit(large_font.render("Играет: " + current_playing_note_name, True, GREEN),
                    (20, TOPBAR_H + 36))
    if current_bar_display:
        screen.blit(small_font.render(current_bar_display, True, YELLOW), (20, TOPBAR_H + 74))
    if is_processing:
        w, _ = screen.get_size()
        pygame.draw.circle(screen, ORANGE, (w - 40, TOPBAR_H + 30), 10)
    draw_pdf(screen, letter_font, big_letter_font)
    draw_keyboard(screen, letter_font)


def main():
    global screen, current_bpm, pdf_scroll_y, is_fullscreen
    global WIN_W, WIN_H, dragging_slider
    init_fluidsynth()
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
    pygame.display.set_caption("Piano Reader v8 - все ноты с буквами")
    font = pygame.font.SysFont("Arial", 20)
    large_font = pygame.font.SysFont("Arial", 26, bold=True)
    small_font = pygame.font.SysFont("Arial", 16)
    letter_font = pygame.font.SysFont("Arial", 13, bold=True)
    big_letter_font = pygame.font.SysFont("Arial", 16, bold=True)
    _rebuild_buttons()
    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False; stop_flag.set()
            elif event.type == pygame.VIDEORESIZE:
                if not is_fullscreen:
                    WIN_W = max(MIN_W, event.w); WIN_H = max(MIN_H, event.h)
                    screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
                    _rebuild_buttons()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: action_toggle_fullscreen()
                elif event.key == pygame.K_ESCAPE and is_fullscreen: action_toggle_fullscreen()
            elif event.type == pygame.MOUSEMOTION:
                for b in buttons: b.hover = b.rect.collidepoint(event.pos)
                if dragging_slider:
                    x = max(slider_rect.x, min(event.pos[0], slider_rect.x + slider_rect.w))
                    frac = (x - slider_rect.x) / slider_rect.w
                    current_bpm = BPM_MIN + frac * (BPM_MAX - BPM_MIN)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if slider_rect.collidepoint(event.pos):
                    dragging_slider = True
                    frac = (event.pos[0] - slider_rect.x) / slider_rect.w
                    current_bpm = BPM_MIN + frac * (BPM_MAX - BPM_MIN)
                else:
                    for b in buttons: b.handle_click(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_slider = False
            elif event.type == pygame.MOUSEWHEEL:
                pdf_scroll_y = max(0, pdf_scroll_y - event.y * 40)
        draw_interface(screen, font, large_font, small_font, letter_font, big_letter_font)
        pygame.display.flip()
        clock.tick(30)
    stop_flag.set()
    if FLUID_AVAILABLE and fs is not None:
        try: fs.delete()
        except: pass
    pygame.quit()


if __name__ == "__main__":
    main()
