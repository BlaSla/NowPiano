# -*- coding: utf-8 -*-
"""
piano5.py — проигрыватель нот из PDF.
- точная подсветка нот на PDF (OpenCV ищет головки)
- звук: синус с затуханием (рабочий вариант)
- кнопки: Открыть PDF, Играть, Пауза, Стоп, Полный экран
- ползунок BPM, F11, ресайз, прокрутка PDF
"""

import sys
import os

if getattr(sys, 'frozen', False):
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')

import threading
import time
import math
import array
import subprocess
import pygame
from tkinter import Tk, filedialog

from music21 import converter

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

AUDIVERIS_EXE = r"C:\Program Files\Audiveris\Audiveris.exe"
OMR_OUTPUT_DIR = r"C:\out_omr"

MANUAL_BPM = 72.0
BPM_MIN, BPM_MAX = 30, 200

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (220, 220, 220)
DARK_GRAY = (40, 40, 40)
BLUE = (51, 153, 255)
RED = (255, 87, 87)
GREEN = (46, 204, 113)
YELLOW = (241, 196, 15)
ORANGE = (230, 126, 34)
CYAN = (60, 200, 220)
BTN_GREEN = (46, 204, 113)
BTN_YELLOW = (241, 196, 15)
BTN_RED = (231, 76, 60)
BTN_GRAY = (200, 200, 200)
BTN_BLUE = (52, 152, 219)

WIN_W, WIN_H = 1400, 800
TOPBAR_H = 60
KEYBOARD_H = 140
MIN_W, MIN_H = 900, 600
START_NOTE, NUM_KEYS = 21, 88

active_notes = set()
is_processing = False
status_text = "Нажмите 'Открыть PDF' — выберите ноты"
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
highlight_map = {}
current_event_index = -1

current_bpm = MANUAL_BPM
is_fullscreen = False

SAMPLE_RATE = 44100
SOUND_CACHE = {}
MAX_CACHED = 200

screen = None
buttons = []
slider_rect = pygame.Rect(0, 0, 0, 0)
dragging_slider = False


# ---------- ЗВУК ----------
def _piano_wave_samples(freq, duration, sample_rate=SAMPLE_RATE):
    n = max(1, int(sample_rate * duration))
    buf = array.array('h', [0]) * n
    two_pi = 2.0 * math.pi
    w = two_pi * freq
    for i in range(n):
        t = i / sample_rate
        env = math.exp(-4 * t)
        buf[i] = int(32767 * env * math.sin(w * t))
    return buf


def _get_sound(midi_note, duration):
    key = (midi_note, round(duration, 2))
    snd = SOUND_CACHE.get(key)
    if snd is not None:
        return snd
    freq = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
    gen_dur = max(0.6, duration + 0.3)
    buf = _piano_wave_samples(freq, gen_dur)
    snd = pygame.mixer.Sound(buffer=buf.tobytes())
    if len(SOUND_CACHE) > MAX_CACHED:
        SOUND_CACHE.clear()
    SOUND_CACHE[key] = snd
    return snd


def note_to_freq(note):
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def is_black_key(note):
    return ((note - 12) % 12) in (1, 3, 6, 8, 10)


def get_note_name(midi_pitch):
    names = ["C (До)", "C# (До#)", "D (Ре)", "D# (Ре#)", "E (Ми)", "F (Фа)",
             "F# (Фа#)", "G (Соль)", "G# (Соль#)", "A (Ля)", "A# (Ля#)", "B (Си)"]
    return names[midi_pitch % 12]


# ---------- PDF -> SURFACE ----------
def _render_pdf_to_surfaces(pdf_path, dpi=150, max_pages=10):
    from pdf2image import convert_from_path
    images = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=max_pages)
    surfaces = []
    for img in images:
        arr = img.convert("RGB")
        surf = pygame.image.fromstring(arr.tobytes(), arr.size, "RGB")
        surfaces.append(surf)
    return surfaces


# ---------- AUDIVERIS ----------
def _run_audiveris(pdf_path):
    os.makedirs(OMR_OUTPUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    for ext in (".mxl", ".xml", ".musicxml"):
        candidate = os.path.join(OMR_OUTPUT_DIR, base + ext)
        if os.path.exists(candidate):
            return candidate
    cmd = [AUDIVERIS_EXE, "-batch", "-transcribe", "-export",
           "-output", OMR_OUTPUT_DIR, "--", pdf_path]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=900)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Audiveris не завершился за 15 минут.")
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode("utf-8", "ignore")
        raise RuntimeError(f"Audiveris вернул код {e.returncode}: {stderr[:300]}")
    for ext in (".mxl", ".xml", ".musicxml"):
        candidate = os.path.join(OMR_OUTPUT_DIR, base + ext)
        if os.path.exists(candidate):
            return candidate
    for f in os.listdir(OMR_OUTPUT_DIR):
        if f.startswith(base) and f.lower().endswith((".mxl", ".xml", ".musicxml")):
            return os.path.join(OMR_OUTPUT_DIR, f)
    raise RuntimeError(f"Audiveris не создал MusicXML в {OMR_OUTPUT_DIR}.")


