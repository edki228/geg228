# ============================================================
# ДВУХИГРОВОЙ КЛИКЕР — ФИНАЛЬНАЯ ВЕРСИЯ
# + Список серверов (UDP-broadcast) через Radmin VPN
# + Достижения отдельно у каждого игрока
# + Мультиплеер во всех режимах
# + Сохранение НЕ сбрасывается после comp/race
# ============================================================

import pygame as ed
import sys
import random
import json
import os
import socket
import threading
import queue
import time as _time
import tkinter as tk
from tkinter import filedialog

ed.init()
WIDTH, HEIGHT = 1520, 800
screen = ed.display.set_mode((WIDTH, HEIGHT), ed.FULLSCREEN)
ed.display.set_caption("огризок")

font_huge  = ed.font.Font(None, 120)
font_big   = ed.font.Font(None, 64)
font_mid   = ed.font.Font(None, 40)
font_small = ed.font.Font(None, 28)
font_tiny  = ed.font.Font(None, 20)
font_mini  = ed.font.Font(None, 17)

clock = ed.time.Clock()
FPS = 240
MAX_LEVEL = 100

# ============================================================
# МУЗЫКА
# ============================================================
MUSIC_DIR = "music"
playlist = []
current_track = 0
music_volume = 0.7
music_paused = False

def scan_music():
    global playlist
    found = []
    if os.path.isdir(MUSIC_DIR):
        for f in sorted(os.listdir(MUSIC_DIR)):
            if f.lower().endswith((".mp3", ".ogg", ".wav")):
                found.append(os.path.join(MUSIC_DIR, f))
    if not found and os.path.exists("muzika.mp3"):
        found.append("muzika.mp3")
    playlist = found

def play_track(idx):
    global current_track
    if not playlist: return
    current_track = idx % len(playlist)
    try:
        ed.mixer.music.load(playlist[current_track])
        ed.mixer.music.set_volume(music_volume)
        ed.mixer.music.play(-1)
    except Exception as e:
        print("Ошибка музыки:", e)

def next_track():
    if playlist: play_track(current_track + 1)

def prev_track():
    if playlist: play_track(current_track - 1)

def toggle_pause():
    global music_paused
    if not playlist: return
    if music_paused:
        ed.mixer.music.unpause(); music_paused = False
    else:
        ed.mixer.music.pause(); music_paused = True

def change_volume(delta):
    global music_volume
    music_volume = max(0.0, min(1.0, music_volume + delta))
    ed.mixer.music.set_volume(music_volume)

def get_track_name():
    if not playlist: return "— нет музыки —"
    return os.path.basename(playlist[current_track])

def add_music_files():
    global playlist
    was_empty = (len(playlist) == 0)
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        files = filedialog.askopenfilenames(
            title="Выберите аудиофайлы",
            filetypes=[("Аудио", "*.mp3 *.ogg *.wav"),
                       ("MP3", "*.mp3"),
                       ("OGG", "*.ogg"),
                       ("WAV", "*.wav"),
                       ("Все файлы", "*.*")]
        )
        root.destroy()
    except Exception as e:
        print("Ошибка диалога выбора файла:", e)
        return
    if not files:
        return
    added = 0
    for f in files:
        if f and f not in playlist:
            playlist.append(f)
            added += 1
    if added > 0:
        print(f"📁 Добавлено треков: {added} (всего: {len(playlist)})")
        if was_empty:
            play_track(0)

scan_music()
if playlist: play_track(0)

# ============================================================
# КАРТИНКИ КНОПОК ИГРОКОВ
# ============================================================
try:
    button_img = ed.image.load("igrok.png").convert_alpha()
    button_img = ed.transform.smoothscale(button_img, (260, 260))
except FileNotFoundError:
    button_img = ed.Surface((260, 260), ed.SRCALPHA)
    ed.draw.circle(button_img, (110, 193, 255), (130, 130), 130)

button_img2 = ed.Surface((260, 260), ed.SRCALPHA)
ed.draw.circle(button_img2, (255, 130, 130), (130, 130), 130)

PLAYER1_X = WIDTH // 4
PLAYER2_X = WIDTH * 3 // 4
button1_rect = button_img.get_rect(center=(PLAYER1_X, 320))
button2_rect = button_img2.get_rect(center=(PLAYER2_X, 320))

# ============================================================
# УЛУЧШЕНИЯ
# ============================================================
UPGRADES_BASE = [
    {"name": "Клик",     "desc": "+1 к силе клика",         "base": 10,   "mult": 1.5, "effect": "power",         "value": 1},
    {"name": "Авто",     "desc": "+1 очко/сек",             "base": 50,   "mult": 1.7, "effect": "auto",          "value": 1},
    {"name": "Множ",     "desc": "x1.10 к урону клика",     "base": 200,  "mult": 2.0, "effect": "mult",          "value": 1.10},
    {"name": "Крит",     "desc": "+3% шанс крита",          "base": 100,  "mult": 1.8, "effect": "crit",          "value": 0.03},
    {"name": "КритУрон", "desc": "+1 к множителю крита",    "base": 300,  "mult": 2.1, "effect": "crit_mult",     "value": 1.0},
    {"name": "АвтоМнож", "desc": "+15% к автодоходу",       "base": 400,  "mult": 1.9, "effect": "auto_mult",     "value": 0.15},
    {"name": "Золото",   "desc": "+2% шанс золотого клика", "base": 500,  "mult": 2.3, "effect": "golden_chance", "value": 0.02},
    {"name": "Мега",     "desc": "x1.05 ко всему доходу",   "base": 800,  "mult": 2.5, "effect": "mega_mult",     "value": 1.05},
]

UPGRADES_EXTRA = [
    {"name": "Комбо",       "desc": "+3% урона за клик подряд",  "base": 1500,   "mult": 1.8, "effect": "combo",         "value": 0.03},
    {"name": "Взрыв",       "desc": "Каждый 25-й клик x10",       "base": 2500,   "mult": 2.0, "effect": "boom",          "value": 25},
    {"name": "Эхо",         "desc": "+5% шанс двойного клика",   "base": 3500,   "mult": 2.0, "effect": "echo",          "value": 0.05},
    {"name": "Берсерк",     "desc": "x1.5 если позади по очкам", "base": 4000,   "mult": 2.2, "effect": "berserk",       "value": 1.5},
    {"name": "Вампир",      "desc": "+2% урона в авто-копилку",  "base": 5000,   "mult": 2.0, "effect": "vampirism",     "value": 0.02},
    {"name": "Магнит",      "desc": "+3% шанс золотого клика",   "base": 6000,   "mult": 2.1, "effect": "gold_magnet",   "value": 0.03},
    {"name": "Удача",       "desc": "+2% крит за клик без крита","base": 7000,   "mult": 2.2, "effect": "crit_luck",     "value": 0.02},
    {"name": "Джекпот",     "desc": "25% шанс двойного золотого","base": 8000,   "mult": 2.3, "effect": "jackpot",       "value": 0.25},
    {"name": "Разгон",      "desc": "+3% к авто за клик (5 сек)","base": 9000,   "mult": 2.0, "effect": "speedup",       "value": 0.03},
    {"name": "Реактор",     "desc": "Авто-клик раз в 10 сек",    "base": 10000,  "mult": 2.2, "effect": "reactor",       "value": 10.0},
    {"name": "Симбиоз",     "desc": "+5% от авто к силе клика",  "base": 12000,  "mult": 2.0, "effect": "symbiosis",     "value": 0.05},
    {"name": "Щит-Реген",   "desc": "Щит раз в 30 сек",          "base": 14000,  "mult": 2.1, "effect": "shield_regen",  "value": 30.0},
    {"name": "Проклятие",   "desc": "Противник -0.3% очков/сек", "base": 16000,  "mult": 2.3, "effect": "curse",         "value": 0.003},
    {"name": "Лотерея",     "desc": "2% шанс x50 урона",         "base": 18000,  "mult": 2.2, "effect": "lottery",       "value": 0.02},
    {"name": "Кристалл",    "desc": "+5 пассивных очков в сек",  "base": 20000,  "mult": 2.0, "effect": "crystal",       "value": 5},
    {"name": "Скидка",      "desc": "-3% ко всем ценам",         "base": 25000,  "mult": 2.4, "effect": "discount",      "value": 0.03},
    {"name": "Иммунитет",   "desc": "20% шанс игнора негатива",  "base": 35000,  "mult": 2.3, "effect": "immunity",      "value": 0.20},
    {"name": "Гамбит",      "desc": "+50% урона, клик -1 очко",  "base": 40000,  "mult": 2.5, "effect": "gambit",        "value": 0.5},
    {"name": "Цепь",        "desc": "Каждые 30 кликов +1 силы",  "base": 50000,  "mult": 2.2, "effect": "chain",         "value": 30},
    {"name": "Феникс",      "desc": "x2 урона при очках < 100",  "base": 60000,  "mult": 2.3, "effect": "phoenix",       "value": 2.0},
    {"name": "Гармония",    "desc": "+2% авто за каждый ур.",    "base": 70000,  "mult": 2.4, "effect": "harmony",       "value": 0.02},
    {"name": "Резонанс",    "desc": "x1.3 если противник впереди","base": 80000, "mult": 2.2, "effect": "resonance",     "value": 1.3},
    {"name": "Терпение",    "desc": "+5% за секунду без кликов", "base": 100000, "mult": 2.0, "effect": "patience",      "value": 0.05},
    {"name": "Снайпер",     "desc": "8% шанс x20 урона",         "base": 120000, "mult": 2.3, "effect": "sniper",        "value": 0.08},
    {"name": "Защита",      "desc": "-25% эффект негатива",      "base": 150000, "mult": 2.4, "effect": "protection",    "value": 0.25},
    {"name": "Слияние",     "desc": "+3% от авто к силе клика",  "base": 180000, "mult": 2.2, "effect": "fusion",        "value": 0.03},
    {"name": "Тайфун",      "desc": "Каждые 10 кликов x5",       "base": 220000, "mult": 2.3, "effect": "typhoon",       "value": 10},
    {"name": "Мудрость",    "desc": "x1.5 к эффектам событий",   "base": 300000, "mult": 2.5, "effect": "wisdom",        "value": 1.5},
    {"name": "Овердрайв",   "desc": "1% шанс бесплатный уровень","base": 500000, "mult": 2.7, "effect": "overdrive",     "value": 0.01},
]

UPGRADES = UPGRADES_BASE + UPGRADES_EXTRA
NUM_UPGRADES = len(UPGRADES)
BASE_COUNT = len(UPGRADES_BASE)

def get_active_count():
    return NUM_UPGRADES if state == "free" else BASE_COUNT

# ============================================================
# ДОСТИЖЕНИЯ
# ============================================================
def _count_maxed(p):
    return sum(1 for l in p["levels"][:get_active_count()] if l >= MAX_LEVEL)

def _all_maxed(p):
    cnt = get_active_count()
    return cnt > 0 and all(l >= MAX_LEVEL for l in p["levels"][:cnt])

def _all_min_level(p, lvl):
    cnt = get_active_count()
    return cnt > 0 and all(l >= lvl for l in p["levels"][:cnt])

ACHIEVEMENTS = [
    {"id": "first_step",  "name": "🐣 Первый шаг",          "desc": "Купить первое улучшение",       "check": lambda p: sum(p["levels"]) >= 1},
    {"id": "first_max",   "name": "🎖️ Первый максимум",    "desc": "1 улучшение на 100 ур.",        "check": lambda p: _count_maxed(p) >= 1},
    {"id": "master_5",    "name": "🏅 Мастер",              "desc": "5 улучшений на максимуме",      "check": lambda p: _count_maxed(p) >= 5},
    {"id": "collector_10","name": "🥈 Коллекционер",        "desc": "10 улучшений на максимуме",     "check": lambda p: _count_maxed(p) >= 10},
    {"id": "legend_20",   "name": "🥇 Легенда",             "desc": "20 улучшений на максимуме",     "check": lambda p: _count_maxed(p) >= 20},
    {"id": "titan_30",    "name": "💎 Титан",               "desc": "30 улучшений на максимуме",     "check": lambda p: _count_maxed(p) >= 30},
    {"id": "god_all",     "name": "👑 БОГ КЛИКЕРА",         "desc": "ВСЕ улучшения на 100 ур.",      "check": lambda p: _all_maxed(p)},
    {"id": "halfway",     "name": "🌗 Полпути",             "desc": "Все улучшения 50+",             "check": lambda p: _all_min_level(p, 50)},
    {"id": "almost_god",  "name": "🌟 Почти Бог",           "desc": "Все улучшения 90+",             "check": lambda p: _all_min_level(p, 90)},
    {"id": "student",     "name": "📚 Ученик",              "desc": "Суммарно 100 уровней прокачки", "check": lambda p: sum(p["levels"]) >= 100},
    {"id": "professor",   "name": "🎓 Профессор",           "desc": "Суммарно 500 уровней",          "check": lambda p: sum(p["levels"]) >= 500},
    {"id": "grandmaster", "name": "🏆 Гроссмейстер",        "desc": "Суммарно 1500 уровней",         "check": lambda p: sum(p["levels"]) >= 1500},
    {"id": "rich_1k",     "name": "💵 Первая тысяча",       "desc": "Накопить 1 000",                "check": lambda p: p.get("max_score", 0) >= 1000},
    {"id": "rich_100k",   "name": "💸 Богач",               "desc": "Накопить 100 000",              "check": lambda p: p.get("max_score", 0) >= 100000},
    {"id": "millionaire", "name": "💰 Миллионер",           "desc": "Накопить 1 000 000",            "check": lambda p: p.get("max_score", 0) >= 1000000},
    {"id": "ten_million", "name": "🤑 Мультимиллионер",     "desc": "Накопить 10 000 000",           "check": lambda p: p.get("max_score", 0) >= 10000000},
    {"id": "billionaire", "name": "🏦 Миллиардер",          "desc": "Накопить 1 000 000 000",        "check": lambda p: p.get("max_score", 0) >= 1000000000},
    {"id": "click_1k",    "name": "🖱️ Новичок клика",      "desc": "1 000 кликов",                  "check": lambda p: p.get("total_clicks", 0) >= 1000},
    {"id": "click_10k",   "name": "🖱️ Клик-машина",        "desc": "10 000 кликов",                 "check": lambda p: p.get("total_clicks", 0) >= 10000},
    {"id": "click_100k",  "name": "🖱️ Клик-маньяк",        "desc": "100 000 кликов",                "check": lambda p: p.get("total_clicks", 0) >= 100000},
    {"id": "combo_100",   "name": "🔥 Комбо-мастер",        "desc": "Комбо из 100 кликов",           "check": lambda p: p.get("max_combo", 0) >= 100},
    {"id": "combo_500",   "name": "🔥🔥 Комбо-бог",         "desc": "Комбо из 500 кликов",           "check": lambda p: p.get("max_combo", 0) >= 500},
    {"id": "golden_50",   "name": "🌟 Охотник за золотом",  "desc": "50 золотых кликов",             "check": lambda p: p.get("golden_caught", 0) >= 50},
    {"id": "golden_500",  "name": "✨ Коллекционер золота", "desc": "500 золотых кликов",            "check": lambda p: p.get("golden_caught", 0) >= 500},
    {"id": "crit_big",    "name": "⚡ Критический удар",    "desc": "Крит-шанс 50%+",                "check": lambda p: p.get("crit", 0) >= 0.5},
]
TOTAL_ACH = len(ACHIEVEMENTS)

