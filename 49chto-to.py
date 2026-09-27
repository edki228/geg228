# ============================================================
# ДВУХИГРОВОЙ КЛИКЕР С ПАНЕЛЬЮ-МАГАЗИНОМ, 8 УЛУЧШЕНИЯМИ И 20 СОБЫТИЯМИ
# Игрок 1 — мышь, ПРОБЕЛ — нет (он кликает мышью)
# Игрок 2 — ПРОБЕЛ (клик) + B (магазин) + Z (купить дешёвое) + 1..8 (купить конкретное)
# DELETE — сброс прогресса с подтверждением
# ============================================================

# ---------- ИМПОРТ БИБЛИОТЕК ----------
import pygame as ed
import sys
import random
import json
import os

# ============================================================
# ИНИЦИАЛИЗАЦИЯ PYGAME И ОКНА
# ============================================================
ed.init()
WIDTH, HEIGHT = 1590, 900
screen = ed.display.set_mode((WIDTH, HEIGHT), ed.FULLSCREEN)
ed.display.set_caption("огризок")

# ---------- ШРИФТЫ ----------
font_big   = ed.font.Font(None, 64)
font_mid   = ed.font.Font(None, 40)
font_small = ed.font.Font(None, 28)
font_tiny  = ed.font.Font(None, 20)
font_mini  = ed.font.Font(None, 17)

# ---------- МУЗЫКА ----------
try:
    ed.mixer.music.load("muzika.mp3")
    ed.mixer.music.play(-1)
except Exception:
    print("музыка не загрузилась, ну и ладно")

clock = ed.time.Clock()
FPS = 240

# ============================================================
# КАРТИНКИ КНОПОК ИГРОКОВ
# ============================================================
try:
    button_img = ed.image.load("igrok.png").convert_alpha()
    button_img = ed.transform.smoothscale(button_img, (260, 260))
except FileNotFoundError:
    button_img = ed.Surface((260, 260), ed.SRCALPHA)
    ed.draw.circle(button_img, (110, 193, 255), (130, 130), 130)
    print("ты зыбыл фел периминавать")

button_img2 = ed.Surface((260, 260), ed.SRCALPHA)
ed.draw.circle(button_img2, (255, 130, 130), (130, 130), 130)

# ---------- ПОЗИЦИИ КЛИК-КНОПОК ----------
PLAYER1_X = WIDTH // 4
PLAYER2_X = WIDTH * 3 // 4
button1_rect = button_img.get_rect(center=(PLAYER1_X, 300))
button2_rect = button_img2.get_rect(center=(PLAYER2_X, 300))

# ============================================================
# ВИДЫ УЛУЧШЕНИЙ (8 штук)
# ============================================================
UPGRADES = [
    {"name": "Клик",     "desc": "+1 к силе клика",         "base": 10,   "mult": 1.5},
    {"name": "Авто",     "desc": "+1 очко/сек",             "base": 50,   "mult": 1.7},
    {"name": "Множ",     "desc": "x1.10 к урону клика",     "base": 200,  "mult": 2.0},
    {"name": "Крит",     "desc": "+3% шанс крита",          "base": 100,  "mult": 1.8},
    {"name": "КритУрон", "desc": "+1 к множителю крита",    "base": 300,  "mult": 2.1},
    {"name": "АвтоМнож", "desc": "+15% к автодоходу",       "base": 400,  "mult": 1.9},
    {"name": "Золото",   "desc": "+2% шанс золотого клика", "base": 500,  "mult": 2.3},
    {"name": "Мега",     "desc": "x1.05 ко всему доходу",   "base": 800,  "mult": 2.5},
]
NUM_UPGRADES = len(UPGRADES)

# ============================================================
# СОЗДАНИЕ ИГРОКА
# ============================================================
def make_player():
    return {
        "score": 0,
        "power": 1,
        "auto": 0,
        "mult": 1.0,
        "crit": 0.0,
        "crit_mult": 5.0,
        "auto_mult": 1.0,
        "golden_chance": 0.0,
        "mega_mult": 1.0,
        "levels": [0] * NUM_UPGRADES,
        "costs": [u["base"] for u in UPGRADES],
        "scale": 1.0,
        "auto_acc": 0.0,
        "golden": 0,
    }

p1 = make_player()
p2 = make_player()