# ---------- MUSICXML ----------
def _musicxml_to_events(mxl_path):
    score = converter.parse(mxl_path)
    bpm = MANUAL_BPM
    marks = score.metronomeMarkBoundaries()
    if marks:
        try:
            bpm = float(marks[0][2].number)
        except Exception:
            pass
    if bpm > 110 and MANUAL_BPM and abs(bpm - MANUAL_BPM) > 20:
        bpm = MANUAL_BPM
    spq = 60.0 / bpm
    used_parts = [p for p in score.parts if len(list(p.flatten().notes)) > 0]
    if not used_parts:
        raise RuntimeError("MusicXML не содержит ни одной партии с нотами.")
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
                    events.append({
                        "bar": bar,
                        "offset_q": offset_q,
                        "time_seconds": offset_q * spq,
                        "notes": midis,
                        "duration": max(0.05, dur_q * spq),
                        "hand": hand
                    })
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


# ---------- ПОИСК ГОЛОВОК НОТ НА СТРАНИЦЕ ----------
def _detect_note_heads_on_surface(surf):
    """
    Ищет овальные головки нот на pygame.Surface.
    Возвращает список (x, y, w, h) в координатах поверхности.
    """
    if cv2 is None or np is None:
        return []

    # pygame.Surface -> numpy RGB
    w, h = surf.get_size()
    raw = pygame.image.tostring(surf, "RGB")
    img = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Бинаризация: инвертируем, чтобы ноты стали белыми на чёрном
    _, binary = cv2.threshold(gray, 0, 255,
                              cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Убираем тонкие линии (нотные станы, штили) горизонтальной и вертикальной эрозией
    # — оставляем только «плотные» пятна (головки)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    # Ищем контуры
    contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

    heads = []
    for cnt in contours:
        x, y, ww, hh = cv2.boundingRect(cnt)
        # Фильтр по размеру: головка ноты примерно 8–18 пикселей при 150 dpi
        if not (5 <= ww <= 25 and 4 <= hh <= 20):
            continue
        # Форма: ширина чуть больше высоты или примерно равна (овал)
        ratio = ww / max(1, hh)
        if not (0.6 <= ratio <= 2.5):
            continue
        # Плотность: у головки высокая (залитая или плотная пустая)
        area = cv2.contourArea(cnt)
        if area < 12:
            continue
        fill = area / float(max(1, ww * hh))
        if fill < 0.35:
            continue
        cx = x + ww // 2
        cy = y + hh // 2
        heads.append((cx, cy, ww, hh))

    # Сортируем сверху вниз, потом слева направо
    heads.sort(key=lambda t: (t[1] // 20, t[0]))
    return heads


# ---------- ПОДСВЕТКА ----------
def _build_highlight_map(pdf_surfaces):
    """
    Ищет головки нот на каждой странице и привязывает к событиям
    по порядку (сверху вниз, слева направо).
    """
    global highlight_map
    highlight_map.clear()
    if not pdf_surfaces or not detected_melody:
        return

    # 1) Найти головки на всех страницах
    per_page_heads = []
    for surf in pdf_surfaces:
        per_page_heads.append(_detect_note_heads_on_surface(surf))

    # 2) Сопоставить события с головками по порядку
    n_events = len(detected_melody)
    total_heads = sum(len(h) for h in per_page_heads)

    # Соберём плоский список, сохраняя привязку к странице
    flat = []
    for pg_idx, heads in enumerate(per_page_heads):
        for (x, y, w, h) in heads:
            flat.append((pg_idx, x, y))

    if not flat:
        return

    if total_heads >= n_events:
        # Больше головок — распределяем пропорционально
        step = total_heads / n_events
        for i in range(n_events):
            k = min(total_heads - 1, int(round(i * step)))
            pg_idx, x, y = flat[k]
            highlight_map[i] = [(pg_idx, x, y)]
    else:
        # Меньше головок, чем событий — сопоставляем с ближайшей
        step = n_events / total_heads
        for k, (pg_idx, x, y) in enumerate(flat):
            i_start = int(round(k * step))
            i_end = int(round((k + 1) * step))
            for i in range(i_start, min(i_end, n_events)):
                highlight_map[i] = [(pg_idx, x, y)]


# ---------- ВОСПРОИЗВЕДЕНИЕ ----------
def play_music_logic():
    global current_playing_note_name, status_text, current_bar_display
    global current_event_index, pdf_current_page

    if not detected_melody:
        status_text = "Нет нот для воспроизведения."
        return

    status_text = "Воспроизведение..."
    speed = MANUAL_BPM / max(1.0, current_bpm)

    prev_end = 0.0
    for idx, ev in enumerate(detected_melody):
        if stop_flag.is_set():
            break
        while pause_flag.is_set() and not stop_flag.is_set():
            time.sleep(0.05)
        if stop_flag.is_set():
            break

        notes = ev.get("notes", [])
        dur = float(ev.get("duration", 0.4)) * speed
        start = float(ev.get("time_seconds", prev_end)) * speed
        bar = ev.get("bar", 0)

        gap = start - prev_end
        if gap > 0.05:
            end = time.time() + min(gap, 4.0)
            while time.time() < end:
                if stop_flag.is_set():
                    break
                time.sleep(0.02)
        if stop_flag.is_set():
            break

        current_event_index = idx
        if notes:
            names = []
            for n in notes:
                try:
                    active_notes.add(n)
                    names.append(get_note_name(n))
                    snd = _get_sound(n, dur)
                    snd.play()
                except Exception:
                    pass
            current_playing_note_name = " + ".join(names)

        current_bar_display = f"Такт {bar}, длит. {dur:.2f} сек."

        pos = highlight_map.get(idx)
        if pos:
            pdf_current_page = pos[0][0]

        end = time.time() + dur
        while time.time() < end:
            if stop_flag.is_set():
                break
            while pause_flag.is_set() and not stop_flag.is_set():
                time.sleep(0.05)
            time.sleep(0.02)

        for n in notes:
            active_notes.discard(n)
        prev_end = start + dur

    current_playing_note_name = ""
    current_bar_display = ""
    current_event_index = -1
    status_text = "Остановлено." if stop_flag.is_set() else "Готово!"


# ---------- ЗАГРУЗКА PDF ----------
def _stop_playback_if_any():
    global play_thread
    stop_flag.set()
    pause_flag.clear()
    if play_thread is not None and play_thread.is_alive():
        play_thread.join(timeout=2.0)
    stop_flag.clear()
    play_thread = None


def _clear_document():
    global detected_melody, pdf_pages, highlight_map, pdf_current_page
    global pdf_scroll_y, current_event_index, current_playing_note_name, current_bar_display
    detected_melody = []
    pdf_pages = []
    highlight_map = {}
    pdf_current_page = 0
    pdf_scroll_y = 0
    current_event_index = -1
    current_playing_note_name = ""
    current_bar_display = ""
    active_notes.clear()


def process_pdf_to_notes(pdf_path):
    global is_processing, detected_melody, status_text, current_bpm_display
    global pdf_pages, pdf_current_page, pdf_scroll_y, current_bpm

    _stop_playback_if_any()
    _clear_document()

    is_processing = True
    try:
        status_text = "Шаг 1/4: рендер PDF в изображение..."
        try:
            pdf_pages = _render_pdf_to_surfaces(pdf_path, dpi=150)
        except Exception as e:
            pdf_pages = []
            status_text = f"PDF не отрендерился: {e}"
        pdf_current_page = 0
        pdf_scroll_y = 0

        status_text = "Шаг 2/4: Audiveris распознаёт ноты..."
        mxl_path = _run_audiveris(pdf_path)

        status_text = "Шаг 3/4: парсинг MusicXML..."
        events, bpm, n_parts = _musicxml_to_events(mxl_path)
        if not events:
            raise RuntimeError("MusicXML не содержит музыкальных событий.")

        detected_melody = events
        current_bpm = bpm
        total_notes = sum(len(e["notes"]) for e in events)
        current_bpm_display = f"BPM: {bpm:.0f}"

        status_text = "Шаг 4/4: поиск головок нот для подсветки..."
        _build_highlight_map(pdf_pages)

        status_text = (f"Готово: {total_notes} нот, {len(events)} событий, "
                       f"партий: {n_parts}. Нажмите Играть.")
        is_processing = False
    except Exception as e:
        status_text = f"Ошибка: {str(e)[:200]}"
        is_processing = False


def open_file_dialog_thread():
    global status_text
    try:
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        root.destroy()
        if path:
            threading.Thread(
                target=process_pdf_to_notes, args=(path,), daemon=True
            ).start()
    except Exception as e:
        status_text = f"Ошибка проводника: {e}"


# ---------- КНОПКИ ----------
class Button:
    def __init__(self, rect, text, color, action):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.action = action
        self.hover = False

    def draw(self, screen, font):
        c = self.color
        if self.hover:
            c = tuple(min(255, v + 25) for v in c)
        pygame.draw.rect(screen, c, self.rect, border_radius=6)
        pygame.draw.rect(screen, BLACK, self.rect, 2, border_radius=6)
        txt = font.render(self.text, True, BLACK)
        screen.blit(txt, (
            self.rect.x + (self.rect.w - txt.get_width()) // 2,
            self.rect.y + (self.rect.h - txt.get_height()) // 2
        ))

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            self.action()
            return True
        return False


def action_open_pdf():
    if is_processing:
        return
    threading.Thread(target=open_file_dialog_thread, daemon=True).start()


def action_play():
    global play_thread
    if is_processing or not detected_melody:
        return
    _stop_playback_if_any()
    stop_flag.clear()
    pause_flag.clear()
    play_thread = threading.Thread(target=play_music_logic, daemon=True)
    play_thread.start()


def action_pause():
    if pause_flag.is_set():
        pause_flag.clear()
    else:
        pause_flag.set()


def action_stop():
    stop_flag.set()
    pause_flag.clear()
    active_notes.clear()


def action_toggle_fullscreen():
    global is_fullscreen, screen
    is_fullscreen = not is_fullscreen
    if is_fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
    _rebuild_buttons()


# ---------- ОТРИСОВКА ----------
def _rebuild_buttons():
    global buttons, slider_rect
    w, _ = screen.get_size()
    btn_w, btn_h = 160, 36
    gap = 10
    y = (TOPBAR_H - btn_h) // 2

    buttons = [
        Button((15, y, btn_w, btn_h), "Открыть PDF", BTN_GRAY, action_open_pdf),
        Button((15 + (btn_w + gap) * 1, y, btn_w, btn_h), "Играть", BTN_GREEN, action_play),
        Button((15 + (btn_w + gap) * 2, y, btn_w, btn_h), "Пауза", BTN_YELLOW, action_pause),
        Button((15 + (btn_w + gap) * 3, y, btn_w, btn_h), "Стоп", BTN_RED, action_stop),
        Button((15 + (btn_w + gap) * 4, y, btn_w, btn_h), "Полный экран", BTN_BLUE,
               action_toggle_fullscreen),
    ]

    slider_w = 220
    slider_x = w - slider_w - 160
    slider_rect = pygame.Rect(slider_x, TOPBAR_H // 2 - 10, slider_w, 20)


def draw_topbar(screen, font):
    w, _ = screen.get_size()
    pygame.draw.rect(screen, (30, 30, 30), pygame.Rect(0, 0, w, TOPBAR_H))
    pygame.draw.line(screen, GRAY, (0, TOPBAR_H), (w, TOPBAR_H), 2)
    for b in buttons:
        b.draw(screen, font)
    slider_y = TOPBAR_H // 2
    pygame.draw.rect(screen, GRAY,
                     pygame.Rect(slider_rect.x, slider_y - 3, slider_rect.w, 6),
                     border_radius=3)
    frac = (current_bpm - BPM_MIN) / (BPM_MAX - BPM_MIN)
    knob_x = slider_rect.x + int(frac * slider_rect.w)
    pygame.draw.circle(screen, ORANGE, (knob_x, slider_y), 10)
    pygame.draw.circle(screen, BLACK, (knob_x, slider_y), 10, 2)
    lbl = font.render(f"BPM: {int(current_bpm)}", True, WHITE)
    screen.blit(lbl, (slider_rect.x + slider_rect.w + 15, slider_y - 12))


def draw_pdf(screen):
    w, h = screen.get_size()
    pdf_y0 = TOPBAR_H
    pdf_h = h - TOPBAR_H - KEYBOARD_H
    pygame.draw.rect(screen, (20, 20, 20), pygame.Rect(0, pdf_y0, w, pdf_h))

    if not pdf_pages:
        msg = pygame.font.SysFont("Arial", 22).render(
            "PDF не загружен. Нажмите 'Открыть PDF'.", True, GRAY)
        screen.blit(msg, (40, pdf_y0 + 40))
        return

    page = pdf_pages[pdf_current_page]
    pw, ph = page.get_size()
    scale = w / pw
    new_w = int(pw * scale)
    new_h = int(ph * scale)
    scaled = pygame.transform.smoothscale(page, (new_w, new_h))
    y_off = pdf_y0 - pdf_scroll_y
    screen.blit(scaled, (0, y_off))

    if current_event_index >= 0 and current_event_index in highlight_map:
        positions = highlight_map[current_event_index]
        for (pg_idx, x, y) in positions:
            if pg_idx != pdf_current_page:
                continue
            dx = int(x * scale)
            dy = int(y * scale) + y_off
            ev = detected_melody[current_event_index] if current_event_index < len(detected_melody) else {}
            hand = ev.get("hand", "R")
            color = GREEN if hand == "R" else CYAN
            pygame.draw.circle(screen, color, (dx, dy), 14, 3)
            pygame.draw.circle(screen, WHITE, (dx, dy), 14, 1)


def draw_keyboard(screen):
    w, h = screen.get_size()
    kb_y = h - KEYBOARD_H
    pygame.draw.rect(screen, (25, 25, 25), pygame.Rect(0, kb_y, w, KEYBOARD_H))
    white_count = sum(1 for n in range(START_NOTE, START_NOTE + NUM_KEYS)
                      if not is_black_key(n))
    key_w = w / white_count
    key_h = KEYBOARD_H - 10
    idx = 0
    note_to_x = {}
    for note in range(START_NOTE, START_NOTE + NUM_KEYS):
        if not is_black_key(note):
            x = idx * key_w
            pygame.draw.rect(
                screen,
                BLUE if note in active_notes else WHITE,
                pygame.Rect(x, kb_y + 5, key_w - 1, key_h)
            )
            note_to_x[note] = x
            idx += 1
    for note in range(START_NOTE, START_NOTE + NUM_KEYS):
        if is_black_key(note):
            prev_x = note_to_x.get(note - 1)
            next_x = note_to_x.get(note + 1)
            x = (prev_x + key_w * 0.7) if prev_x is not None else (next_x - key_w * 0.3)
            pygame.draw.rect(
                screen,
                RED if note in active_notes else BLACK,
                pygame.Rect(x, kb_y + 5, key_w * 0.6, key_h * 0.6)
            )


def draw_interface(screen, font, large_font, small_font):
    screen.fill(DARK_GRAY)
    draw_topbar(screen, font)
    st = font.render(status_text, True, WHITE)
    screen.blit(st, (20, TOPBAR_H + 6))
    if current_playing_note_name:
        nt = large_font.render(f"Играет: {current_playing_note_name}", True, GREEN)
        screen.blit(nt, (20, TOPBAR_H + 36))
    if current_bar_display:
        bd = small_font.render(current_bar_display, True, YELLOW)
        screen.blit(bd, (20, TOPBAR_H + 74))
    if current_bpm_display:
        w, _ = screen.get_size()
        bp = small_font.render(current_bpm_display, True, ORANGE)
        screen.blit(bp, (w - 200, TOPBAR_H + 36))
    if is_processing:
        w, _ = screen.get_size()
        pygame.draw.circle(screen, ORANGE, (w - 40, TOPBAR_H + 30), 10)
    draw_pdf(screen)
    draw_keyboard(screen)


# ---------- ЗАПУСК ----------
def main():
    global screen, current_bpm, pdf_scroll_y, is_fullscreen
    global WIN_W, WIN_H, dragging_slider

    pygame.init()
    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)

    screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
    pygame.display.set_caption("Piano Reader v5 — распознавание нот из PDF")

    font = pygame.font.SysFont("Arial", 20)
    large_font = pygame.font.SysFont("Arial", 26, bold=True)
    small_font = pygame.font.SysFont("Arial", 16)

    _rebuild_buttons()

    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                stop_flag.set()

            elif event.type == pygame.VIDEORESIZE:
                if not is_fullscreen:
                    WIN_W = max(MIN_W, event.w)
                    WIN_H = max(MIN_H, event.h)
                    screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
                    _rebuild_buttons()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    action_toggle_fullscreen()
                elif event.key == pygame.K_ESCAPE and is_fullscreen:
                    action_toggle_fullscreen()

            elif event.type == pygame.MOUSEMOTION:
                for b in buttons:
                    b.hover = b.rect.collidepoint(event.pos)
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
                    for b in buttons:
                        b.handle_click(event.pos)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_slider = False

            elif event.type == pygame.MOUSEWHEEL:
                pdf_scroll_y = max(0, pdf_scroll_y - event.y * 40)

        draw_interface(screen, font, large_font, small_font)
        pygame.display.flip()
        clock.tick(30)

    stop_flag.set()
    pygame.quit()


if __name__ == "__main__":
    main()