unlocked_achievements_p1 = set()
unlocked_achievements_p2 = set()
achievement_banner = ""
achievement_banner_timer = 0.0
achievement_banner_player = 0
show_achievements = False
achievements_scroll = 0

# ============================================================
# СОЗДАНИЕ ИГРОКА
# ============================================================
def make_player():
    return {
        "score": 0, "power": 1, "auto": 0, "mult": 1.0,
        "crit": 0.0, "crit_mult": 5.0, "auto_mult": 1.0,
        "golden_chance": 0.0, "golden_mult": 10.0, "mega_mult": 1.0,
        "levels": [0] * NUM_UPGRADES, "costs": [u["base"] for u in UPGRADES],
        "scale": 1.0, "auto_acc": 0.0, "golden": 0,
        "max_score": 0, "max_combo": 0, "golden_caught": 0, "total_clicks": 0,
        "combo": 0, "combo_timer": 0.0, "combo_value": 0.0, "combo_max": 1.5,
        "click_counter": 0, "boom_every": 0, "boom_mult": 10, "echo": 0.0,
        "berserk": 1.0, "vampirism": 0.0, "gold_magnet": 0.0,
        "crit_luck": 0.0, "crit_stack": 0.0, "jackpot": 0.0,
        "speedup_value": 0.0, "speedup_bonus": 0.0, "speedup_max": 1.5, "speedup_timer": 0.0,
        "reactor_interval": 0.0, "reactor_timer": 0.0,
        "symbiosis": 0.0, "shield_regen": 0.0, "shield_regen_timer": 0.0,
        "curse": 0.0, "lottery_chance": 0.0, "lottery_mult": 50,
        "crystal": 0, "discount": 0.0, "immunity": 0.0, "gambit": 0.0,
        "chain_every": 0, "phoenix": 1.0, "harmony": 0.0, "resonance": 1.0,
        "patience_value": 0.0, "patience_timer": 0.0,
        "sniper_chance": 0.0, "sniper_mult": 20, "protection": 0.0,
        "fusion": 0.0, "typhoon_every": 0, "typhoon_mult": 5, "typhoon_ready": False,
        "wisdom": 1.0, "overdrive": 0.0,
    }

p1 = make_player()
p2 = make_player()

# Снимок свободного режима (для сохранения save.json)
free_p1_snapshot = None
free_p2_snapshot = None

# ============================================================
# СОХРАНЕНИЕ / ЗАГРУЗКА
# ============================================================
SAVE_FILE = "save.json"

def save_game():
    # Всегда сохраняем игроков свободного режима.
    # Если сейчас идёт comp/race — берём из снимка.
    src_p1 = free_p1_snapshot if free_p1_snapshot is not None else p1
    src_p2 = free_p2_snapshot if free_p2_snapshot is not None else p2

    keys = list(make_player().keys())
    safe = ("scale","auto_acc","golden","combo","combo_timer","click_counter",
            "speedup_bonus","speedup_timer","reactor_timer","shield_regen_timer",
            "patience_timer","crit_stack","typhoon_ready")
    data = {}
    for name, pl in (("p1", src_p1), ("p2", src_p2)):
        data[name] = {k: pl[k] for k in keys if k not in safe}
    data["achievements_p1"] = list(unlocked_achievements_p1)
    data["achievements_p2"] = list(unlocked_achievements_p2)
    data["playlist"] = playlist
    data["current_track"] = current_track
    data["music_volume"] = music_volume
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Не удалось сохранить:", e)

def load_game():
    global unlocked_achievements_p1, unlocked_achievements_p2
    global playlist, current_track, music_volume
    if not os.path.exists(SAVE_FILE): return
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, player in (("p1", p1), ("p2", p2)):
            if key in data:
                for k, v in data[key].items():
                    if k in player: player[k] = v
                if len(player["costs"]) != NUM_UPGRADES:
                    player["costs"] = [u["base"] for u in UPGRADES]
                    player["levels"] = [0] * NUM_UPGRADES
        if "achievements_p1" in data:
            unlocked_achievements_p1 = set(data["achievements_p1"])
        if "achievements_p2" in data:
            unlocked_achievements_p2 = set(data["achievements_p2"])
        if "playlist" in data and isinstance(data["playlist"], list):
            for f in data["playlist"]:
                if os.path.exists(f) and f not in playlist:
                    playlist.append(f)
        if "current_track" in data and playlist:
            current_track = min(data["current_track"], len(playlist) - 1)
        if "music_volume" in data:
            music_volume = max(0.0, min(1.0, float(data["music_volume"])))
    except Exception as e:
        print("Не удалось загрузить:", e)

def reset_game():
    global unlocked_achievements_p1, unlocked_achievements_p2
    global free_p1_snapshot, free_p2_snapshot
    try:
        if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
    except Exception: pass
    for player in (p1, p2):
        for k, v in make_player().items(): player[k] = v
    unlocked_achievements_p1 = set()
    unlocked_achievements_p2 = set()
    free_p1_snapshot = None
    free_p2_snapshot = None
    reset_effects()

# ============================================================
# ЦВЕТА
# ============================================================
COLOR_P1 = (110, 193, 255)
COLOR_P2 = (255, 130, 130)
COLOR_BG = (30, 30, 47)
COLOR_GOLD = (255, 215, 0)
COLOR_GRAY = (150, 150, 150)
COLOR_RED = (255, 70, 70)
COLOR_GREEN = (100, 255, 150)
COLOR_PANEL_BG = (22, 22, 36)
COLOR_BTN_BG = (42, 42, 66)
COLOR_BTN_BG_OK = (55, 75, 110)
COLOR_BTN_BG_OK2 = (110, 60, 60)
COLOR_EXTRA = (200, 150, 255)
COLOR_MAX = (255, 200, 60)
COLOR_NET = (200, 150, 255)

# ============================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================
state = "menu"
prev_state = "free"
popups = []

EVENT_INTERVAL = 20.0
AUTOSAVE_INTERVAL = 30.0
event_timer = EVENT_INTERVAL
autosave_timer = AUTOSAVE_INTERVAL

double_time = 0.0
mega_click_time = 0.0
freeze_time = 0.0
auto_boom_time = 0.0
auto_mega_time = 0.0
temp_crit_time = 0.0
temp_power_time = 0.0
shield_active = False

event_message = ""
event_message_timer = 0.0

comp_target = 5000
RACE_DURATION = 60.0
race_timer = RACE_DURATION
winner = None
winner_message = ""

shop_open_p1 = False
shop_open_p2 = False
shop_anim_p1 = 0.0
shop_anim_p2 = 0.0
shop_scroll_p1 = 0
shop_scroll_p2 = 0
PANEL_W = 420
SHOP_ITEM_H = 72
SHOP_VIEW_TOP = 175
SHOP_VIEW_BOTTOM = HEIGHT - 20

confirm_reset = False

SHOP_BTN_P1 = ed.Rect(PLAYER1_X - 110, 600, 220, 55)
SHOP_BTN_P2 = ed.Rect(PLAYER2_X - 110, 600, 220, 55)

def get_max_scroll():
    visible = SHOP_VIEW_BOTTOM - SHOP_VIEW_TOP
    total = get_active_count() * SHOP_ITEM_H
    return max(0, total - visible)

def reset_effects():
    global event_timer, autosave_timer, double_time, mega_click_time
    global freeze_time, auto_boom_time, auto_mega_time
    global temp_crit_time, temp_power_time, shield_active
    global event_message, event_message_timer, race_timer, popups
    global shop_scroll_p1, shop_scroll_p2
    global achievement_banner, achievement_banner_timer, achievements_scroll
    event_timer = EVENT_INTERVAL; autosave_timer = AUTOSAVE_INTERVAL
    double_time = 0.0; mega_click_time = 0.0; freeze_time = 0.0
    auto_boom_time = 0.0; auto_mega_time = 0.0
    temp_crit_time = 0.0; temp_power_time = 0.0
    shield_active = False; event_message = ""; event_message_timer = 0.0
    race_timer = RACE_DURATION
    shop_scroll_p1 = 0; shop_scroll_p2 = 0
    achievement_banner = ""; achievement_banner_timer = 0.0
    achievements_scroll = 0
    popups = []

def start_match(mode):
    """Запускает режим.
       comp/race: делает снимок свободных игроков и стартует с чистых.
       free:      восстанавливает игроков из снимка (если есть)."""
    global state, p1, p2, winner, winner_message, net_is_online
    global shop_open_p1, shop_open_p2, shop_anim_p1, shop_anim_p2, race_timer
    global free_p1_snapshot, free_p2_snapshot

    was_online = net_is_online

    if not was_online:
        if mode in ("comp", "race"):
            # Уходим из free — сохраняем прогресс
            if free_p1_snapshot is None:
                free_p1_snapshot = p1
                free_p2_snapshot = p2
        elif mode == "free":
            # Возвращаемся в free — восстанавливаем
            if free_p1_snapshot is not None:
                p1 = free_p1_snapshot
                p2 = free_p2_snapshot
                free_p1_snapshot = None
                free_p2_snapshot = None

    # Сбрасываем флаг онлайн только для оффлайн-режимов
    if mode != "online" and not net_connected:
        net_is_online = False

    # Свежие игроки для comp/race (оффлайн)
    if mode in ("comp", "race") and not was_online:
        p1 = make_player()
        p2 = make_player()

    reset_effects()
    winner = None; winner_message = ""
    shop_open_p1 = False; shop_open_p2 = False
    shop_anim_p1 = 0.0; shop_anim_p2 = 0.0
    race_timer = RACE_DURATION
    state = mode

load_game()
if playlist: play_track(current_track)

def check_achievements():
    global achievement_banner, achievement_banner_timer, achievement_banner_player
    if net_is_online:
        if net_my_num == 1:
            targets = [(1, p1, unlocked_achievements_p1)]
        else:
            targets = [(2, p2, unlocked_achievements_p2)]
    else:
        targets = [(1, p1, unlocked_achievements_p1),
                   (2, p2, unlocked_achievements_p2)]

    for pnum, p, bag in targets:
        for ach in ACHIEVEMENTS:
            if ach["id"] in bag: continue
            try:
                if ach["check"](p):
                    bag.add(ach["id"])
                    achievement_banner = f"{ach['name']}  —  Игрок {pnum}!"
                    achievement_banner_player = pnum
                    achievement_banner_timer = 4.0
            except Exception:
                pass

def get_panel_p1_rect():
    x = -PANEL_W + int(PANEL_W * shop_anim_p1)
    return ed.Rect(x, 0, PANEL_W, HEIGHT)

def get_panel_p2_rect():
    x = WIDTH - int(PANEL_W * shop_anim_p2)
    return ed.Rect(x, 0, PANEL_W, HEIGHT)

def panel_upgrade_rect(panel_left_x, idx, scroll):
    y = SHOP_VIEW_TOP + idx * SHOP_ITEM_H - scroll
    return ed.Rect(panel_left_x + 20, y, PANEL_W - 40, SHOP_ITEM_H - 8)

# ============================================================
# РАСЧЁТ УРОНА
# ============================================================
def compute_damage(player, opponent):
    dmg = player["power"] * player["mult"] * player["mega_mult"]
    synergy = player.get("symbiosis", 0.0) + player.get("fusion", 0.0)
    if synergy > 0 and player["auto"] > 0:
        dmg += player["auto"] * player["auto_mult"] * synergy
    if temp_power_time > 0: dmg += 5
    if double_time > 0:     dmg *= 2
    if mega_click_time > 0: dmg *= 5
    if player.get("combo", 0) > 0 and player.get("combo_timer", 0) > 0:
        bonus = min(player.get("combo_max", 1.5), player["combo"] * player.get("combo_value", 0.0))
        dmg *= (1 + bonus)
    if player.get("berserk", 1.0) > 1.0 and player["score"] < opponent["score"]:
        dmg *= player["berserk"]
    if player.get("resonance", 1.0) > 1.0 and player["score"] < opponent["score"]:
        dmg *= player["resonance"]
    if player.get("phoenix", 1.0) > 1.0 and player["score"] < 100:
        dmg *= player["phoenix"]
    if player.get("patience_value", 0.0) > 0 and player.get("patience_timer", 0) > 0:
        bonus = min(1.5, player["patience_timer"] * player["patience_value"])
        dmg *= (1 + bonus)
    if player.get("gambit", 0.0) > 0:
        dmg *= (1 + player["gambit"])
    crit_chance = player["crit"] + player.get("crit_stack", 0.0) + \
                  (0.10 if temp_crit_time > 0 else 0.0)
    is_crit = random.random() < crit_chance
    if is_crit: dmg *= player["crit_mult"]
    if player.get("sniper_chance", 0.0) > 0 and random.random() < player["sniper_chance"]:
        dmg *= player.get("sniper_mult", 20)
    if player.get("lottery_chance", 0.0) > 0 and random.random() < player["lottery_chance"]:
        dmg *= player.get("lottery_mult", 50)
    is_boom = False
    n = player.get("boom_every", 0)
    if n > 0 and (player.get("click_counter", 0) + 1) % n == 0:
        dmg *= player.get("boom_mult", 10); is_boom = True
    is_typhoon = False
    if player.get("typhoon_ready", False):
        dmg *= player.get("typhoon_mult", 5); is_typhoon = True
    is_golden = False
    gch = player["golden_chance"] + player.get("gold_magnet", 0.0)
    if player["golden"] > 0:
        dmg *= player["golden_mult"]; player["golden"] -= 1; is_golden = True
    elif random.random() < gch:
        dmg *= player["golden_mult"]; is_golden = True
    if is_golden:
        player["golden_caught"] = player.get("golden_caught", 0) + 1
    if is_golden and player.get("jackpot", 0.0) > 0 and random.random() < player["jackpot"]:
        dmg *= player["golden_mult"]
    return max(1, int(dmg)), is_crit, is_golden, is_boom, is_typhoon