# ============================================================
# СОХРАНЕНИЕ И ЗАГРУЗКА
# ============================================================
SAVE_FILE = "save.json"

def save_game():
    data = {
        "p1": {k: p1[k] for k in ("score","power","auto","mult","crit","crit_mult",
                                  "auto_mult","golden_chance","mega_mult","levels","costs")},
        "p2": {k: p2[k] for k in ("score","power","auto","mult","crit","crit_mult",
                                  "auto_mult","golden_chance","mega_mult","levels","costs")},
    }
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("💾 Прогресс сохранён")
    except Exception as e:
        print("Не удалось сохранить:", e)

def load_game():
    if not os.path.exists(SAVE_FILE):
        print("Сохранения нет — начинаем с нуля")
        return
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, player in (("p1", p1), ("p2", p2)):
            if key in data:
                for k, v in data[key].items():
                    if k in player:
                        player[k] = v
                # На всякий случай — достраиваем costs, если изменилось число апгрейдов
                if len(player["costs"]) != NUM_UPGRADES:
                    player["costs"] = [u["base"] for u in UPGRADES]
                    player["levels"] = [0] * NUM_UPGRADES
        print("📂 Прогресс загружен")
    except Exception as e:
        print("Не удалось загрузить:", e)

def reset_game():
    try:
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
            print("🗑️ Файл сохранения удалён")
    except Exception as e:
        print("Не удалось удалить файл:", e)

    for player in (p1, p2):
        for k, v in make_player().items():
            player[k] = v

    global event_timer, double_time, mega_click_time, freeze_time
    global auto_boom_time, auto_mega_time, temp_crit_time, temp_power_time
    global shield_active, event_message, event_message_timer, autosave_timer
    event_timer = EVENT_INTERVAL
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
    autosave_timer = AUTOSAVE_INTERVAL
    popups.clear()
    print("♻️ Прогресс сброшен")

load_game()

# ============================================================
# ЦВЕТА
# ============================================================
COLOR_P1 = (110, 193, 255)
COLOR_P2 = (255, 130, 130)
COLOR_BG = (30, 30, 47)
COLOR_GOLD = (255, 215, 0)
COLOR_GRAY = (150, 150, 150)
COLOR_RED = (255, 70, 70)
COLOR_PANEL_BG = (22, 22, 36)
COLOR_PANEL_BORDER = (70, 70, 110)
COLOR_BTN_BG = (42, 42, 66)
COLOR_BTN_BG_OK = (55, 75, 110)
COLOR_BTN_BG_OK2 = (110, 60, 60)

# ============================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================
popups = []

EVENT_INTERVAL = 20.0
event_timer = EVENT_INTERVAL

# Активные эффекты
double_time     = 0.0   # x2 к клику
mega_click_time = 0.0   # x5 к клику
freeze_time     = 0.0   # запрет кликов
auto_boom_time  = 0.0   # x3 к авто
auto_mega_time  = 0.0   # x10 к авто
temp_crit_time  = 0.0   # +10% крит
temp_power_time = 0.0   # +5 к силе
shield_active   = False # блокирует след. негативное событие

event_message = ""
event_message_timer = 0.0

AUTOSAVE_INTERVAL = 30.0
autosave_timer = AUTOSAVE_INTERVAL

confirm_reset = False

# ---------- СОСТОЯНИЕ МАГАЗИНОВ ----------
shop_open_p1 = False
shop_open_p2 = False
shop_anim_p1 = 0.0
shop_anim_p2 = 0.0

PANEL_W = 420

# Кнопки-переключатели магазина (под кликерами)
SHOP_BTN_P1 = ed.Rect(PLAYER1_X - 110, 600, 220, 55)
SHOP_BTN_P2 = ed.Rect(PLAYER2_X - 110, 600, 220, 55)

# ============================================================
# ФУНКЦИИ ПОЗИЦИЙ
# ============================================================
def get_panel_p1_rect():
    x = -PANEL_W + int(PANEL_W * shop_anim_p1)
    return ed.Rect(x, 0, PANEL_W, HEIGHT)

def get_panel_p2_rect():
    x = WIDTH - int(PANEL_W * shop_anim_p2)
    return ed.Rect(x, 0, PANEL_W, HEIGHT)

def panel_upgrade_rect(panel_left_x, idx):
    return ed.Rect(panel_left_x + 20, 190 + idx * 72, PANEL_W - 40, 64)

# ============================================================
# РАСЧЁТ УРОНА КЛИКА
# ============================================================
def compute_damage(player):
    dmg = player["power"] * player["mult"] * player["mega_mult"]
    if temp_power_time > 0:
        dmg += 5
    if double_time > 0:
        dmg *= 2
    if mega_click_time > 0:
        dmg *= 5

    crit_chance = player["crit"] + (0.10 if temp_crit_time > 0 else 0.0)
    is_crit = random.random() < crit_chance
    if is_crit:
        dmg *= player["crit_mult"]

    is_golden = False
    if player["golden"] > 0:
        dmg *= 10
        player["golden"] -= 1
        is_golden = True
    elif random.random() < player["golden_chance"]:
        dmg *= 10
        is_golden = True

    return max(1, int(dmg)), is_crit, is_golden

# ============================================================
# КЛИК ИГРОКА
# ============================================================
def do_click(player, pos, color):
    if freeze_time > 0:
        popups.append({"pos": [pos[0], pos[1]], "life": 40,
                       "alpha": 255, "text": "❄️", "color": (150, 200, 255)})
        return
    dmg, is_crit, is_golden = compute_damage(player)
    player["score"] += dmg
    player["scale"] = 0.9

    if is_golden:
        text = f"🌟 +{dmg}"
    elif is_crit:
        text = f"КРИТ! +{dmg}"
    else:
        text = f"+{dmg}"
    popups.append({"pos": [pos[0], pos[1]], "life": 60,
                   "alpha": 255, "text": text, "color": color})

# ============================================================
# ПОКУПКА УЛУЧШЕНИЯ
# ============================================================
def buy(player, idx):
    if idx < 0 or idx >= NUM_UPGRADES:
        return False
    cost = player["costs"][idx]
    if player["score"] < cost:
        return False

    player["score"] -= cost
    player["levels"][idx] += 1
    player["costs"][idx] = int(player["costs"][idx] * UPGRADES[idx]["mult"])

    if idx == 0:
        player["power"] += 1
    elif idx == 1:
        player["auto"] += 1
    elif idx == 2:
        player["mult"] *= 1.10
    elif idx == 3:
        player["crit"] = min(1.0, player["crit"] + 0.03)
    elif idx == 4:
        player["crit_mult"] += 1.0
    elif idx == 5:
        player["auto_mult"] += 0.15
    elif idx == 6:
        player["golden_chance"] = min(1.0, player["golden_chance"] + 0.02)
    elif idx == 7:
        player["mega_mult"] *= 1.05

    return True