def do_click(player, pos, color):
    opponent = p2 if player is p1 else p1
    if freeze_time > 0:
        popups.append({"pos": [pos[0], pos[1]], "life": 40, "alpha": 255,
                       "text": "❄️", "color": (150, 200, 255)})
        return
    cost = 1 if player.get("gambit", 0.0) > 0 else 0
    if player["score"] < cost: return
    player["score"] -= cost
    dmg, is_crit, is_golden, is_boom, is_typhoon = compute_damage(player, opponent)
    player["score"] += dmg
    player["scale"] = 0.9
    player["total_clicks"] = player.get("total_clicks", 0) + 1
    player["click_counter"] = player.get("click_counter", 0) + 1
    player["combo"] = player.get("combo", 0) + 1
    player["combo_timer"] = 1.0
    if player["combo"] > player.get("max_combo", 0): player["max_combo"] = player["combo"]
    player["patience_timer"] = 0.0
    if is_crit: player["crit_stack"] = 0.0
    else:
        if player.get("crit_luck", 0.0) > 0:
            player["crit_stack"] = min(0.5, player.get("crit_stack", 0.0) + player["crit_luck"])
    if player.get("speedup_value", 0.0) > 0:
        player["speedup_bonus"] = min(player.get("speedup_max", 1.5),
                                      player.get("speedup_bonus", 0.0) + player["speedup_value"])
        player["speedup_timer"] = 5.0
    if player.get("vampirism", 0.0) > 0:
        player["auto_acc"] += dmg * player["vampirism"]
    tn = player.get("typhoon_every", 0)
    if tn > 0 and player["click_counter"] % tn == 0: player["typhoon_ready"] = True
    if is_typhoon: player["typhoon_ready"] = False
    cn = player.get("chain_every", 0)
    if cn > 0 and player["click_counter"] % cn == 0:
        player["power"] += 1
        popups.append({"pos": [pos[0], pos[1] - 30], "life": 70, "alpha": 255,
                       "text": "⛓️ +1 СИЛА", "color": (200, 255, 200)})
    if player.get("overdrive", 0.0) > 0 and random.random() < player["overdrive"]:
        count = get_active_count(); idx = random.randint(0, count - 1)
        if player["levels"][idx] < MAX_LEVEL:
            player["levels"][idx] += 1
            apply_effect(player, UPGRADES[idx])
            popups.append({"pos": [pos[0], pos[1] - 55], "life": 80, "alpha": 255,
                           "text": f"⚡ БОНУС: {UPGRADES[idx]['name']}!",
                           "color": COLOR_EXTRA})
    if is_typhoon:   text = f"🌊 ТАЙФУН! +{dmg}"
    elif is_boom:    text = f"💥 ВЗРЫВ! +{dmg}"
    elif is_golden:  text = f"🌟 +{dmg}"
    elif is_crit:    text = f"КРИТ! +{dmg}"
    else:            text = f"+{dmg}"
    popups.append({"pos": [pos[0], pos[1]], "life": 60, "alpha": 255,
                   "text": text, "color": color})
    if player.get("echo", 0.0) > 0 and random.random() < player["echo"]:
        dmg2, _, _, _, _ = compute_damage(player, opponent)
        player["score"] += dmg2
        popups.append({"pos": [pos[0] + 40, pos[1] - 25], "life": 50, "alpha": 255,
                       "text": f"🔁 +{dmg2}", "color": (200, 150, 255)})

def apply_effect(player, upg):
    eff = upg["effect"]; val = upg["value"]
    if eff == "power":          player["power"] += int(val)
    elif eff == "auto":         player["auto"] += int(val)
    elif eff == "mult":         player["mult"] *= val
    elif eff == "crit":         player["crit"] = min(1.0, player["crit"] + val)
    elif eff == "crit_mult":    player["crit_mult"] += val
    elif eff == "auto_mult":    player["auto_mult"] += val
    elif eff == "golden_chance":player["golden_chance"] = min(1.0, player["golden_chance"] + val)
    elif eff == "mega_mult":    player["mega_mult"] *= val
    elif eff == "combo":        player["combo_value"] += val
    elif eff == "boom":         player["boom_every"] = int(val)
    elif eff == "echo":         player["echo"] = min(0.9, player["echo"] + val)
    elif eff == "berserk":      player["berserk"] *= val
    elif eff == "vampirism":    player["vampirism"] += val
    elif eff == "gold_magnet":  player["gold_magnet"] += val
    elif eff == "crit_luck":    player["crit_luck"] += val
    elif eff == "jackpot":      player["jackpot"] += val
    elif eff == "speedup":      player["speedup_value"] += val
    elif eff == "reactor":      player["reactor_interval"] = val
    elif eff == "symbiosis":    player["symbiosis"] += val
    elif eff == "shield_regen": player["shield_regen"] = val
    elif eff == "curse":        player["curse"] += val
    elif eff == "lottery":      player["lottery_chance"] += val
    elif eff == "crystal":      player["crystal"] += int(val)
    elif eff == "discount":     player["discount"] = min(0.6, player["discount"] + val)
    elif eff == "immunity":     player["immunity"] = min(0.9, player["immunity"] + val)
    elif eff == "gambit":       player["gambit"] += val
    elif eff == "chain":        player["chain_every"] = int(val)
    elif eff == "phoenix":      player["phoenix"] *= val
    elif eff == "harmony":      player["harmony"] += val
    elif eff == "resonance":    player["resonance"] *= val
    elif eff == "patience":     player["patience_value"] += val
    elif eff == "sniper":       player["sniper_chance"] += val
    elif eff == "protection":   player["protection"] = min(0.9, player["protection"] + val)
    elif eff == "fusion":       player["fusion"] += val
    elif eff == "typhoon":      player["typhoon_every"] = int(val)
    elif eff == "wisdom":       player["wisdom"] *= val
    elif eff == "overdrive":    player["overdrive"] = min(0.1, player["overdrive"] + val)

def buy(player, idx):
    if idx < 0 or idx >= get_active_count(): return False
    if player["levels"][idx] >= MAX_LEVEL: return False
    discount = player.get("discount", 0.0)
    cost = int(player["costs"][idx] * (1 - discount))
    if player["score"] < cost: return False
    player["score"] -= cost
    player["levels"][idx] += 1
    player["costs"][idx] = int(player["costs"][idx] * UPGRADES[idx]["mult"])
    apply_effect(player, UPGRADES[idx])
    check_achievements()
    return True