# ============================================================
# СЛУЧАЙНЫЕ СОБЫТИЯ (20 штук)
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

    # Щит блокирует негативные события
    if evt in ("penalty", "bigpenalty", "robbery", "freeze") and shield_active:
        shield_active = False
        event_message = "🛡️ ЩИТ отразил негативное событие!"
        event_message_timer = 3.5
        return

    if evt == "bonus":
        p1["score"] += 50; p2["score"] += 50
        event_message = "🎁 БОНУС! +50 каждому"
    elif evt == "bigbonus":
        p1["score"] += 200; p2["score"] += 200
        event_message = "💰 БОЛЬШОЙ БОНУС! +200 каждому"
    elif evt == "double":
        double_time = 10.0
        event_message = "⚡ X2 КЛИКИ НА 10 СЕКУНД!"
    elif evt == "mega":
        mega_click_time = 5.0
        event_message = "🔥 МЕГА! X5 КЛИКИ НА 5 СЕКУНД!"
    elif evt == "penalty":
        p1["score"] = max(0, p1["score"] - 30)
        p2["score"] = max(0, p2["score"] - 30)
        event_message = "💀 ШТРАФ! -30 каждому"
    elif evt == "bigpenalty":
        p1["score"] = max(0, p1["score"] - 100)
        p2["score"] = max(0, p2["score"] - 100)
        event_message = "☠️ БОЛЬШОЙ ШТРАФ! -100 каждому"
    elif evt == "gift":
        if p1["score"] > p2["score"]:
            p2["score"] += 100
            event_message = "🎈 ПОДАРОК: игрок 2 получает 100!"
        elif p2["score"] > p1["score"]:
            p1["score"] += 100
            event_message = "🎈 ПОДАРОК: игрок 1 получает 100!"
        else:
            p1["score"] += 50; p2["score"] += 50
            event_message = "🎈 Ничья! +50 каждому"
    elif evt == "golden":
        p1["golden"] += 1; p2["golden"] += 1
        event_message = "🌟 ЗОЛОТОЙ КЛИК! Следующий клик x10"
    elif evt == "supergolden":
        p1["golden"] += 1; p2["golden"] += 1
        p1["golden"] += 1; p2["golden"] += 1  # x50 значит 5 зарядов по x10? Нет — оставим один, но супержирный
        # Проще: выдаём 5 зарядов каждому
        p1["golden"] += 3; p2["golden"] += 3
        event_message = "✨ СУПЕР-ЗОЛОТО! 5 зарядов x10 каждому"
    elif evt == "autoboom":
        auto_boom_time = 10.0
        event_message = "🏃 АВТОБУМ! Автоклик x3 на 10 сек"
    elif evt == "automega":
        auto_mega_time = 5.0
        event_message = "🚀 АВТО-МЕГА! Автоклик x10 на 5 сек"
    elif evt == "freeze":
        freeze_time = 3.0
        event_message = "❄️ ЗАМОРОЗКА! Клики отключены на 3 сек"
    elif evt == "swap":
        p1["score"], p2["score"] = p2["score"], p1["score"]
        event_message = "🔄 ОБМЕН! Счета поменялись местами"
    elif evt == "power":
        p1["power"] += 5; p2["power"] += 5
        event_message = "💎 +5 к силе клика каждому"
    elif evt == "megapower":
        p1["power"] += 15; p2["power"] += 15
        event_message = "💠 МЕГА-СИЛА! +15 к силе клика каждому"
    elif evt == "autoclick":
        p1["auto"] += 5; p2["auto"] += 5
        event_message = "⏩ +5 автокликов каждому"
    elif evt == "robbery":
        if p1["score"] > p2["score"]:
            stolen = p1["score"] // 5
            p1["score"] -= stolen; p2["score"] += stolen
            event_message = f"☠️ ОГРАБЛЕНИЕ! У игрока 1 украдено {stolen}"
        elif p2["score"] > p1["score"]:
            stolen = p2["score"] // 5
            p2["score"] -= stolen; p1["score"] += stolen
            event_message = f"☠️ ОГРАБЛЕНИЕ! У игрока 2 украдено {stolen}"
        else:
            event_message = "☠️ ОГРАБЛЕНИЕ провалилось — ничья"
    elif evt == "lucky":
        temp_crit_time = 15.0
        event_message = "🍀 УДАЧА! +10% крит на 15 сек"
    elif evt == "chaos":
        d1 = random.randint(-80, 150)
        d2 = random.randint(-80, 150)
        p1["score"] = max(0, p1["score"] + d1)
        p2["score"] = max(0, p2["score"] + d2)
        event_message = f"🎲 ХАОС! Игрок1 {d1:+d}, Игрок2 {d2:+d}"
    elif evt == "shield":
        shield_active = True
        event_message = "🛡️ ЩИТ! След. негативное событие отражено"

    event_message_timer = 3.5