# ============================================================
# СОБЫТИЯ
# ============================================================
def trigger_event():
    global event_message, event_message_timer
    global double_time, mega_click_time, freeze_time
    global auto_boom_time, auto_mega_time, temp_crit_time, temp_power_time
    global shield_active
    evt = random.choice([
        "bonus", "bigbonus", "double", "mega", "penalty", "bigpenalty",
        "gift", "golden", "supergolden", "autoboom", "automega",
        "freeze", "swap", "power", "megapower", "autoclick",
        "robbery", "lucky", "chaos", "shield"
    ])
    if evt in ("penalty", "bigpenalty", "robbery", "freeze") and shield_active:
        shield_active = False
        event_message = "🛡️ ЩИТ отразил негативное событие!"
        event_message_timer = 3.5; return
    if evt in ("penalty", "bigpenalty", "robbery", "freeze"):
        for pl in (p1, p2):
            if pl.get("immunity", 0.0) > 0 and random.random() < pl["immunity"]:
                event_message = "🧿 ИММУНИТЕТ! Негатив проигнорирован"
                event_message_timer = 3.5; return
    mult = max(p1.get("wisdom", 1.0), p2.get("wisdom", 1.0))
    prot = 1.0 - max(p1.get("protection", 0.0), p2.get("protection", 0.0))
    def add_bonus(amount):    return int(amount * mult)
    def take_penalty(amount): return int(amount * mult * prot)
    if evt == "bonus":
        b = add_bonus(50); p1["score"] += b; p2["score"] += b
        event_message = f"🎁 БОНУС! +{b} каждому"
    elif evt == "bigbonus":
        b = add_bonus(200); p1["score"] += b; p2["score"] += b
        event_message = f"💰 БОЛЬШОЙ БОНУС! +{b} каждому"
    elif evt == "double":
        double_time = 10.0 * mult; event_message = f"⚡ X2 КЛИКИ НА {double_time:.0f} СЕКУНД!"
    elif evt == "mega":
        mega_click_time = 5.0 * mult; event_message = f"🔥 МЕГА! X5 КЛИКИ НА {mega_click_time:.0f} СЕКУНД!"
    elif evt == "penalty":
        v = take_penalty(30)
        p1["score"] = max(0, p1["score"] - v); p2["score"] = max(0, p2["score"] - v)
        event_message = f"💀 ШТРАФ! -{v} каждому"
    elif evt == "bigpenalty":
        v = take_penalty(100)
        p1["score"] = max(0, p1["score"] - v); p2["score"] = max(0, p2["score"] - v)
        event_message = f"☠️ БОЛЬШОЙ ШТРАФ! -{v} каждому"
    elif evt == "gift":
        b = add_bonus(100)
        if p1["score"] > p2["score"]:
            p2["score"] += b; event_message = f"🎈 ПОДАРОК: игрок 2 получает {b}!"
        elif p2["score"] > p1["score"]:
            p1["score"] += b; event_message = f"🎈 ПОДАРОК: игрок 1 получает {b}!"
        else:
            h = add_bonus(50); p1["score"] += h; p2["score"] += h
            event_message = f"🎈 Ничья! +{h} каждому"
    elif evt == "golden":
        p1["golden"] += 1; p2["golden"] += 1
        event_message = "🌟 ЗОЛОТОЙ КЛИК! Следующий клик x10"
    elif evt == "supergolden":
        p1["golden"] += 5; p2["golden"] += 5
        event_message = "✨ СУПЕР-ЗОЛОТО! 5 зарядов x10 каждому"
    elif evt == "autoboom":
        auto_boom_time = 10.0; event_message = "🏃 АВТОБУМ! Автоклик x3 на 10 сек"
    elif evt == "automega":
        auto_mega_time = 5.0; event_message = "🚀 АВТО-МЕГА! Автоклик x10 на 5 сек"
    elif evt == "freeze":
        freeze_time = 3.0; event_message = "❄️ ЗАМОРОЗКА! Клики отключены на 3 сек"
    elif evt == "swap":
        p1["score"], p2["score"] = p2["score"], p1["score"]
        event_message = "🔄 ОБМЕН! Счета поменялись местами"
    elif evt == "power":
        p = int(5 * mult); p1["power"] += p; p2["power"] += p
        event_message = f"💎 +{p} к силе клика каждому"
    elif evt == "megapower":
        p = int(15 * mult); p1["power"] += p; p2["power"] += p
        event_message = f"💠 МЕГА-СИЛА! +{p} к силе клика каждому"
    elif evt == "autoclick":
        p = int(5 * mult); p1["auto"] += p; p2["auto"] += p
        event_message = f"⏩ +{p} автокликов каждому"
    elif evt == "robbery":
        if p1["score"] > p2["score"]:
            stolen = int(p1["score"] // 5 * prot)
            p1["score"] -= stolen; p2["score"] += stolen
            event_message = f"☠️ ОГРАБЛЕНИЕ! У игрока 1 украдено {stolen}"
        elif p2["score"] > p1["score"]:
            stolen = int(p2["score"] // 5 * prot)
            p2["score"] -= stolen; p1["score"] += stolen
            event_message = f"☠️ ОГРАБЛЕНИЕ! У игрока 2 украдено {stolen}"
        else:
            event_message = "☠️ ОГРАБЛЕНИЕ провалилось — ничья"
    elif evt == "lucky":
        temp_crit_time = 15.0; event_message = "🍀 УДАЧА! +10% крит на 15 сек"
    elif evt == "chaos":
        d1 = random.randint(-80, 150); d2 = random.randint(-80, 150)
        p1["score"] = max(0, p1["score"] + d1); p2["score"] = max(0, p2["score"] + d2)
        event_message = f"🎲 ХАОС! Игрок1 {d1:+d}, Игрок2 {d2:+d}"
    elif evt == "shield":
        shield_active = True; event_message = "🛡️ ЩИТ! След. негативное событие отражено"
    event_message_timer = 3.5

# ============================================================
# СЕТЕВАЯ ИГРА
# ============================================================
NET_PORT_DEFAULT = 5050
DISCOVERY_PORT = 5051
DISCOVERY_MAGIC = "CLICKER_SERVER_V1"

net_socket = None
net_role = None
net_connected = False
net_recv_q = queue.Queue()
net_opponent_state = {}
net_status_msg = ""
net_is_online = False
net_my_num = 1
net_last_send = 0.0
NET_SEND_INTERVAL = 1.0 / 30.0

net_ip_input = ""
net_input_active = False
net_manual_mode = False

discovered_servers = {}
discovery_sock = None
discovery_running = False
broadcasting = False
server_name = (socket.gethostname() or "ClickerServer")[:18]
pending_mode = None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return "127.0.0.1"

def start_discovery_listener():
    global discovery_sock, discovery_running
    if discovery_running: return
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try: s.bind(("", DISCOVERY_PORT))
        except Exception: s.bind(("0.0.0.0", DISCOVERY_PORT))
        s.settimeout(1.0)
        discovery_sock = s; discovery_running = True
        def loop():
            while discovery_running:
                try:
                    data, addr = s.recvfrom(1024)
                except socket.timeout:
                    continue
                except Exception:
                    break
                try:
                    msg = data.decode("utf-8", errors="ignore").strip()
                    if not msg.startswith(DISCOVERY_MAGIC): continue
                    parts = msg.split("|")
                    if len(parts) < 3: continue
                    name = parts[1]; port = int(parts[2]); ip = addr[0]
                    if ip == get_local_ip() and net_role == "host": continue
                    discovered_servers[ip] = {
                        "name": name, "port": port,
                        "last_seen": _time.time(), "ip": ip,
                    }
                except Exception: pass
        threading.Thread(target=loop, daemon=True).start()
    except Exception as e:
        print("discovery listener error:", e)

def stop_discovery_listener():
    global discovery_sock, discovery_running
    discovery_running = False
    if discovery_sock:
        try: discovery_sock.close()
        except Exception: pass
        discovery_sock = None

def start_broadcaster(name, port):
    global broadcasting
    if broadcasting: return
    broadcasting = True
    def loop():
        global broadcasting
        bs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        bs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = f"{DISCOVERY_MAGIC}|{name}|{port}".encode("utf-8")
        while broadcasting:
            try: bs.sendto(msg, ("255.255.255.255", DISCOVERY_PORT))
            except Exception: pass
            _time.sleep(1.0)
        try: bs.close()
        except Exception: pass
    threading.Thread(target=loop, daemon=True).start()

def stop_broadcaster():
    global broadcasting
    broadcasting = False

def clean_stale_servers():
    now = _time.time()
    to_remove = [ip for ip, info in discovered_servers.items()
                 if now - info.get("last_seen", 0) > 3.5]
    for ip in to_remove:
        del discovered_servers[ip]

def net_reset():
    global net_socket, net_role, net_connected, net_opponent_state
    global net_status_msg, net_is_online, net_my_num
    net_connected = False
    if net_socket:
        try: net_socket.close()
        except Exception: pass
    net_socket = None
    net_role = None
    net_opponent_state = {}
    net_status_msg = ""
    net_is_online = False
    net_my_num = 1
    stop_broadcaster()
    while not net_recv_q.empty():
        try: net_recv_q.get_nowait()
        except Exception: break

def net_recv_loop():
    global net_connected
    buf = b""
    try:
        while net_connected and net_socket is not None:
            try: data = net_socket.recv(8192)
            except Exception: break
            if not data: break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    msg = json.loads(line.decode("utf-8"))
                    net_recv_q.put(msg)
                except Exception: pass
    except Exception as e:
        print("net_recv error:", e)
    net_connected = False

def net_send(msg):
    if not net_connected or net_socket is None: return
    try:
        data = (json.dumps(msg) + "\n").encode("utf-8")
        net_socket.sendall(data)
    except Exception as e:
        print("net_send error:", e)

def net_host(port=NET_PORT_DEFAULT):
    global net_socket, net_role, net_status_msg
    net_reset()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        s.listen(1)
        s.settimeout(1.0)
        net_socket = s
        net_role = "host"
        net_status_msg = f"Ждём подключения (порт {port})..."
        start_broadcaster(server_name, port)
        def accept_loop():
            global net_socket, net_connected, net_status_msg, net_my_num
            while net_role == "host" and not net_connected:
                try: conn, addr = s.accept()
                except socket.timeout: continue
                except Exception: break
                net_socket = conn; net_connected = True; net_my_num = 1
                net_status_msg = f"Подключён: {addr[0]}"
                stop_broadcaster(); break
            if net_connected: net_recv_loop()
        threading.Thread(target=accept_loop, daemon=True).start()
        return True
    except Exception as e:
        net_status_msg = f"Ошибка хоста: {e}"
        return False

def net_join(host_ip, port=NET_PORT_DEFAULT):
    global net_socket, net_role, net_status_msg, net_connected, net_my_num
    net_reset()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((host_ip, port))
        s.settimeout(None)
        net_socket = s; net_role = "client"
        net_connected = True; net_my_num = 2
        net_status_msg = f"Подключено к {host_ip}"
        threading.Thread(target=net_recv_loop, daemon=True).start()
        return True
    except Exception as e:
        net_status_msg = f"Ошибка подключения: {e}"
        return False

def net_state_dict(p):
    keys = ["score", "power", "auto", "mult", "crit", "crit_mult",
            "auto_mult", "golden_chance", "golden_mult", "mega_mult",
            "levels", "costs"]
    return {k: p[k] for k in keys if k in p}

def net_pump():
    global net_opponent_state, net_connected, net_status_msg, pending_mode
    while not net_recv_q.empty():
        try: msg = net_recv_q.get_nowait()
        except queue.Empty: break
        t = msg.get("type")
        if t == "state":
            net_opponent_state = msg.get("data", {})
        elif t == "bye":
            net_connected = False
            net_status_msg = "Противник отключился"
        elif t == "start_mode":
            pending_mode = {
                "mode": msg.get("mode", "free"),
                "target": msg.get("target", 5000),
            }
    if not net_opponent_state: return
    opp = p2 if net_my_num == 1 else p1
    d = net_opponent_state
    for k in ("score", "power", "auto", "mult", "crit", "crit_mult",
              "auto_mult", "golden_chance", "golden_mult", "mega_mult"):
        if k in d:
            try: opp[k] = d[k]
            except Exception: pass
    if "levels" in d:
        for i, v in enumerate(d["levels"]):
            if i < len(opp["levels"]): opp["levels"][i] = v
    if "costs" in d:
        for i, v in enumerate(d["costs"]):
            if i < len(opp["costs"]): opp["costs"][i] = v

def net_send_local_state():
    global net_last_send
    now = _time.time()
    if now - net_last_send < NET_SEND_INTERVAL: return
    net_last_send = now
    local = p1 if net_my_num == 1 else p2
    net_send({"type": "state", "data": net_state_dict(local)})

start_discovery_listener()

# ============================================================
# МЕНЮ
# ============================================================
MENU_BUTTONS = [
    {"state": "free", "label": "СВОБОДНЫЙ РЕЖИМ",
     "sub": "Сохранения · события · 8 + 29 уникальных прокачек",
     "color": COLOR_P1, "rect": ed.Rect(60, 200, 720, 100)},
    {"state": "comp_setup", "label": "СОРЕВНОВАНИЕ",
     "sub": "Первый, кто наберёт заданную цель",
     "color": COLOR_GOLD, "rect": ed.Rect(60, 320, 720, 100)},
    {"state": "race", "label": "ГОНКА 60 СЕКУНД",
     "sub": "Кто больше наберёт за минуту",
     "color": COLOR_GREEN, "rect": ed.Rect(60, 440, 720, 100)},
]

COMP_PRESETS = [1000, 5000, 10000, 50000]
COMP_PRESET_RECTS = []
for i, amount in enumerate(COMP_PRESETS):
    r = ed.Rect(WIDTH//2 - 800 + i * 410, 340, 380, 160)
    COMP_PRESET_RECTS.append((r, amount))

MUSIC_BTN_PREV     = ed.Rect(0, 0, 0, 0)
MUSIC_BTN_PAUSE    = ed.Rect(0, 0, 0, 0)
MUSIC_BTN_NEXT     = ed.Rect(0, 0, 0, 0)
MUSIC_BTN_VOL_UP   = ed.Rect(0, 0, 0, 0)
MUSIC_BTN_VOL_DOWN = ed.Rect(0, 0, 0, 0)
MUSIC_BTN_LOAD     = ed.Rect(0, 0, 0, 0)

NET_PANEL    = ed.Rect(WIDTH - 400, 140, 360, 640)
NET_HOST_BTN = ed.Rect(NET_PANEL.x + 20, NET_PANEL.y + 55,  320, 50)
NET_LIST_LBL_Y = NET_PANEL.y + 120
NET_LIST_RECT  = ed.Rect(NET_PANEL.x + 20, NET_PANEL.y + 145, 320, 280)
NET_MANUAL_BTN = ed.Rect(NET_PANEL.x + 20, NET_PANEL.y + 440, 320, 34)
NET_IP_RECT    = ed.Rect(NET_PANEL.x + 20, NET_PANEL.y + 482, 320, 46)
NET_JOIN_BTN   = ed.Rect(NET_PANEL.x + 20, NET_PANEL.y + 534, 320, 46)

NET_FREE_BTN  = ed.Rect(NET_PANEL.x + 20, NET_PANEL.y + 160, 320, 46)
NET_COMP_BTN  = ed.Rect(NET_PANEL.x + 20, NET_PANEL.y + 216, 320, 46)
NET_RACE_BTN  = ed.Rect(NET_PANEL.x + 20, NET_PANEL.y + 272, 320, 46)
NET_LEAVE_BTN = ed.Rect(NET_PANEL.x + 20, NET_PANEL.y + 340, 320, 40)

SERVER_ROW_H = 52
SERVER_LIST_VISIBLE = 5

def server_row_rect(idx):
    return ed.Rect(NET_LIST_RECT.x + 4,
                   NET_LIST_RECT.y + 4 + idx * SERVER_ROW_H,
                   NET_LIST_RECT.width - 8,
                   SERVER_ROW_H - 6)

# ============================================================
# ОТРИСОВКА
# ============================================================
def draw_player_column(px, player, color, shop_btn, shop_open):
    s = font_big.render(f"Игрок {1 if px == PLAYER1_X else 2}: {player['score']}", True, color)
    screen.blit(s, s.get_rect(center=(px, 45)))
    w = int(260 * player["scale"])
    img = button_img if px == PLAYER1_X else button_img2
    scaled = ed.transform.smoothscale(img, (w, w))
    screen.blit(scaled, scaled.get_rect(center=(px, 320)))
    info = (f"Сила:{player['power']}  Авто:{player['auto']}/с  "
            f"Множ:x{player['mult']:.2f}  Крит:{int(player['crit']*100)}%")
    if player["golden"] > 0: info += f"  🌟x{player['golden']}"
    t = font_mini.render(info, True, (200, 200, 200))
    screen.blit(t, t.get_rect(center=(px, 470)))
    bg = (60, 80, 120) if shop_open else (40, 40, 60)
    ed.draw.rect(screen, bg, shop_btn, border_radius=12)
    ed.draw.rect(screen, color, shop_btn, 3, border_radius=12)
    t = font_small.render("🛒 МАГАЗИН", True, color)
    screen.blit(t, t.get_rect(center=shop_btn.center))

def draw_shop_panel(panel_rect, player, color, scroll):
    if panel_rect.right <= 0 or panel_rect.left >= WIDTH: return
    ed.draw.rect(screen, COLOR_PANEL_BG, panel_rect)
    if panel_rect.x <= 0:
        ed.draw.line(screen, color, (panel_rect.right - 1, 0), (panel_rect.right - 1, HEIGHT), 4)
    else:
        ed.draw.line(screen, color, (panel_rect.x, 0), (panel_rect.x, HEIGHT), 4)
    title = font_big.render("МАГАЗИН", True, color)
    screen.blit(title, title.get_rect(center=(panel_rect.centerx, 45)))
    discount = player.get("discount", 0.0)
    disc_txt = f"  (−{int(discount*100)}%)" if discount > 0 else ""
    sc = font_mid.render(f"💰 {player['score']}{disc_txt}", True, COLOR_GOLD)
    screen.blit(sc, sc.get_rect(center=(panel_rect.centerx, 100)))
    count = get_active_count(); maxed_cnt = _count_maxed(player)
    mode_hint = (f"Свободный режим · {count} прокачек · MAX: {maxed_cnt}"
                 if state == "free" else f"8 базовых · MAX: {maxed_cnt}")
    t = font_mini.render(mode_hint, True, (160, 160, 190))
    screen.blit(t, t.get_rect(center=(panel_rect.centerx, 140)))
    clip = ed.Rect(panel_rect.x, SHOP_VIEW_TOP, panel_rect.width, SHOP_VIEW_BOTTOM - SHOP_VIEW_TOP)
    old_clip = screen.get_clip()
    screen.set_clip(clip)
    px = panel_rect.x
    for i in range(count):
        rect = panel_upgrade_rect(px, i, scroll)
        if rect.bottom < SHOP_VIEW_TOP or rect.top > SHOP_VIEW_BOTTOM: continue
        upg = UPGRADES[i]; lvl = player["levels"][i]
        is_max = lvl >= MAX_LEVEL; is_extra = i >= BASE_COUNT
        discount = player.get("discount", 0.0)
        cost = int(player["costs"][i] * (1 - discount))
        affordable = (not is_max) and player["score"] >= cost
        if is_max:       bg = (70, 50, 20)
        elif affordable: bg = (COLOR_BTN_BG_OK if color == COLOR_P1 else COLOR_BTN_BG_OK2)
        else:            bg = COLOR_BTN_BG
        ed.draw.rect(screen, bg, rect, border_radius=10)
        border = COLOR_MAX if is_max else (color if affordable else (80, 80, 100))
        ed.draw.rect(screen, border, rect, 2 if not is_max else 3, border_radius=10)
        if is_extra and not is_max:
            ed.draw.rect(screen, COLOR_EXTRA, rect, 3, border_radius=10)
        if is_max:      name_col = COLOR_MAX
        elif is_extra:  name_col = COLOR_EXTRA
        else:           name_col = color
        lvl_txt = f"MAX" if is_max else f"ур.{lvl}"
        name = font_small.render(f"{i+1}. {upg['name']} {lvl_txt}", True, name_col)
        screen.blit(name, (rect.x + 12, rect.y + 6))
        bar_x, bar_y = rect.x + 12, rect.y + 50
        bar_w2, bar_h2 = rect.width - 24, 8
        ed.draw.rect(screen, (50, 50, 70), (bar_x, bar_y, bar_w2, bar_h2), border_radius=4)
        ratio = min(1.0, lvl / MAX_LEVEL)
        bar_col = COLOR_MAX if is_max else (color if affordable else (100, 100, 130))
        ed.draw.rect(screen, bar_col, (bar_x, bar_y, int(bar_w2 * ratio), bar_h2), border_radius=4)
        if is_max:
            cost_t = font_small.render("✔ MAX", True, COLOR_MAX)
        else:
            cost_color = COLOR_GOLD if affordable else (140, 140, 140)
            cost_t = font_small.render(f"{cost}", True, cost_color)
        screen.blit(cost_t, (rect.right - cost_t.get_width() - 12, rect.y + 20))
    screen.set_clip(old_clip)
    max_scroll = get_max_scroll()
    if max_scroll > 0:
        track = ed.Rect(panel_rect.right - 12, SHOP_VIEW_TOP, 6, SHOP_VIEW_BOTTOM - SHOP_VIEW_TOP)
        ed.draw.rect(screen, (50, 50, 70), track, border_radius=3)
        visible = SHOP_VIEW_BOTTOM - SHOP_VIEW_TOP
        total = count * SHOP_ITEM_H
        bar_h = max(30, int(visible * visible / total))
        bar_y = SHOP_VIEW_TOP + int((visible - bar_h) * (scroll / max_scroll))
        ed.draw.rect(screen, color, ed.Rect(track.x, bar_y, track.width, bar_h), border_radius=3)

def draw_effects():
    y = 110; effects = []
    if double_time > 0:     effects.append((f"⚡ X2: {double_time:.1f}с", (255, 100, 255)))
    if mega_click_time > 0: effects.append((f"🔥 X5: {mega_click_time:.1f}с", (255, 150, 50)))
    if auto_boom_time > 0:  effects.append((f"🏃 АВТОБУМ: {auto_boom_time:.1f}с", (100, 255, 150)))
    if auto_mega_time > 0:  effects.append((f"🚀 АВТО-МЕГА: {auto_mega_time:.1f}с", (100, 255, 255)))
    if freeze_time > 0:     effects.append((f"❄️ ЗАМОРОЗКА: {freeze_time:.1f}с", (150, 200, 255)))
    if temp_crit_time > 0:  effects.append((f"🍀 УДАЧА: {temp_crit_time:.1f}с", (150, 255, 150)))
    if temp_power_time > 0: effects.append((f"💪 СИЛА: {temp_power_time:.1f}с", (255, 220, 100)))
    if shield_active:       effects.append(("🛡️ ЩИТ активен", (200, 200, 255)))
    for text, color in effects:
        t = font_small.render(text, True, color)
        screen.blit(t, t.get_rect(center=(WIDTH // 2, y))); y += 30

def draw_popups():
    for p in popups[:]:
        p["life"] -= 1; p["pos"][1] -= 1.5
        p["alpha"] = max(0, int(255 * (p["life"] / 60)))
        surf = font_small.render(p["text"], True, p["color"])
        surf.set_alpha(p["alpha"]); screen.blit(surf, p["pos"])
        if p["life"] <= 0: popups.remove(p)

def draw_event_message():
    if event_message_timer > 0:
        alpha = min(255, int(event_message_timer * 255))
        msg = font_mid.render(event_message, True, COLOR_GOLD)
        msg.set_alpha(alpha)
        screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT - 90)))

def draw_confirm_reset():
    overlay = ed.Surface((WIDTH, HEIGHT), ed.SRCALPHA)
    overlay.fill((0, 0, 0, 180)); screen.blit(overlay, (0, 0))
    box_w, box_h = 900, 340
    box = ed.Rect(WIDTH // 2 - box_w // 2, HEIGHT // 2 - box_h // 2, box_w, box_h)
    ed.draw.rect(screen, (40, 20, 30), box, border_radius=20)
    ed.draw.rect(screen, COLOR_RED, box, 4, border_radius=20)
    t1 = font_big.render("⚠️ СТЕРЕТЬ ПРОГРЕСС?", True, COLOR_RED)
    screen.blit(t1, t1.get_rect(center=(WIDTH // 2, box.y + 70)))
    t2 = font_mid.render("Прогресс, достижения и save.json будут удалены!", True, (255, 220, 220))
    screen.blit(t2, t2.get_rect(center=(WIDTH // 2, box.y + 150)))
    t3 = font_small.render("Y / ENTER — подтвердить    |    N / ESC — отмена", True, COLOR_GOLD)
    screen.blit(t3, t3.get_rect(center=(WIDTH // 2, box.y + 230)))
    if (ed.time.get_ticks() // 400) % 2:
        t4 = font_tiny.render("Это действие необратимо!", True, (255, 120, 120))
        screen.blit(t4, t4.get_rect(center=(WIDTH // 2, box.y + 290)))

def draw_achievement_banner():
    if achievement_banner_timer <= 0: return
    alpha = min(255, int(achievement_banner_timer * 80))
    bc = COLOR_P1 if achievement_banner_player == 1 else COLOR_P2
    bw, bh = 800, 90
    bx = WIDTH // 2 - bw // 2; by = 210
    surf = ed.Surface((bw, bh), ed.SRCALPHA); surf.fill((0, 0, 0, 180))
    screen.blit(surf, (bx, by))
    ed.draw.rect(screen, COLOR_GOLD, (bx, by, bw, bh), 3, border_radius=15)
    t1 = font_mid.render("🏆 ДОСТИЖЕНИЕ!", True, COLOR_GOLD); t1.set_alpha(alpha)
    screen.blit(t1, t1.get_rect(center=(WIDTH // 2, by + 25)))
    t2 = font_small.render(achievement_banner, True, bc); t2.set_alpha(alpha)
    screen.blit(t2, t2.get_rect(center=(WIDTH // 2, by + 60)))

def draw_achievements_panel():
    overlay = ed.Surface((WIDTH, HEIGHT), ed.SRCALPHA)
    overlay.fill((0, 0, 0, 230)); screen.blit(overlay, (0, 0))
    t = font_huge.render("ДОСТИЖЕНИЯ", True, COLOR_GOLD)
    screen.blit(t, t.get_rect(center=(WIDTH // 2, 45)))
    cnt1 = len(unlocked_achievements_p1)
    cnt2 = len(unlocked_achievements_p2)
    sub1 = font_mid.render(f"Игрок 1: {cnt1} / {TOTAL_ACH}", True, COLOR_P1)
    sub2 = font_mid.render(f"Игрок 2: {cnt2} / {TOTAL_ACH}", True, COLOR_P2)
    screen.blit(sub1, sub1.get_rect(center=(WIDTH // 4, 105)))
    screen.blit(sub2, sub2.get_rect(center=(WIDTH * 3 // 4, 105)))
    col_w = WIDTH // 2 - 40
    row_h = 52
    y_start = 140
    visible_h = HEIGHT - y_start - 40
    scroll = achievements_scroll
    max_scroll = max(0, TOTAL_ACH * row_h - visible_h)
    clip = ed.Rect(0, y_start, WIDTH, visible_h)
    old_clip = screen.get_clip()
    screen.set_clip(clip)
    for i, ach in enumerate(ACHIEVEMENTS):
        y = y_start + i * row_h - scroll
        if y + row_h < y_start or y > y_start + visible_h: continue
        x1 = 20
        u1 = ach["id"] in unlocked_achievements_p1
        bg1 = (40, 60, 60) if u1 else (30, 30, 45)
        b1 = COLOR_P1 if u1 else (70, 70, 90)
        r1 = ed.Rect(x1, y, col_w, row_h - 6)
        ed.draw.rect(screen, bg1, r1, border_radius=8)
        ed.draw.rect(screen, b1, r1, 2, border_radius=8)
        m1 = font_mid.render("✔" if u1 else "✗", True,
                             COLOR_P1 if u1 else (110, 110, 130))
        screen.blit(m1, (r1.x + 10, r1.y + 6))
        n1 = font_small.render(ach["name"], True, COLOR_GOLD if u1 else (170, 170, 190))
        screen.blit(n1, (r1.x + 45, r1.y + 2))
        d1 = font_mini.render(ach["desc"], True, (160, 160, 180))
        screen.blit(d1, (r1.x + 45, r1.y + 26))
        x2 = WIDTH // 2 + 20
        u2 = ach["id"] in unlocked_achievements_p2
        bg2 = (60, 40, 40) if u2 else (30, 30, 45)
        b2 = COLOR_P2 if u2 else (70, 70, 90)
        r2 = ed.Rect(x2, y, col_w, row_h - 6)
        ed.draw.rect(screen, bg2, r2, border_radius=8)
        ed.draw.rect(screen, b2, r2, 2, border_radius=8)
        m2 = font_mid.render("✔" if u2 else "✗", True,
                             COLOR_P2 if u2 else (110, 110, 130))
        screen.blit(m2, (r2.x + 10, r2.y + 6))
        n2 = font_small.render(ach["name"], True, COLOR_GOLD if u2 else (170, 170, 190))
        screen.blit(n2, (r2.x + 45, r2.y + 2))
        d2 = font_mini.render(ach["desc"], True, (160, 160, 180))
        screen.blit(d2, (r2.x + 45, r2.y + 26))
    screen.set_clip(old_clip)
    if max_scroll > 0:
        track_x = WIDTH - 10
        ed.draw.rect(screen, (50, 50, 70), (track_x, y_start, 6, visible_h), border_radius=3)
        bar_h = max(30, int(visible_h * visible_h / (TOTAL_ACH * row_h)))
        bar_y = y_start + int((visible_h - bar_h) * (scroll / max_scroll))
        ed.draw.rect(screen, COLOR_GOLD, (track_x, bar_y, 6, bar_h), border_radius=3)
    hint = font_tiny.render(
        "H / ESC — закрыть   |   ↑↓ / колесо — прокрутка   |   Левый = Игрок 1, правый = Игрок 2",
        True, COLOR_GRAY)
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 20)))

def draw_music_panel():
    global MUSIC_BTN_PREV, MUSIC_BTN_PAUSE, MUSIC_BTN_NEXT
    global MUSIC_BTN_VOL_UP, MUSIC_BTN_VOL_DOWN, MUSIC_BTN_LOAD
    panel_w, panel_h = 420, 175
    px, py = 15, HEIGHT - panel_h - 15
    ed.draw.rect(screen, (20, 20, 32), (px, py, panel_w, panel_h), border_radius=12)
    ed.draw.rect(screen, COLOR_GOLD, (px, py, panel_w, panel_h), 2, border_radius=12)
    title = font_small.render("🎵 МУЗЫКА", True, COLOR_GOLD)
    screen.blit(title, (px + 12, py + 6))
    name = get_track_name()
    if len(name) > 40: name = name[:37] + "..."
    t = font_mini.render(f"{current_track+1}/{len(playlist)}  {name}", True, (200, 200, 220))
    screen.blit(t, (px + 12, py + 32))
    btn_y = py + 58; btn_size = 42
    def music_btn(x, symbol, color=COLOR_GOLD):
        r = ed.Rect(x, btn_y, btn_size, btn_size)
        hover = r.collidepoint(mouse_pos)
        ed.draw.rect(screen, (60, 60, 85) if hover else (40, 40, 60), r, border_radius=8)
        ed.draw.rect(screen, color, r, 2, border_radius=8)
        s = font_mid.render(symbol, True, color)
        screen.blit(s, s.get_rect(center=r.center))
        return r
    MUSIC_BTN_PREV     = music_btn(px + 12, "⏮")
    MUSIC_BTN_PAUSE    = music_btn(px + 12 + 52, "▶" if music_paused else "⏸")
    MUSIC_BTN_NEXT     = music_btn(px + 12 + 104, "⏭")
    MUSIC_BTN_VOL_DOWN = music_btn(px + 12 + 160, "−")
    MUSIC_BTN_VOL_UP   = music_btn(px + 12 + 212, "+")
    vol_t = font_mini.render(f"Громкость: {int(music_volume*100)}%", True, (200, 200, 220))
    screen.blit(vol_t, (px + 12, py + 103))
    load_rect = ed.Rect(px + 12, py + 128, panel_w - 24, 34)
    hover = load_rect.collidepoint(mouse_pos)
    bg = (70, 60, 30) if hover else (45, 40, 25)
    ed.draw.rect(screen, bg, load_rect, border_radius=8)
    ed.draw.rect(screen, COLOR_GOLD, load_rect, 2, border_radius=8)
    lt = font_small.render("📁 ЗАГРУЗИТЬ МУЗЫКУ С ДИСКА", True, COLOR_GOLD)
    screen.blit(lt, lt.get_rect(center=load_rect.center))
    MUSIC_BTN_LOAD = load_rect

def draw_net_widget():
    global net_input_active, net_manual_mode
    ed.draw.rect(screen, (22, 22, 36), NET_PANEL, border_radius=14)
    ed.draw.rect(screen, COLOR_NET, NET_PANEL, 3, border_radius=14)
    t = font_mid.render("🌐 СЕТЕВАЯ ИГРА", True, COLOR_NET)
    screen.blit(t, t.get_rect(center=(NET_PANEL.centerx, NET_PANEL.y + 25)))
    if not net_connected:
        hover_h = NET_HOST_BTN.collidepoint(mouse_pos)
        ed.draw.rect(screen, (60, 45, 80) if hover_h else (40, 30, 60),
                     NET_HOST_BTN, border_radius=10)
        ed.draw.rect(screen, COLOR_NET, NET_HOST_BTN, 2, border_radius=10)
        th = font_small.render("🏠 СОЗДАТЬ ИГРУ", True, COLOR_NET)
        screen.blit(th, th.get_rect(center=NET_HOST_BTN.center))
        lbl = font_small.render("📡 Серверы в сети:", True, (210, 210, 230))
        screen.blit(lbl, (NET_LIST_RECT.x, NET_LIST_LBL_Y))
        ed.draw.rect(screen, (16, 16, 28), NET_LIST_RECT, border_radius=10)
        ed.draw.rect(screen, (70, 70, 100), NET_LIST_RECT, 2, border_radius=10)
        servers = sorted(discovered_servers.values(), key=lambda s: s.get("name", ""))
        if not servers:
            msg = font_mini.render("Поиск серверов...", True, (120, 120, 140))
            screen.blit(msg, (NET_LIST_RECT.x + 12, NET_LIST_RECT.y + 12))
            msg2 = font_mini.render("(включите Radmin VPN)", True, (100, 100, 120))
            screen.blit(msg2, (NET_LIST_RECT.x + 12, NET_LIST_RECT.y + 34))
        else:
            for i, srv in enumerate(servers[:SERVER_LIST_VISIBLE]):
                row = server_row_rect(i)
                hover = row.collidepoint(mouse_pos)
                ed.draw.rect(screen, (45, 55, 80) if hover else (30, 30, 48),
                             row, border_radius=8)
                ed.draw.rect(screen, COLOR_NET if hover else (80, 80, 110),
                             row, 2, border_radius=8)
                name_t = font_small.render(f"🖥️ {srv['name']}", True, (240, 240, 255))
                screen.blit(name_t, (row.x + 10, row.y + 2))
                info_t = font_mini.render(f"{srv['ip']}:{srv['port']}",
                                          True, (160, 160, 200))
                screen.blit(info_t, (row.x + 10, row.y + 26))
            if len(servers) > SERVER_LIST_VISIBLE:
                more = font_mini.render(f"...ещё {len(servers) - SERVER_LIST_VISIBLE}",
                                        True, (150, 150, 170))
                screen.blit(more, (NET_LIST_RECT.x + 10, NET_LIST_RECT.bottom - 20))
        mb = NET_MANUAL_BTN
        mhover = mb.collidepoint(mouse_pos)
        ed.draw.rect(screen, (55, 45, 35) if mhover else (35, 30, 25), mb, border_radius=8)
        ed.draw.rect(screen, COLOR_GOLD, mb, 2, border_radius=8)
        mt = font_mini.render("🔧 Ввести IP вручную" if not net_manual_mode
                              else "▲ Скрыть ручной ввод", True, COLOR_GOLD)
        screen.blit(mt, mt.get_rect(center=mb.center))
        if net_manual_mode:
            ed.draw.rect(screen, (30, 30, 45), NET_IP_RECT, border_radius=8)
            bc = COLOR_GOLD if net_input_active else (120, 120, 140)
            ed.draw.rect(screen, bc, NET_IP_RECT, 2, border_radius=8)
            txt = net_ip_input if net_ip_input else "26.x.x.x"
            col = (255, 255, 255) if net_ip_input else (110, 110, 130)
            tt = font_small.render(txt, True, col)
            screen.blit(tt, (NET_IP_RECT.x + 10, NET_IP_RECT.y + 10))
            if net_input_active and (ed.time.get_ticks() // 500) % 2:
                cx = NET_IP_RECT.x + 10 + tt.get_width() + 3
                ed.draw.line(screen, (255, 255, 255),
                             (cx, NET_IP_RECT.y + 8),
                             (cx, NET_IP_RECT.bottom - 8), 2)
            can_join = bool(net_ip_input.strip())
            jc = (100, 255, 150) if can_join else (100, 100, 120)
            hj = NET_JOIN_BTN.collidepoint(mouse_pos) and can_join
            ed.draw.rect(screen, (50, 80, 55) if hj else (35, 45, 40),
                         NET_JOIN_BTN, border_radius=8)
            ed.draw.rect(screen, jc, NET_JOIN_BTN, 2, border_radius=8)
            tj = font_small.render("🔌 ПОДКЛЮЧИТЬСЯ", True, jc)
            screen.blit(tj, tj.get_rect(center=NET_JOIN_BTN.center))
        if net_status_msg:
            s = font_mini.render(net_status_msg, True, (255, 200, 100))
            screen.blit(s, (NET_PANEL.x + 20, NET_PANEL.y + 592))
    else:
        t2 = font_small.render("✓ Связь установлена!", True, (100, 255, 150))
        screen.blit(t2, t2.get_rect(center=(NET_PANEL.centerx, NET_PANEL.y + 60)))
        info = font_mini.render(
            f"Вы — Игрок {net_my_num}  ({'хост' if net_my_num == 1 else 'клиент'})",
            True, (200, 200, 220))
        screen.blit(info, info.get_rect(center=(NET_PANEL.centerx, NET_PANEL.y + 92)))
        prompt = font_small.render("Выберите режим:", True, COLOR_NET)
        screen.blit(prompt, prompt.get_rect(center=(NET_PANEL.centerx, NET_PANEL.y + 125)))
        is_host = (net_my_num == 1)
        def mode_btn(rect, text, color, enabled=True):
            hover = rect.collidepoint(mouse_pos) and enabled
            base = (color[0]//3, color[1]//3, color[2]//3) if hover else (35, 35, 55)
            if not enabled: base = (30, 30, 40)
            ed.draw.rect(screen, base, rect, border_radius=8)
            col = color if enabled else (90, 90, 110)
            ed.draw.rect(screen, col, rect, 2, border_radius=8)
            tx = font_small.render(text, True, col)
            screen.blit(tx, tx.get_rect(center=rect.center))
        mode_btn(NET_FREE_BTN, "🖱️ Свободный режим", COLOR_P1, is_host)
        mode_btn(NET_COMP_BTN, "🎯 Соревнование",    COLOR_GOLD, is_host)
        mode_btn(NET_RACE_BTN, "⏱️ Гонка 60 сек",    COLOR_GREEN, is_host)
        if not is_host:
            wait = font_mini.render("Ожидание выбора хостом...",
                                    True, (180, 180, 200))
            screen.blit(wait, wait.get_rect(center=(NET_PANEL.centerx, NET_PANEL.y + 330)))
        hover_l = NET_LEAVE_BTN.collidepoint(mouse_pos)
        ed.draw.rect(screen, (80, 40, 40) if hover_l else (50, 30, 30),
                     NET_LEAVE_BTN, border_radius=8)
        ed.draw.rect(screen, COLOR_RED, NET_LEAVE_BTN, 2, border_radius=8)
        tl = font_mini.render("✖ ОТКЛЮЧИТЬСЯ", True, COLOR_RED)
        screen.blit(tl, tl.get_rect(center=NET_LEAVE_BTN.center))
        if net_status_msg and "отключ" in net_status_msg.lower():
            warn = font_mini.render(net_status_msg, True, COLOR_RED)
            screen.blit(warn, (NET_PANEL.x + 20, NET_PANEL.y + 480))

# ============================================================
# ОБНОВЛЕНИЕ ОБЩЕЙ ЛОГИКИ
# ============================================================
def update_common(dt):
    global double_time, mega_click_time, freeze_time, auto_boom_time
    global auto_mega_time, temp_crit_time, temp_power_time, event_message_timer
    global shop_anim_p1, shop_anim_p2, shield_active, event_message
    global achievement_banner_timer
    for p in (p1, p2):
        if net_is_online:
            is_local = ((net_my_num == 1 and p is p1) or
                        (net_my_num == 2 and p is p2))
            if not is_local: continue
        if p["scale"] < 1.0: p["scale"] = min(1.0, p["scale"] + 0.05)
        if p["score"] > p.get("max_score", 0): p["max_score"] = p["score"]
        if p.get("combo_timer", 0) > 0:
            p["combo_timer"] -= dt
            if p["combo_timer"] <= 0: p["combo"] = 0; p["combo_timer"] = 0.0
        p["patience_timer"] = p.get("patience_timer", 0) + dt
        if p.get("speedup_timer", 0) > 0:
            p["speedup_timer"] -= dt
            if p["speedup_timer"] <= 0: p["speedup_bonus"] = 0.0
        if p.get("reactor_interval", 0) > 0:
            if p["reactor_timer"] <= 0:
                p["reactor_timer"] = p["reactor_interval"]
                opp = p2 if p is p1 else p1
                dmg, _, _, _, _ = compute_damage(p, opp)
                p["score"] += dmg
                popups.append({"pos": [PLAYER1_X if p is p1 else PLAYER2_X, 220],
                               "life": 50, "alpha": 255,
                               "text": f"⚙️ +{dmg}", "color": (150, 220, 255)})
            else: p["reactor_timer"] -= dt
        if p.get("shield_regen", 0) > 0 and not shield_active:
            if p.get("shield_regen_timer", 0) <= 0:
                shield_active = True
                p["shield_regen_timer"] = p["shield_regen"]
                event_message = "🛡️ Щит восстановлен!"; event_message_timer = 2.0
            else: p["shield_regen_timer"] -= dt
        if p["auto"] > 0 or p.get("crystal", 0) > 0:
            rate = p["auto"] * p["auto_mult"]
            if p.get("speedup_bonus", 0) > 0: rate *= (1 + p["speedup_bonus"])
            if p.get("harmony", 0) > 0:
                total_lvl = sum(p["levels"]); rate *= (1 + total_lvl * p["harmony"])
            if auto_boom_time > 0: rate *= 3
            if auto_mega_time > 0: rate *= 10
            rate += p.get("crystal", 0)
            p["auto_acc"] += rate * dt
            while p["auto_acc"] >= 1:
                p["auto_acc"] -= 1
                income = max(1, int(p["power"] * p["mult"] * p["mega_mult"] * 0.5))
                p["score"] += income
    if not net_is_online:
        for attacker, victim in ((p1, p2), (p2, p1)):
            if attacker.get("curse", 0.0) > 0 and victim["score"] > 0:
                loss = int(victim["score"] * attacker["curse"] * dt)
                if loss > 0: victim["score"] = max(0, victim["score"] - loss)
    if double_time > 0:     double_time = max(0.0, double_time - dt)
    if mega_click_time > 0: mega_click_time = max(0.0, mega_click_time - dt)
    if freeze_time > 0:     freeze_time = max(0.0, freeze_time - dt)
    if auto_boom_time > 0:  auto_boom_time = max(0.0, auto_boom_time - dt)
    if auto_mega_time > 0:  auto_mega_time = max(0.0, auto_mega_time - dt)
    if temp_crit_time > 0:  temp_crit_time = max(0.0, temp_crit_time - dt)
    if temp_power_time > 0: temp_power_time = max(0.0, temp_power_time - dt)
    if event_message_timer > 0: event_message_timer = max(0.0, event_message_timer - dt)
    if achievement_banner_timer > 0:
        achievement_banner_timer = max(0.0, achievement_banner_timer - dt)
    shop_anim_p1 = min(1.0, shop_anim_p1 + 0.10) if shop_open_p1 else max(0.0, shop_anim_p1 - 0.10)
    shop_anim_p2 = min(1.0, shop_anim_p2 + 0.10) if shop_open_p2 else max(0.0, shop_anim_p2 - 0.10)
    check_achievements()

# ============================================================
# ВВОД В ИГРЕ
# ============================================================
def handle_gameplay_input(event):
    global shop_open_p1, shop_open_p2, confirm_reset, state, running
    global shop_scroll_p1, shop_scroll_p2, show_achievements, net_is_online
    global achievements_scroll
    online = net_is_online
    local_is_p1 = (not online) or (net_my_num == 1)
    local_is_p2 = (not online) or (net_my_num == 2)
    if event.type == ed.KEYDOWN:
        if event.key == ed.K_ESCAPE:
            if online:
                net_send({"type": "bye"})
                net_reset()
                net_is_online = False
            state = "menu"
            return
        if event.key == ed.K_RETURN:
            if online:
                net_send({"type": "bye"})
                net_reset()
                net_is_online = False
            running = False
            return
        if event.key == ed.K_h:
            show_achievements = not show_achievements
            achievements_scroll = 0
            return
        if event.key == ed.K_DELETE and state == "free":
            confirm_reset = True
            return
        if event.key == ed.K_m: toggle_pause()
        elif event.key == ed.K_n: next_track()
        elif event.key == ed.K_p: prev_track()
        elif event.key in (ed.K_EQUALS, ed.K_PLUS): change_volume(0.05)
        elif event.key == ed.K_MINUS: change_volume(-0.05)
        if local_is_p2:
            if event.key == ed.K_SPACE:
                do_click(p2, button2_rect.center, COLOR_P2)
            elif event.key == ed.K_b:
                shop_open_p2 = not shop_open_p2
            elif event.key == ed.K_z:
                best_idx, best_cost = -1, float("inf")
                discount = p2.get("discount", 0.0)
                for i in range(get_active_count()):
                    if p2["levels"][i] >= MAX_LEVEL: continue
                    c = int(p2["costs"][i] * (1 - discount))
                    if p2["score"] >= c and c < best_cost:
                        best_cost = c; best_idx = i
                if best_idx >= 0:
                    buy(p2, best_idx)
                    popups.append({"pos": [button2_rect.centerx - 40,
                                            button2_rect.centery - 40],
                                   "life": 60, "alpha": 255,
                                   "text": f"🛒 {UPGRADES[best_idx]['name']}!",
                                   "color": COLOR_P2})
            elif event.key in (ed.K_1, ed.K_2, ed.K_3, ed.K_4,
                                ed.K_5, ed.K_6, ed.K_7, ed.K_8):
                idx = event.key - ed.K_1
                if buy(p2, idx):
                    popups.append({"pos": [button2_rect.centerx - 40,
                                            button2_rect.centery - 40],
                                   "life": 60, "alpha": 255,
                                   "text": f"🛒 {UPGRADES[idx]['name']}!",
                                   "color": COLOR_P2})
        if online and local_is_p1:
            if event.key == ed.K_f:
                do_click(p1, button1_rect.center, COLOR_P1)
            elif event.key == ed.K_g:
                shop_open_p1 = not shop_open_p1
            elif event.key == ed.K_q:
                best_idx, best_cost = -1, float("inf")
                discount = p1.get("discount", 0.0)
                for i in range(get_active_count()):
                    if p1["levels"][i] >= MAX_LEVEL: continue
                    c = int(p1["costs"][i] * (1 - discount))
                    if p1["score"] >= c and c < best_cost:
                        best_cost = c; best_idx = i
                if best_idx >= 0:
                    buy(p1, best_idx)
                    popups.append({"pos": [button1_rect.centerx - 40,
                                            button1_rect.centery - 40],
                                   "life": 60, "alpha": 255,
                                   "text": f"🛒 {UPGRADES[best_idx]['name']}!",
                                   "color": COLOR_P1})
        if event.key == ed.K_UP:
            if shop_open_p2 and local_is_p2:
                shop_scroll_p2 = max(0, shop_scroll_p2 - SHOP_ITEM_H)
            elif shop_open_p1 and local_is_p1:
                shop_scroll_p1 = max(0, shop_scroll_p1 - SHOP_ITEM_H)
        elif event.key == ed.K_DOWN:
            if shop_open_p2 and local_is_p2:
                shop_scroll_p2 = min(get_max_scroll(), shop_scroll_p2 + SHOP_ITEM_H)
            elif shop_open_p1 and local_is_p1:
                shop_scroll_p1 = min(get_max_scroll(), shop_scroll_p1 + SHOP_ITEM_H)
    elif event.type == ed.MOUSEWHEEL:
        mx, my = ed.mouse.get_pos()
        if shop_open_p1 and local_is_p1 and get_panel_p1_rect().collidepoint(mx, my):
            shop_scroll_p1 -= event.y * 40
            shop_scroll_p1 = max(0, min(get_max_scroll(), shop_scroll_p1))
        elif shop_open_p2 and local_is_p2 and get_panel_p2_rect().collidepoint(mx, my):
            shop_scroll_p2 -= event.y * 40
            shop_scroll_p2 = max(0, min(get_max_scroll(), shop_scroll_p2))
    elif event.type == ed.MOUSEBUTTONDOWN and event.button == 1:
        pos = event.pos
        if SHOP_BTN_P1.collidepoint(pos) and local_is_p1:
            shop_open_p1 = not shop_open_p1; return
        if SHOP_BTN_P2.collidepoint(pos) and local_is_p2:
            shop_open_p2 = not shop_open_p2; return
        if shop_anim_p1 > 0.5 and local_is_p1 and get_panel_p1_rect().collidepoint(pos):
            px = get_panel_p1_rect().x
            for i in range(get_active_count()):
                r = panel_upgrade_rect(px, i, shop_scroll_p1)
                if r.collidepoint(pos) and SHOP_VIEW_TOP <= pos[1] <= SHOP_VIEW_BOTTOM:
                    buy(p1, i); return
            return
        if shop_anim_p2 > 0.5 and local_is_p2 and get_panel_p2_rect().collidepoint(pos):
            px = get_panel_p2_rect().x
            for i in range(get_active_count()):
                r = panel_upgrade_rect(px, i, shop_scroll_p2)
                if r.collidepoint(pos) and SHOP_VIEW_TOP <= pos[1] <= SHOP_VIEW_BOTTOM:
                    buy(p2, i); return
            return
        if button1_rect.collidepoint(pos) and local_is_p1:
            do_click(p1, pos, COLOR_P1)
        elif button2_rect.collidepoint(pos) and local_is_p2:
            do_click(p2, pos, COLOR_P2)

# ============================================================
# ГЛАВНЫЙ ЦИКЛ
# ============================================================
running = True
mouse_pos = (0, 0)

while running:
    dt = clock.tick(FPS) / 1000.0
    mouse_pos = ed.mouse.get_pos()
    clean_stale_servers()

    for event in ed.event.get():
        if event.type == ed.QUIT: running = False; continue

        if state == "menu":
            if event.type == ed.KEYDOWN:
                if event.key == ed.K_RETURN: running = False
                elif event.key == ed.K_1 and not net_input_active:
                    # Старт свободного режима (восстановит снимок, если есть)
                    start_match("free")
                elif event.key == ed.K_2 and not net_input_active: state = "comp_setup"
                elif event.key == ed.K_3 and not net_input_active: start_match("race")
                elif event.key == ed.K_h:
                    show_achievements = not show_achievements
                    achievements_scroll = 0
                elif event.key == ed.K_m: toggle_pause()
                elif event.key == ed.K_n: next_track()
                elif event.key == ed.K_p: prev_track()
                elif event.key in (ed.K_PLUS, ed.K_EQUALS): change_volume(0.05)
                elif event.key == ed.K_MINUS: change_volume(-0.05)
                elif net_input_active:
                    if event.key == ed.K_BACKSPACE:
                        net_ip_input = net_ip_input[:-1]
                    elif event.key == ed.K_ESCAPE:
                        net_input_active = False
                    elif event.unicode and event.unicode.isprintable() and len(net_ip_input) < 20:
                        net_ip_input += event.unicode
            elif event.type == ed.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if MUSIC_BTN_PREV.collidepoint(pos): prev_track()
                elif MUSIC_BTN_PAUSE.collidepoint(pos): toggle_pause()
                elif MUSIC_BTN_NEXT.collidepoint(pos): next_track()
                elif MUSIC_BTN_VOL_UP.collidepoint(pos): change_volume(0.05)
                elif MUSIC_BTN_VOL_DOWN.collidepoint(pos): change_volume(-0.05)
                elif MUSIC_BTN_LOAD.collidepoint(pos): add_music_files()
                elif not net_connected and NET_HOST_BTN.collidepoint(pos):
                    net_host(NET_PORT_DEFAULT); net_input_active = False
                elif not net_connected and NET_MANUAL_BTN.collidepoint(pos):
                    net_manual_mode = not net_manual_mode
                    if not net_manual_mode: net_input_active = False
                elif not net_connected and net_manual_mode and NET_IP_RECT.collidepoint(pos):
                    net_input_active = True
                elif not net_connected and net_manual_mode and \
                        NET_JOIN_BTN.collidepoint(pos) and net_ip_input.strip():
                    net_join(net_ip_input.strip()); net_input_active = False
                elif net_connected and NET_LEAVE_BTN.collidepoint(pos):
                    net_send({"type": "bye"}); net_reset()
                elif net_connected and net_my_num == 1 and NET_FREE_BTN.collidepoint(pos):
                    net_send({"type": "start_mode", "mode": "free"})
                    net_is_online = True
                    start_match("free")
                elif net_connected and net_my_num == 1 and NET_COMP_BTN.collidepoint(pos):
                    net_send({"type": "start_mode", "mode": "comp",
                              "target": comp_target})
                    net_is_online = True
                    start_match("comp")
                elif net_connected and net_my_num == 1 and NET_RACE_BTN.collidepoint(pos):
                    net_send({"type": "start_mode", "mode": "race"})
                    net_is_online = True
                    start_match("race")
                elif not net_connected and NET_LIST_RECT.collidepoint(pos):
                    servers = sorted(discovered_servers.values(), key=lambda s: s.get("name", ""))
                    rel_y = pos[1] - NET_LIST_RECT.y - 4
                    idx = int(rel_y // SERVER_ROW_H)
                    if 0 <= idx < min(len(servers), SERVER_LIST_VISIBLE):
                        srv = servers[idx]
                        net_join(srv["ip"], srv["port"])
                else:
                    for btn in MENU_BUTTONS:
                        if btn["rect"].collidepoint(pos):
                            if btn["state"] == "free":
                                start_match("free")
                            elif btn["state"] == "comp_setup":
                                state = "comp_setup"
                            elif btn["state"] == "race":
                                start_match("race")

        elif state == "comp_setup":
            if event.type == ed.KEYDOWN:
                if event.key in (ed.K_ESCAPE, ed.K_RETURN): state = "menu"
                elif event.key == ed.K_m: toggle_pause()
                elif event.key == ed.K_n: next_track()
                elif event.key == ed.K_p: prev_track()
            elif event.type == ed.MOUSEBUTTONDOWN and event.button == 1:
                if MUSIC_BTN_PREV.collidepoint(event.pos): prev_track()
                elif MUSIC_BTN_PAUSE.collidepoint(event.pos): toggle_pause()
                elif MUSIC_BTN_NEXT.collidepoint(event.pos): next_track()
                elif MUSIC_BTN_VOL_UP.collidepoint(event.pos): change_volume(0.05)
                elif MUSIC_BTN_VOL_DOWN.collidepoint(event.pos): change_volume(-0.05)
                elif MUSIC_BTN_LOAD.collidepoint(event.pos): add_music_files()
                else:
                    for r, amount in COMP_PRESET_RECTS:
                        if r.collidepoint(event.pos):
                            comp_target = amount
                            if net_is_online:
                                net_send({"type": "start_mode", "mode": "comp",
                                          "target": amount})
                            start_match("comp")
                            break

        elif state in ("free", "comp", "race"):
            if show_achievements:
                if event.type == ed.KEYDOWN:
                    if event.key in (ed.K_h, ed.K_ESCAPE):
                        show_achievements = False
                    elif event.key == ed.K_UP:
                        achievements_scroll = max(0, achievements_scroll - 52)
                    elif event.key == ed.K_DOWN:
                        max_s = max(0, TOTAL_ACH * 52 - (HEIGHT - 180))
                        achievements_scroll = min(max_s, achievements_scroll + 52)
                elif event.type == ed.MOUSEWHEEL:
                    max_s = max(0, TOTAL_ACH * 52 - (HEIGHT - 180))
                    achievements_scroll = max(0, min(max_s, achievements_scroll - event.y * 40))
                continue
            if confirm_reset:
                if event.type == ed.KEYDOWN:
                    if event.key in (ed.K_y, ed.K_RETURN, ed.K_DELETE):
                        reset_game(); confirm_reset = False
                    elif event.key in (ed.K_n, ed.K_ESCAPE):
                        confirm_reset = False
                continue
            handle_gameplay_input(event)

        elif state == "game_over":
            if event.type == ed.KEYDOWN:
                if event.key == ed.K_ESCAPE:
                    if net_is_online:
                        net_send({"type": "bye"}); net_reset()
                    state = "menu"
                elif event.key == ed.K_r:
                    if net_is_online and net_connected:
                        net_send({"type": "start_mode", "mode": prev_state})
                    start_match(prev_state)
                elif event.key == ed.K_RETURN: running = False
            elif event.type == ed.MOUSEBUTTONDOWN and event.button == 1:
                replay_rect = ed.Rect(WIDTH//2 - 400, HEIGHT - 220, 380, 90)
                menu_rect   = ed.Rect(WIDTH//2 + 20,  HEIGHT - 220, 380, 90)
                if replay_rect.collidepoint(event.pos):
                    if net_is_online and net_connected:
                        net_send({"type": "start_mode", "mode": prev_state})
                    start_match(prev_state)
                elif menu_rect.collidepoint(event.pos):
                    if net_is_online:
                        net_send({"type": "bye"}); net_reset()
                    state = "menu"

    if pending_mode is not None:
        m = pending_mode.get("mode", "free")
        if m == "comp":
            comp_target = pending_mode.get("target", 5000)
        net_is_online = True
        start_match(m)
        pending_mode = None

    if state in ("free", "comp", "race") and not confirm_reset and not show_achievements:
        if net_is_online:
            net_pump()
            net_send_local_state()
        update_common(dt)
        if state == "free":
            event_timer -= dt
            if event_timer <= 0:
                event_timer = EVENT_INTERVAL
                if not net_is_online:
                    trigger_event()
                elif net_my_num == 1:
                    trigger_event()
            autosave_timer -= dt
            if autosave_timer <= 0:
                autosave_timer = AUTOSAVE_INTERVAL
                save_game()
        elif state == "comp":
            if p1["score"] >= comp_target and p2["score"] >= comp_target:
                winner = 0
            elif p1["score"] >= comp_target:
                winner = 1
            elif p2["score"] >= comp_target:
                winner = 2
            if winner is not None:
                prev_state = "comp"; state = "game_over"
                winner_message = ("НИЧЬЯ! Оба достигли цели!" if winner == 0
                                  else f"🏆 ПОБЕДИЛ ИГРОК {winner}!")
        elif state == "race":
            race_timer = max(0.0, race_timer - dt)
            if race_timer <= 0:
                if p1["score"] > p2["score"]: winner = 1
                elif p2["score"] > p1["score"]: winner = 2
                else: winner = 0
                prev_state = "race"; state = "game_over"
                winner_message = (f"НИЧЬЯ! Оба набрали {p1['score']}" if winner == 0
                                  else f"🏆 ПОБЕДИЛ ИГРОК {winner}! ({p1['score']} : {p2['score']})")

    screen.fill(COLOR_BG)

    if state == "menu":
        title = font_huge.render("КЛИКЕР", True, COLOR_GOLD)
        screen.blit(title, title.get_rect(center=(WIDTH // 2 - 200, 80)))
        sub = font_mid.render("Выбери режим игры", True, (200, 200, 220))
        screen.blit(sub, sub.get_rect(center=(WIDTH // 2 - 200, 150)))
        for i, btn in enumerate(MENU_BUTTONS):
            hover = btn["rect"].collidepoint(mouse_pos)
            bg = (55, 55, 85) if hover else (40, 40, 60)
            ed.draw.rect(screen, bg, btn["rect"], border_radius=20)
            ed.draw.rect(screen, btn["color"], btn["rect"], 4, border_radius=20)
            num = font_big.render(f"{i+1}", True, btn["color"])
            screen.blit(num, (btn["rect"].x + 35, btn["rect"].y + 25))
            label = font_big.render(btn["label"], True, btn["color"])
            screen.blit(label, (btn["rect"].x + 120, btn["rect"].y + 6))
            s = font_small.render(btn["sub"], True, (200, 200, 220))
            screen.blit(s, (btn["rect"].x + 120, btn["rect"].y + 62))
        ach_t = font_small.render(
            f"🏆 Игрок 1: {len(unlocked_achievements_p1)}/{TOTAL_ACH}   |   "
            f"Игрок 2: {len(unlocked_achievements_p2)}/{TOTAL_ACH}",
            True, COLOR_GOLD)
        screen.blit(ach_t, ach_t.get_rect(center=(WIDTH // 2 - 200, HEIGHT - 175)))
        ach_btn = ed.Rect(WIDTH // 2 - 350, HEIGHT - 145, 300, 40)
        ed.draw.rect(screen, (40, 40, 60), ach_btn, border_radius=10)
        ed.draw.rect(screen, COLOR_GOLD, ach_btn, 2, border_radius=10)
        ab = font_small.render("Посмотреть достижения (H)", True, COLOR_GOLD)
        screen.blit(ab, ab.get_rect(center=ach_btn.center))
        hint = font_tiny.render(
            "1 / 2 / 3 — быстрый выбор режима   |   ENTER — выход   |   H — достижения",
            True, COLOR_GRAY)
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2 - 200, HEIGHT - 70)))
        draw_music_panel()
        draw_net_widget()
        if show_achievements: draw_achievements_panel()

    elif state == "comp_setup":
        title = font_huge.render("СОРЕВНОВАНИЕ", True, COLOR_GOLD)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 120)))
        sub = font_mid.render("Выбери цель — первый, кто её достигнет, победит!",
                              True, (200, 200, 220))
        screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 210)))
        for r, amount in COMP_PRESET_RECTS:
            hover = r.collidepoint(mouse_pos)
            bg = (70, 60, 30) if hover else (50, 45, 25)
            ed.draw.rect(screen, bg, r, border_radius=20)
            ed.draw.rect(screen, COLOR_GOLD, r, 4, border_radius=20)
            t = font_big.render(f"{amount:,}".replace(",", " "), True, COLOR_GOLD)
            screen.blit(t, t.get_rect(center=(r.centerx, r.y + 60)))
            s = font_small.render("очков", True, (220, 220, 220))
            screen.blit(s, s.get_rect(center=(r.centerx, r.y + 120)))
        hint = font_tiny.render("Клик по кнопке — старт   |   ESC / ENTER — назад",
                                True, COLOR_GRAY)
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 60)))
        draw_music_panel()

    elif state in ("free", "comp", "race"):
        ed.draw.line(screen, (60, 60, 90), (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 2)
        if net_is_online:
            t = font_mid.render(
                f"🌐 ОНЛАЙН — ВЫ Игрок {net_my_num}  "
                f"({'хост' if net_my_num == 1 else 'клиент'})", True, COLOR_NET)
            screen.blit(t, t.get_rect(center=(WIDTH // 2, 15)))
            if not net_connected:
                warn = font_small.render("⚠ Противник отключился (ESC — в меню)",
                                         True, (255, 100, 100))
                screen.blit(warn, warn.get_rect(center=(WIDTH // 2, 45)))
        if state == "free":
            bar_w, bar_h = 500, 22
            bx = WIDTH // 2 - bar_w // 2; by = 25 if not net_is_online else 55
            ed.draw.rect(screen, (60, 60, 90), (bx, by, bar_w, bar_h), border_radius=10)
            ratio = 1.0 - (event_timer / EVENT_INTERVAL)
            ed.draw.rect(screen, COLOR_GOLD, (bx, by, int(bar_w * ratio), bar_h), border_radius=10)
            tc = (255, 100, 100) if event_timer < 5 else COLOR_GOLD
            t = font_mid.render(f"Событие через: {event_timer:4.1f}с", True, tc)
            screen.blit(t, t.get_rect(center=(WIDTH // 2, by + 50)))
        elif state == "comp":
            t = font_mid.render(f"🎯 ЦЕЛЬ: {comp_target}", True, COLOR_GOLD)
            screen.blit(t, t.get_rect(center=(WIDTH // 2, 45 if not net_is_online else 75)))
            for px, player, color in ((PLAYER1_X, p1, COLOR_P1), (PLAYER2_X, p2, COLOR_P2)):
                pct = min(1.0, player["score"] / comp_target) if comp_target > 0 else 0
                bw, bh = 500, 26
                bx = px - bw // 2
                by = 75 if not net_is_online else 105
                ed.draw.rect(screen, (60, 60, 90), (bx, by, bw, bh), border_radius=10)
                ed.draw.rect(screen, color, (bx, by, int(bw * pct), bh), border_radius=10)
                pt = font_small.render(f"{player['score']} / {comp_target}  ({int(pct*100)}%)",
                                       True, (240, 240, 240))
                screen.blit(pt, pt.get_rect(center=(px, by + 13)))
        elif state == "race":
            t = font_mid.render(f"⏱️ ГОНКА — осталось: {race_timer:4.1f}с", True,
                                COLOR_GREEN if race_timer > 10 else COLOR_RED)
            screen.blit(t, t.get_rect(center=(WIDTH // 2, 40 if not net_is_online else 70)))
            total = max(1, p1["score"] + p2["score"]); ratio = p1["score"] / total
            bw, bh = 900, 40; bx = WIDTH // 2 - bw // 2
            by = 75 if not net_is_online else 105
            ed.draw.rect(screen, COLOR_P2, (bx, by, bw, bh), border_radius=20)
            ed.draw.rect(screen, COLOR_P1, (bx, by, int(bw * ratio), bh), border_radius=20)
            ed.draw.rect(screen, (230, 230, 230), (bx, by, bw, bh), 3, border_radius=20)
            lt = font_small.render(f"Игрок 1: {p1['score']}", True, (255, 255, 255))
            screen.blit(lt, (bx + 15, by + 8))
            rt = font_small.render(f"Игрок 2: {p2['score']}", True, (255, 255, 255))
            screen.blit(rt, (bx + bw - rt.get_width() - 15, by + 8))
        draw_effects()
        draw_player_column(PLAYER1_X, p1, COLOR_P1, SHOP_BTN_P1, shop_open_p1)
        draw_player_column(PLAYER2_X, p2, COLOR_P2, SHOP_BTN_P2, shop_open_p2)
        hint2 = font_mini.render(
            "ПРОБЕЛ — клик  |  B — магазин  |  Z — дешёвое  |  1..8 — конкретное  |  ↑↓ — прокрутка  |  H — достижения",
            True, COLOR_P2)
        screen.blit(hint2, hint2.get_rect(center=(PLAYER2_X, 680)))
        draw_shop_panel(get_panel_p1_rect(), p1, COLOR_P1, shop_scroll_p1)
        draw_shop_panel(get_panel_p2_rect(), p2, COLOR_P2, shop_scroll_p2)
        draw_popups()
        if state == "free": draw_event_message()
        ach_t = font_small.render(
            f"🏆 И1: {len(unlocked_achievements_p1)}  |  И2: {len(unlocked_achievements_p2)}",
            True, COLOR_GOLD)
        screen.blit(ach_t, (20, 20))
        bottom = "ENTER — выход  |  ESC — в меню  |  H — достижения  |  M/N/P — музыка"
        if state == "free" and not net_is_online:
            bottom = ("ENTER — выход  |  ESC — в меню  |  H — достижения  "
                      "|  DELETE — стереть  |  M/N/P — музыка")
        elif net_is_online:
            bottom = ("Хост: F — клик, G — магазин, Q — дешёвое  |  "
                      "Клиент: ПРОБЕЛ/B/Z  |  ESC — в меню")
        t = font_mini.render(bottom, True, COLOR_GRAY)
        screen.blit(t, t.get_rect(center=(WIDTH // 2, HEIGHT - 25)))
        if confirm_reset: draw_confirm_reset()
        draw_achievement_banner()
        if show_achievements: draw_achievements_panel()

    elif state == "game_over":
        overlay = ed.Surface((WIDTH, HEIGHT), ed.SRCALPHA)
        overlay.fill((0, 0, 0, 200)); screen.blit(overlay, (0, 0))
        t = font_huge.render("ИГРА ОКОНЧЕНА", True, COLOR_GOLD)
        screen.blit(t, t.get_rect(center=(WIDTH // 2, 180)))
        wc = COLOR_P1 if winner == 1 else COLOR_P2 if winner == 2 else COLOR_GOLD
        t = font_big.render(winner_message, True, wc)
        screen.blit(t, t.get_rect(center=(WIDTH // 2, 320)))
        t = font_mid.render(f"Игрок 1: {p1['score']}   |   Игрок 2: {p2['score']}",
                            True, (230, 230, 230))
        screen.blit(t, t.get_rect(center=(WIDTH // 2, 400)))
        replay_rect = ed.Rect(WIDTH // 2 - 400, HEIGHT - 220, 380, 90)
        menu_rect   = ed.Rect(WIDTH // 2 + 20,  HEIGHT - 220, 380, 90)
        for r, label, color in ((replay_rect, "🔁 ИГРАТЬ СНОВА", COLOR_GREEN),
                                (menu_rect,   "🏠 В МЕНЮ",       COLOR_GOLD)):
            hover = r.collidepoint(mouse_pos)
            bg = (55, 75, 55) if (hover and color == COLOR_GREEN) else \
                 (75, 65, 30) if (hover and color == COLOR_GOLD) else (40, 40, 60)
            ed.draw.rect(screen, bg, r, border_radius=20)
            ed.draw.rect(screen, color, r, 4, border_radius=20)
            t = font_mid.render(label, True, color)
            screen.blit(t, t.get_rect(center=r.center))
        hint = font_tiny.render("R — играть снова  |  ESC — в меню  |  ENTER — выход",
                                True, COLOR_GRAY)
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 90)))

    hovering = False
    if state == "menu":
        for b in MENU_BUTTONS:
            if b["rect"].collidepoint(mouse_pos): hovering = True; break
        if MUSIC_BTN_PREV.collidepoint(mouse_pos) or MUSIC_BTN_PAUSE.collidepoint(mouse_pos) or \
           MUSIC_BTN_NEXT.collidepoint(mouse_pos) or MUSIC_BTN_VOL_UP.collidepoint(mouse_pos) or \
           MUSIC_BTN_VOL_DOWN.collidepoint(mouse_pos) or MUSIC_BTN_LOAD.collidepoint(mouse_pos):
            hovering = True
        if ed.Rect(WIDTH // 2 - 350, HEIGHT - 145, 300, 40).collidepoint(mouse_pos):
            hovering = True
        if not net_connected:
            if NET_HOST_BTN.collidepoint(mouse_pos) or NET_MANUAL_BTN.collidepoint(mouse_pos):
                hovering = True
            if net_manual_mode and (NET_IP_RECT.collidepoint(mouse_pos) or
                                     NET_JOIN_BTN.collidepoint(mouse_pos)):
                hovering = True
            servers = sorted(discovered_servers.values(), key=lambda s: s.get("name", ""))
            for i in range(min(len(servers), SERVER_LIST_VISIBLE)):
                if server_row_rect(i).collidepoint(mouse_pos):
                    hovering = True; break
        else:
            if NET_LEAVE_BTN.collidepoint(mouse_pos): hovering = True
            if net_my_num == 1 and (NET_FREE_BTN.collidepoint(mouse_pos) or
                                     NET_COMP_BTN.collidepoint(mouse_pos) or
                                     NET_RACE_BTN.collidepoint(mouse_pos)):
                hovering = True
    elif state == "comp_setup":
        for r, _ in COMP_PRESET_RECTS:
            if r.collidepoint(mouse_pos): hovering = True; break
        if MUSIC_BTN_PREV.collidepoint(mouse_pos) or MUSIC_BTN_PAUSE.collidepoint(mouse_pos) or \
           MUSIC_BTN_NEXT.collidepoint(mouse_pos) or MUSIC_BTN_VOL_UP.collidepoint(mouse_pos) or \
           MUSIC_BTN_VOL_DOWN.collidepoint(mouse_pos) or MUSIC_BTN_LOAD.collidepoint(mouse_pos):
            hovering = True
    elif state == "game_over":
        if ed.Rect(WIDTH // 2 - 400, HEIGHT - 220, 380, 90).collidepoint(mouse_pos) or \
           ed.Rect(WIDTH // 2 + 20,  HEIGHT - 220, 380, 90).collidepoint(mouse_pos):
            hovering = True
    elif state in ("free", "comp", "race") and not confirm_reset and not show_achievements:
        if SHOP_BTN_P1.collidepoint(mouse_pos) or SHOP_BTN_P2.collidepoint(mouse_pos) or \
           button1_rect.collidepoint(mouse_pos):
            hovering = True
        else:
            if shop_anim_p1 > 0.5:
                px = get_panel_p1_rect().x
                for i in range(get_active_count()):
                    r = panel_upgrade_rect(px, i, shop_scroll_p1)
                    if r.collidepoint(mouse_pos) and SHOP_VIEW_TOP <= mouse_pos[1] <= SHOP_VIEW_BOTTOM:
                        hovering = True; break
            if not hovering and shop_anim_p2 > 0.5:
                px = get_panel_p2_rect().x
                for i in range(get_active_count()):
                    r = panel_upgrade_rect(px, i, shop_scroll_p2)
                    if r.collidepoint(mouse_pos) and SHOP_VIEW_TOP <= mouse_pos[1] <= SHOP_VIEW_BOTTOM:
                        hovering = True; break

    ed.mouse.set_cursor(ed.SYSTEM_CURSOR_HAND if hovering else ed.SYSTEM_CURSOR_ARROW)
    ed.display.flip()

# --- Выход ---
try:
    if net_connected:
        net_send({"type": "bye"})
except Exception:
    pass
net_reset()
stop_discovery_listener()
save_game()
ed.quit()
sys.exit()