# ============================================================
# ГЛАВНЫЙ ЦИКЛ
# ============================================================
running = True
while running:
    dt = clock.tick(FPS) / 1000.0

    # ============================================================
    # ОБРАБОТКА ВВОДА
    # ============================================================
    for event in ed.event.get():
        if event.type == ed.QUIT:
            running = False

        elif event.type == ed.KEYDOWN:
            # --- Подтверждение сброса ---
            if confirm_reset:
                if event.key in (ed.K_y, ed.K_RETURN, ed.K_DELETE):
                    reset_game()
                    confirm_reset = False
                elif event.key in (ed.K_n, ed.K_ESCAPE):
                    confirm_reset = False
                continue

            # --- Обычное управление ---
            if event.key == ed.K_RETURN:
                running = False

            elif event.key == ed.K_DELETE:
                confirm_reset = True

            # -------- ИГРОК 2 --------
            elif event.key == ed.K_SPACE:
                do_click(p2, button2_rect.center, COLOR_P2)

            elif event.key == ed.K_b:
                shop_open_p2 = not shop_open_p2

            elif event.key == ed.K_z:
                # Купить самое дешёвое доступное у игрока 2
                best_idx = -1
                best_cost = float("inf")
                for i in range(NUM_UPGRADES):
                    if p2["score"] >= p2["costs"][i] and p2["costs"][i] < best_cost:
                        best_cost = p2["costs"][i]
                        best_idx = i
                if best_idx >= 0:
                    buy(p2, best_idx)
                    popups.append({"pos": [button2_rect.centerx - 40,
                                           button2_rect.centery - 40],
                                   "life": 60, "alpha": 255,
                                   "text": f"🛒 {UPGRADES[best_idx]['name']}!",
                                   "color": COLOR_P2})
                else:
                    popups.append({"pos": [button2_rect.centerx - 60,
                                           button2_rect.centery - 40],
                                   "life": 50, "alpha": 255,
                                   "text": "❌ нет денег",
                                   "color": (255, 80, 80)})

            # Цифры 1..8 — покупка конкретного улучшения у 2-го игрока
            elif event.key in (ed.K_1, ed.K_2, ed.K_3, ed.K_4,
                               ed.K_5, ed.K_6, ed.K_7, ed.K_8):
                idx = event.key - ed.K_1
                if buy(p2, idx):
                    popups.append({"pos": [button2_rect.centerx - 40,
                                           button2_rect.centery - 40],
                                   "life": 60, "alpha": 255,
                                   "text": f"🛒 {UPGRADES[idx]['name']}!",
                                   "color": COLOR_P2})

        elif event.type == ed.MOUSEBUTTONDOWN and event.button == 1 and not confirm_reset:
            pos = event.pos

            # 1. Кнопки-переключатели магазинов
            if SHOP_BTN_P1.collidepoint(pos):
                shop_open_p1 = not shop_open_p1
                continue
            if SHOP_BTN_P2.collidepoint(pos):
                shop_open_p2 = not shop_open_p2
                continue

            # 2. Клики внутри панели магазина 1 (если открыта)
            if shop_anim_p1 > 0.5 and get_panel_p1_rect().collidepoint(pos):
                px = get_panel_p1_rect().x
                for i in range(NUM_UPGRADES):
                    if panel_upgrade_rect(px, i).collidepoint(pos):
                        buy(p1, i)
                        break
                continue

            # 3. Клики внутри панели магазина 2
            if shop_anim_p2 > 0.5 and get_panel_p2_rect().collidepoint(pos):
                px = get_panel_p2_rect().x
                for i in range(NUM_UPGRADES):
                    if panel_upgrade_rect(px, i).collidepoint(pos):
                        buy(p2, i)
                        break
                continue

            # 4. Клик по главной кнопке 1-го игрока
            if button1_rect.collidepoint(pos):
                do_click(p1, pos, COLOR_P1)

    # ============================================================
    # АНИМАЦИЯ МАГАЗИНОВ
    # ============================================================
    if shop_open_p1:
        shop_anim_p1 = min(1.0, shop_anim_p1 + 0.10)
    else:
        shop_anim_p1 = max(0.0, shop_anim_p1 - 0.10)

    if shop_open_p2:
        shop_anim_p2 = min(1.0, shop_anim_p2 + 0.10)
    else:
        shop_anim_p2 = max(0.0, shop_anim_p2 - 0.10)

    # ============================================================
    # ОБНОВЛЕНИЕ ЛОГИКИ (если не открыт диалог сброса)
    # ============================================================
    if not confirm_reset:
        # --- Анимация кликов ---
        for p in (p1, p2):
            if p["scale"] < 1.0:
                p["scale"] = min(1.0, p["scale"] + 0.05)

        # --- Автодоход ---
        for p in (p1, p2):
            if p["auto"] > 0:
                rate = p["auto"] * p["auto_mult"]
                if auto_boom_time > 0:
                    rate *= 3
                if auto_mega_time > 0:
                    rate *= 10
                p["auto_acc"] += rate * dt
                while p["auto_acc"] >= 1:
                    p["auto_acc"] -= 1
                    income = max(1, int(p["power"] * p["mult"] * p["mega_mult"] * 0.5))
                    p["score"] += income

        # --- Таймер события ---
        event_timer -= dt
        if event_timer <= 0:
            event_timer = EVENT_INTERVAL
            trigger_event()

        # --- Убывание эффектов ---
        if double_time > 0:     double_time = max(0.0, double_time - dt)
        if mega_click_time > 0: mega_click_time = max(0.0, mega_click_time - dt)
        if freeze_time > 0:     freeze_time = max(0.0, freeze_time - dt)
        if auto_boom_time > 0:  auto_boom_time = max(0.0, auto_boom_time - dt)
        if auto_mega_time > 0:  auto_mega_time = max(0.0, auto_mega_time - dt)
        if temp_crit_time > 0:  temp_crit_time = max(0.0, temp_crit_time - dt)
        if temp_power_time > 0: temp_power_time = max(0.0, temp_power_time - dt)
        if event_message_timer > 0:
            event_message_timer = max(0.0, event_message_timer - dt)

        # --- Автосохранение ---
        autosave_timer -= dt
        if autosave_timer <= 0:
            autosave_timer = AUTOSAVE_INTERVAL
            save_game()

    # ============================================================
    # ОТРИСОВКА
    # ============================================================
    screen.fill(COLOR_BG)
    ed.draw.line(screen, (60, 60, 90), (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 2)

    # --- Счёт игроков ---
    s1 = font_big.render(f"Игрок 1: {p1['score']}", True, COLOR_P1)
    screen.blit(s1, s1.get_rect(center=(PLAYER1_X, 45)))
    s2 = font_big.render(f"Игрок 2: {p2['score']}", True, COLOR_P2)
    screen.blit(s2, s2.get_rect(center=(PLAYER2_X, 45)))

    # --- Таймер события ---
    bar_width, bar_height = 500, 22
    bar_x = WIDTH // 2 - bar_width // 2
    bar_y = 25
    ed.draw.rect(screen, (60, 60, 90), (bar_x, bar_y, bar_width, bar_height), border_radius=10)
    ratio = 1.0 - (event_timer / EVENT_INTERVAL)
    ed.draw.rect(screen, COLOR_GOLD,
                 (bar_x, bar_y, int(bar_width * ratio), bar_height), border_radius=10)
    timer_color = (255, 100, 100) if event_timer < 5 else COLOR_GOLD
    timer_txt = font_mid.render(f"Событие через: {event_timer:4.1f}с", True, timer_color)
    screen.blit(timer_txt, timer_txt.get_rect(center=(WIDTH // 2, 75)))

    # --- Индикаторы активных эффектов ---
    y_eff = 110
    effects = []
    if double_time > 0:     effects.append((f"⚡ X2 КЛИКИ: {double_time:.1f}с", (255, 100, 255)))
    if mega_click_time > 0: effects.append((f"🔥 X5 КЛИКИ: {mega_click_time:.1f}с", (255, 150, 50)))
    if auto_boom_time > 0:  effects.append((f"🏃 АВТОБУМ: {auto_boom_time:.1f}с", (100, 255, 150)))
    if auto_mega_time > 0:  effects.append((f"🚀 АВТО-МЕГА: {auto_mega_time:.1f}с", (100, 255, 255)))
    if freeze_time > 0:     effects.append((f"❄️ ЗАМОРОЗКА: {freeze_time:.1f}с", (150, 200, 255)))
    if temp_crit_time > 0:  effects.append((f"🍀 УДАЧА: {temp_crit_time:.1f}с", (150, 255, 150)))
    if temp_power_time > 0: effects.append((f"💪 СИЛА: {temp_power_time:.1f}с", (255, 220, 100)))
    if shield_active:       effects.append(("🛡️ ЩИТ активен", (200, 200, 255)))

    for text, color in effects:
        t = font_small.render(text, True, color)
        screen.blit(t, t.get_rect(center=(WIDTH // 2, y_eff)))
        y_eff += 30

    # --- Клик-кнопки игроков ---
    w = int(260 * p1["scale"])
    scaled1 = ed.transform.smoothscale(button_img, (w, w))
    screen.blit(scaled1, scaled1.get_rect(center=button1_rect.center))

    w = int(260 * p2["scale"])
    scaled2 = ed.transform.smoothscale(button_img2, (w, w))
    screen.blit(scaled2, scaled2.get_rect(center=button2_rect.center))

    # --- Информация под кнопками ---
    info1 = (f"Сила:{p1['power']}  Авто:{p1['auto']}/с  Множ:x{p1['mult']:.2f}  "
             f"Крит:{int(p1['crit']*100)}%x{p1['crit_mult']:.1f}  Мега:x{p1['mega_mult']:.2f}")
    if p1["golden"] > 0: info1 += f"  🌟x{p1['golden']}"
    t = font_mini.render(info1, True, (200, 200, 200))
    screen.blit(t, t.get_rect(center=(PLAYER1_X, 450)))

    info2 = (f"Сила:{p2['power']}  Авто:{p2['auto']}/с  Множ:x{p2['mult']:.2f}  "
             f"Крит:{int(p2['crit']*100)}%x{p2['crit_mult']:.1f}  Мега:x{p2['mega_mult']:.2f}")
    if p2["golden"] > 0: info2 += f"  🌟x{p2['golden']}"
    t = font_mini.render(info2, True, (200, 200, 200))
    screen.blit(t, t.get_rect(center=(PLAYER2_X, 450)))

    # --- Кнопки "Магазин" ---
    for btn, color, opened, label in (
        (SHOP_BTN_P1, COLOR_P1, shop_open_p1, "🛒 МАГАЗИН (клик)"),
        (SHOP_BTN_P2, COLOR_P2, shop_open_p2, "🛒 МАГАЗИН (B)"),
    ):
        bg = (60, 80, 120) if opened else (40, 40, 60)
        ed.draw.rect(screen, bg, btn, border_radius=12)
        ed.draw.rect(screen, color, btn, 3, border_radius=12)
        t = font_small.render(label, True, color)
        screen.blit(t, t.get_rect(center=btn.center))

    # --- Подсказки ---
    hint2 = font_mini.render("ПРОБЕЛ — клик  |  B — магазин  |  Z — купить дешёвое  |  1..8 — купить конкретное",
                             True, COLOR_P2)
    screen.blit(hint2, hint2.get_rect(center=(PLAYER2_X, 680)))

    # ============================================================
    # ОТРИСОВКА ПАНЕЛЕЙ-МАГАЗИНОВ (поверх игрового поля)
    # ============================================================
    def draw_shop_panel(panel_rect, player, color, opened):
        """Рисует выезжающую панель магазина"""
        if panel_rect.right <= 0 or panel_rect.left >= WIDTH:
            return

        # Фон панели
        ed.draw.rect(screen, COLOR_PANEL_BG, panel_rect)
        # Красивая светящаяся рамка с внутренней стороны
        if panel_rect.x <= 0:
            # P1 панель — правая граница
            ed.draw.line(screen, color, (panel_rect.right - 1, 0),
                         (panel_rect.right - 1, HEIGHT), 4)
        else:
            # P2 панель — левая граница
            ed.draw.line(screen, color, (panel_rect.x, 0),
                         (panel_rect.x, HEIGHT), 4)

        # Заголовок
        title = font_big.render("МАГАЗИН", True, color)
        screen.blit(title, title.get_rect(center=(panel_rect.centerx, 50)))
        # Счёт игрока
        sc = font_mid.render(f"💰 {player['score']}", True, COLOR_GOLD)
        screen.blit(sc, sc.get_rect(center=(panel_rect.centerx, 110)))

        # Кнопки улучшений
        px = panel_rect.x
        for i, upg in enumerate(UPGRADES):
            rect = panel_upgrade_rect(px, i)
            if rect.right < 0 or rect.left > WIDTH:
                continue

            affordable = player["score"] >= player["costs"][i]
            if affordable:
                bg = COLOR_BTN_BG_OK if color == COLOR_P1 else COLOR_BTN_BG_OK2
            else:
                bg = COLOR_BTN_BG

            ed.draw.rect(screen, bg, rect, border_radius=10)
            border = color if affordable else (80, 80, 100)
            ed.draw.rect(screen, border, rect, 2, border_radius=10)

            # Название + уровень
            name = font_small.render(f"{i+1}. {upg['name']} ур.{player['levels'][i]}",
                                     True, color)
            screen.blit(name, (rect.x + 12, rect.y + 6))
            # Описание
            desc = font_mini.render(upg["desc"], True, (190, 190, 210))
            screen.blit(desc, (rect.x + 12, rect.y + 30))
            # Цена справа
            cost_color = COLOR_GOLD if affordable else (140, 140, 140)
            cost = font_small.render(f"{player['costs'][i]}", True, cost_color)
            screen.blit(cost, (rect.right - cost.get_width() - 12, rect.y + 20))

    draw_shop_panel(get_panel_p1_rect(), p1, COLOR_P1, shop_open_p1)
    draw_shop_panel(get_panel_p2_rect(), p2, COLOR_P2, shop_open_p2)

    # ============================================================
    # ПЛАВАЮЩИЕ ВСПЛЫВАШКИ "+N"
    # ============================================================
    for p in popups[:]:
        p["life"] -= 1
        p["pos"][1] -= 1.5
        p["alpha"] = max(0, int(255 * (p["life"] / 60)))
        pop_surf = font_small.render(p["text"], True, p["color"])
        pop_surf.set_alpha(p["alpha"])
        screen.blit(pop_surf, p["pos"])
        if p["life"] <= 0:
            popups.remove(p)

    # --- Сообщение о событии ---
    if event_message_timer > 0:
        alpha = min(255, int(event_message_timer * 255))
        msg = font_mid.render(event_message, True, COLOR_GOLD)
        msg.set_alpha(alpha)
        screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT - 90)))

    # --- Курсор ---
    mouse_pos = ed.mouse.get_pos()
    hovering = False
    if not confirm_reset:
        if SHOP_BTN_P1.collidepoint(mouse_pos) or SHOP_BTN_P2.collidepoint(mouse_pos):
            hovering = True
        elif button1_rect.collidepoint(mouse_pos):
            hovering = True
        elif shop_anim_p1 > 0.5:
            px = get_panel_p1_rect().x
            for i in range(NUM_UPGRADES):
                if panel_upgrade_rect(px, i).collidepoint(mouse_pos):
                    hovering = True
                    break
        elif shop_anim_p2 > 0.5:
            px = get_panel_p2_rect().x
            for i in range(NUM_UPGRADES):
                if panel_upgrade_rect(px, i).collidepoint(mouse_pos):
                    hovering = True
                    break
    if hovering:
        ed.mouse.set_cursor(ed.SYSTEM_CURSOR_HAND)
    else:
        ed.mouse.set_cursor(ed.SYSTEM_CURSOR_ARROW)

    # --- Подсказка снизу ---
    hint = font_mini.render(
        "Игрок 1: мышь  |  Игрок 2: ПРОБЕЛ + B + Z + 1..8  |  ENTER — выход  |  DELETE — стереть прогресс  |  💾 автосейв 30с",
        True, COLOR_GRAY)
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 25)))

    # ============================================================
    # ОКНО ПОДТВЕРЖДЕНИЯ СБРОСА
    # ============================================================
    if confirm_reset:
        overlay = ed.Surface((WIDTH, HEIGHT), ed.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        box_w, box_h = 900, 340
        box = ed.Rect(WIDTH // 2 - box_w // 2, HEIGHT // 2 - box_h // 2, box_w, box_h)
        ed.draw.rect(screen, (40, 20, 30), box, border_radius=20)
        ed.draw.rect(screen, COLOR_RED, box, 4, border_radius=20)

        t1 = font_big.render("⚠️ СТЕРЕТЬ ПРОГРЕСС?", True, COLOR_RED)
        screen.blit(t1, t1.get_rect(center=(WIDTH // 2, box.y + 70)))

        t2 = font_mid.render("Весь прогресс и файл save.json будут удалены!",
                             True, (255, 220, 220))
        screen.blit(t2, t2.get_rect(center=(WIDTH // 2, box.y + 150)))

        t3 = font_small.render("Y / ENTER — подтвердить    |    N / ESC — отмена",
                               True, COLOR_GOLD)
        screen.blit(t3, t3.get_rect(center=(WIDTH // 2, box.y + 230)))

        blink = (ed.time.get_ticks() // 400) % 2
        if blink:
            t4 = font_tiny.render("Это действие необратимо!", True, (255, 120, 120))
            screen.blit(t4, t4.get_rect(center=(WIDTH // 2, box.y + 290)))

    ed.display.flip()

# ============================================================
# СОХРАНЕНИЕ И ВЫХОД
# ============================================================
save_game()
ed.quit()
sys.exit()