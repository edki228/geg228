# ============================================================
# ДВУХИГРОВОЙ КЛИКЕР С УЛУЧШЕНИЯМИ И РАНДОМНЫМИ СОБЫТИЯМИ
# Игрок 1 — мышь
# Игрок 2 — ПРОБЕЛ (клик) + Z (покупка самого дешёвого улучшения)
# Прогресс сохраняется в файл save.json при выходе
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

# ---------- РАЗМЕРЫ ЭКРАНА ----------
WIDTH, HEIGHT = 1820, 800
screen = ed.display.set_mode((WIDTH, HEIGHT), ed.FULLSCREEN)
ed.display.set_caption("огризок")

# ---------- ШРИФТЫ РАЗНЫХ РАЗМЕРОВ ----------
font_big = ed.font.Font(None, 64)
font_mid = ed.font.Font(None, 40)
font_small = ed.font.Font(None, 30)
font_tiny = ed.font.Font(None, 22)

# ---------- ЗАГРУЗКА И ЗАПУСК МУЗЫКИ ----------
try:
    ed.mixer.music.load("muzika.mp3")
    ed.mixer.music.play(-1)
except Exception:
    print("музыка не загрузилась, ну и ладно")

# ---------- ЧАСЫ / ОГРАНИЧЕНИЕ FPS ----------
clock = ed.time.Clock()
FPS = 240

# ============================================================
# ЗАГРУЗКА КАРТИНОК ДЛЯ КНОПОК ИГРОКОВ
# ============================================================
# Картинка для 1-го игрока (синий круг)
try:
    button_img = ed.image.load("igrok.png").convert_alpha()
    button_img = ed.transform.smoothscale(button_img, (260, 260))
except FileNotFoundError:
    button_img = ed.Surface((260, 260), ed.SRCALPHA)
    ed.draw.circle(button_img, (110, 193, 255), (130, 130), 130)
    print("ты зыбыл фел периминавать")

# Картинка для 2-го игрока (красный круг)
button_img2 = ed.Surface((260, 260), ed.SRCALPHA)
ed.draw.circle(button_img2, (255, 130, 130), (130, 130), 130)

# ---------- ПОЗИЦИИ КЛИК-КНОПОК ИГРОКОВ ----------
PLAYER1_X = WIDTH // 4
PLAYER2_X = WIDTH * 3 // 4
button1_rect = button_img.get_rect(center=(PLAYER1_X, 320))
button2_rect = button_img2.get_rect(center=(PLAYER2_X, 320))

# ============================================================
# ОПРЕДЕЛЕНИЕ ВИДОВ УЛУЧШЕНИЙ
# ============================================================
# Каждое улучшение: название, базовая цена, коэффициент роста цены
UPGRADES = [
    {"name": "Клик",  "base_cost": 10,  "cost_mult": 1.5},   # +1 к силе клика
    {"name": "Авто",  "base_cost": 50,  "cost_mult": 1.7},   # +1 авто-очко в секунду
    {"name": "Множ",  "base_cost": 200, "cost_mult": 2.2},   # x1.15 к клику
    {"name": "Крит",  "base_cost": 150, "cost_mult": 1.9},   # +5% шанс крита x5
]

# ============================================================
# СОЗДАНИЕ ИГРОКОВ (словарь с параметрами)
# ============================================================
def make_player():
    """Создаёт словарь с состоянием игрока"""
    return {
        "score": 0,          # очки
        "power": 1,          # сила одного клика
        "auto": 0,           # автокликов в секунду
        "mult": 1.0,         # множитель клика
        "crit": 0.0,         # шанс крита (0..1)
        "levels": [0, 0, 0, 0],          # уровни каждого улучшения
        "costs": [10, 50, 200, 150],     # текущая цена каждого улучшения
        "scale": 1.0,        # для анимации нажатия
        "auto_acc": 0.0,     # аккумулятор для автокликов
        "golden": 0,         # сколько "золотых" кликов осталось
    }

p1 = make_player()
p2 = make_player()

# ============================================================
# СОХРАНЕНИЕ И ЗАГРУЗКА ПРОГРЕССА
# ============================================================
SAVE_FILE = "save.json"

def save_game():
    """Сохраняет прогресс обоих игроков в файл save.json"""
    data = {
        "p1": {
            "score": p1["score"],
            "power": p1["power"],
            "auto": p1["auto"],
            "mult": p1["mult"],
            "crit": p1["crit"],
            "levels": p1["levels"],
            "costs": p1["costs"],
        },
        "p2": {
            "score": p2["score"],
            "power": p2["power"],
            "auto": p2["auto"],
            "mult": p2["mult"],
            "crit": p2["crit"],
            "levels": p2["levels"],
            "costs": p2["costs"],
        },
    }
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("💾 Прогресс сохранён в", SAVE_FILE)
    except Exception as e:
        print("Не удалось сохранить:", e)

def load_game():
    """Загружает прогресс из файла save.json, если он есть"""
    if not os.path.exists(SAVE_FILE):
        print("Сохранения нет — начинаем с нуля")
        return
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for key, player in (("p1", p1), ("p2", p2)):
            if key in data:
                player["score"] = data[key].get("score", 0)
                player["power"] = data[key].get("power", 1)
                player["auto"]  = data[key].get("auto", 0)
                player["mult"]  = data[key].get("mult", 1.0)
                player["crit"]  = data[key].get("crit", 0.0)
                player["levels"] = data[key].get("levels", [0, 0, 0, 0])
                player["costs"]  = data[key].get("costs", [10, 50, 200, 150])
        print("📂 Прогресс загружен из", SAVE_FILE)
    except Exception as e:
        print("Не удалось загрузить сохранение:", e)

# ---------- ЗАГРУЖАЕМ ПРОГРЕСС СРАЗУ ПОСЛЕ СОЗДАНИЯ ИГРОКОВ ----------
load_game()

# ============================================================
# ЦВЕТА
# ============================================================
COLOR_P1 = (110, 193, 255)     # цвет 1-го игрока (синий)
COLOR_P2 = (255, 130, 130)     # цвет 2-го игрока (красный)
COLOR_BG = (30, 30, 47)        # фон
COLOR_GOLD = (255, 215, 0)     # золотой (для событий/таймера)
COLOR_GRAY = (150, 150, 150)   # серый (подсказки)

# ============================================================
# ВСПЛЫВАЮЩИЕ "+N" ПРИ КЛИКЕ
# ============================================================
popups = []

# ============================================================
# ПЕРЕМЕННЫЕ ДЛЯ СОБЫТИЙ И ТАЙМЕРОВ
# ============================================================
EVENT_INTERVAL = 20.0          # интервал между событиями в секундах
event_timer = EVENT_INTERVAL   # сколько ещё до следующего события
double_time = 0.0              # время действия X2 на клики
freeze_time = 0.0              # время действия заморозки
auto_boom_time = 0.0           # время действия автобума (x3 авто)
event_message = ""             # текст последнего события
event_message_timer = 0.0      # время показа сообщения

# ---------- АВТОСОХРАНЕНИЕ РАЗ В 30 СЕКУНД ----------
AUTOSAVE_INTERVAL = 30.0
autosave_timer = AUTOSAVE_INTERVAL

# ============================================================
# ФУНКЦИЯ ПОЛУЧЕНИЯ ПРЯМОУГОЛЬНИКА КНОПКИ УЛУЧШЕНИЯ
# ============================================================
def upgrade_rect(player_x, idx):
    """Возвращает прямоугольник кнопки улучшения idx в колонке игрока"""
    col = idx % 2
    row = idx // 2
    cx = player_x + (-125 if col == 0 else 125)
    cy = 530 + row * 85
    return ed.Rect(cx - 120, cy - 37, 240, 75)

# ============================================================
# ФУНКЦИЯ РАСЧЁТА УРОНА ОТ КЛИКА
# ============================================================
def compute_damage(player):
    """Считает, сколько очков принесёт клик (и был ли крит)"""
    dmg = player["power"] * player["mult"]

    # X2 от события
    if double_time > 0:
        dmg *= 2

    # Проверка на крит
    is_crit = random.random() < player["crit"]
    if is_crit:
        dmg *= 5

    # Золотой клик (одноразово x10)
    is_golden = False
    if player["golden"] > 0:
        dmg *= 10
        player["golden"] -= 1
        is_golden = True

    return max(1, int(dmg)), is_crit, is_golden

# ============================================================
# ФУНКЦИЯ ОБРАБОТКИ КЛИКА
# ============================================================
def do_click(player, pos, color):
    """Обрабатывает клик игрока"""
    # Если действует заморозка — клики не работают
    if freeze_time > 0:
        popups.append({
            "pos": [pos[0], pos[1]],
            "life": 40,
            "alpha": 255,
            "text": "❄️",
            "color": (150, 200, 255),
        })
        return

    dmg, is_crit, is_golden = compute_damage(player)
    player["score"] += dmg
    player["scale"] = 0.9  # анимация нажатия

    # Текст всплывашки
    if is_golden:
        text = f"🌟 +{dmg}"
    elif is_crit:
        text = f"КРИТ! +{dmg}"
    else:
        text = f"+{dmg}"

    popups.append({
        "pos": [pos[0], pos[1]],
        "life": 60,
        "alpha": 255,
        "text": text,
        "color": color,
    })

# ============================================================
# ФУНКЦИЯ ПОКУПКИ УЛУЧШЕНИЯ
# ============================================================
def buy(player, idx):
    """Пытается купить улучшение idx у игрока"""
    cost = player["costs"][idx]
    if player["score"] < cost:
        return False

    player["score"] -= cost
    player["levels"][idx] += 1
    # Увеличиваем цену следующего уровня
    player["costs"][idx] = int(player["costs"][idx] * UPGRADES[idx]["cost_mult"])

    # Применяем эффект улучшения
    if idx == 0:      # +1 к силе клика
        player["power"] += 1
    elif idx == 1:    # +1 к автоклику
        player["auto"] += 1
    elif idx == 2:    # x1.15 к множителю
        player["mult"] *= 1.15
    elif idx == 3:    # +5% крит-шанс
        player["crit"] = min(1.0, player["crit"] + 0.05)

    return True

# ============================================================
# ФУНКЦИЯ СЛУЧАЙНОГО СОБЫТИЯ
# ============================================================
def trigger_event():
    """Срабатывает раз в 20 секунд. Выбирает случайное событие."""
    global event_message, event_message_timer
    global double_time, freeze_time, auto_boom_time

    evt = random.choice([
        "bonus", "double", "penalty", "gift", "golden",
        "autoboom", "freeze", "swap", "power", "robbery"
    ])

    if evt == "bonus":
        p1["score"] += 50
        p2["score"] += 50
        event_message = "🎁 БОНУС! +50 каждому"

    elif evt == "double":
        double_time = 10.0
        event_message = "⚡ X2 КЛИКИ НА 10 СЕКУНД!"

    elif evt == "penalty":
        p1["score"] = max(0, p1["score"] - 30)
        p2["score"] = max(0, p2["score"] - 30)
        event_message = "💀 ШТРАФ! -30 каждому"

    elif evt == "gift":
        if p1["score"] > p2["score"]:
            p2["score"] += 100
            event_message = "🎈 ПОДАРОК: игрок 2 получает 100!"
        elif p2["score"] > p1["score"]:
            p1["score"] += 100
            event_message = "🎈 ПОДАРОК: игрок 1 получает 100!"
        else:
            p1["score"] += 50
            p2["score"] += 50
            event_message = "🎈 Ничья! +50 каждому"

    elif evt == "golden":
        p1["golden"] += 1
        p2["golden"] += 1
        event_message = "🌟 ЗОЛОТОЙ КЛИК! Следующий клик x10"

    elif evt == "autoboom":
        auto_boom_time = 10.0
        event_message = "🏃 АВТОБУМ! Автоклик x3 на 10 сек"

    elif evt == "freeze":
        freeze_time = 3.0
        event_message = "❄️ ЗАМОРОЗКА! Клики отключены на 3 сек"

    elif evt == "swap":
        p1["score"], p2["score"] = p2["score"], p1["score"]
        event_message = "🔄 ОБМЕН! Счета поменялись местами"

    elif evt == "power":
        p1["power"] += 5
        p2["power"] += 5
        event_message = "💎 БОГАТСТВО! +5 к силе клика каждому"

    elif evt == "robbery":
        if p1["score"] > p2["score"]:
            stolen = p1["score"] // 5
            p1["score"] -= stolen
            p2["score"] += stolen
            event_message = f"☠️ ОГРАБЛЕНИЕ! У игрока 1 украдено {stolen}"
        elif p2["score"] > p1["score"]:
            stolen = p2["score"] // 5
            p2["score"] -= stolen
            p1["score"] += stolen
            event_message = f"☠️ ОГРАБЛЕНИЕ! У игрока 2 украдено {stolen}"
        else:
            event_message = "☠️ ОГРАБЛЕНИЕ провалилось — ничья"

    event_message_timer = 3.5

# ============================================================
# ГЛАВНЫЙ ИГРОВОЙ ЦИКЛ
# ============================================================
running = True
while running:
    # ---------- ВРЕМЯ КАДРА В СЕКУНДАХ ----------
    dt = clock.tick(FPS) / 1000.0

    # ========================================================
    # БЛОК ОБРАБОТКИ СОБЫТИЙ ВВОДА
    # ========================================================
    for event in ed.event.get():
        # --- Закрытие окна ---
        if event.type == ed.QUIT:
            running = False

        # --- Нажатия клавиш ---
        elif event.type == ed.KEYDOWN:
            if event.key == ed.K_RETURN:      # Выход по Enter
                running = False

            elif event.key == ed.K_SPACE:     # Пробел = клик 2-го игрока
                do_click(p2, button2_rect.center, COLOR_P2)

            # ================================================
            # Z — покупка улучшения у 2-го игрока
            # Автоматически покупается САМОЕ ДЕШЁВОЕ доступное
            # ================================================
            elif event.key == ed.K_z:
                best_idx = -1
                best_cost = float("inf")
                for i in range(4):
                    if p2["score"] >= p2["costs"][i] and p2["costs"][i] < best_cost:
                        best_cost = p2["costs"][i]
                        best_idx = i

                if best_idx >= 0:
                    buy(p2, best_idx)
                    popups.append({
                        "pos": [button2_rect.centerx - 40,
                                button2_rect.centery - 40],
                        "life": 60,
                        "alpha": 255,
                        "text": f"🛒 {UPGRADES[best_idx]['name']}!",
                        "color": COLOR_P2,
                    })
                else:
                    popups.append({
                        "pos": [button2_rect.centerx - 60,
                                button2_rect.centery - 40],
                        "life": 50,
                        "alpha": 255,
                        "text": "❌ нет денег",
                        "color": (255, 80, 80),
                    })

        # --- Клики мышью ---
        elif event.type == ed.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Клик по главной кнопке 1-го игрока
            if button1_rect.collidepoint(pos):
                do_click(p1, pos, COLOR_P1)
            else:
                bought = False
                # Клики по улучшениям 1-го игрока
                for i in range(4):
                    if upgrade_rect(PLAYER1_X, i).collidepoint(pos):
                        buy(p1, i)
                        bought = True
                        break
                # Клики по улучшениям 2-го игрока (мышью тоже можно)
                if not bought:
                    for i in range(4):
                        if upgrade_rect(PLAYER2_X, i).collidepoint(pos):
                            buy(p2, i)
                            break

    # ========================================================
    # БЛОК ОБНОВЛЕНИЯ АНИМАЦИИ КЛИКОВ
    # ========================================================
    for p in (p1, p2):
        if p["scale"] < 1.0:
            p["scale"] = min(1.0, p["scale"] + 0.05)

    # ========================================================
    # БЛОК АВТОКЛИКОВ (генерируют очки без нажатий)
    # ========================================================
    for p in (p1, p2):
        if p["auto"] > 0:
            rate = p["auto"]
            if auto_boom_time > 0:
                rate *= 3  # автобум утраивает
            p["auto_acc"] += rate * dt
            while p["auto_acc"] >= 1:
                p["auto_acc"] -= 1
                p["score"] += max(1, int(p["power"] * p["mult"]))

    # ========================================================
    # БЛОК ТАЙМЕРОВ (события, X2, заморозка и т.д.)
    # ========================================================
    # --- Таймер до следующего случайного события ---
    event_timer -= dt
    if event_timer <= 0:
        event_timer = EVENT_INTERVAL
        trigger_event()

    # --- Убывание таймеров эффектов ---
    if double_time > 0:
        double_time = max(0.0, double_time - dt)
    if freeze_time > 0:
        freeze_time = max(0.0, freeze_time - dt)
    if auto_boom_time > 0:
        auto_boom_time = max(0.0, auto_boom_time - dt)
    if event_message_timer > 0:
        event_message_timer = max(0.0, event_message_timer - dt)

    # --- Таймер автосохранения ---
    autosave_timer -= dt
    if autosave_timer <= 0:
        autosave_timer = AUTOSAVE_INTERVAL
        save_game()

    # ========================================================
    # БЛОК ОТРИСОВКИ (всё что видно на экране)
    # ========================================================
    screen.fill(COLOR_BG)

    # --- Разделительная линия между игроками ---
    ed.draw.line(screen, (60, 60, 90), (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 2)

    # --- Счёт 1-го игрока ---
    s1 = font_big.render(f"Игрок 1: {p1['score']}", True, COLOR_P1)
    screen.blit(s1, s1.get_rect(center=(PLAYER1_X, 50)))
    # --- Счёт 2-го игрока ---
    s2 = font_big.render(f"Игрок 2: {p2['score']}", True, COLOR_P2)
    screen.blit(s2, s2.get_rect(center=(PLAYER2_X, 50)))

    # --- Полоска таймера до следующего события ---
    bar_width, bar_height = 500, 22
    bar_x = WIDTH // 2 - bar_width // 2
    bar_y = 25
    ed.draw.rect(screen, (60, 60, 90),
                 (bar_x, bar_y, bar_width, bar_height), border_radius=10)
    ratio = 1.0 - (event_timer / EVENT_INTERVAL)
    ed.draw.rect(screen, COLOR_GOLD,
                 (bar_x, bar_y, int(bar_width * ratio), bar_height),
                 border_radius=10)

    # --- Текстовый таймер ---
    timer_color = (255, 100, 100) if event_timer < 5 else COLOR_GOLD
    timer_txt = font_mid.render(f"Событие через: {event_timer:4.1f}с", True, timer_color)
    screen.blit(timer_txt, timer_txt.get_rect(center=(WIDTH // 2, 75)))

    # --- Индикаторы активных эффектов ---
    y_eff = 115
    if double_time > 0:
        d = font_mid.render(f"⚡ X2 КЛИКИ: {double_time:.1f}с", True, (255, 100, 255))
        screen.blit(d, d.get_rect(center=(WIDTH // 2, y_eff)))
        y_eff += 40
    if auto_boom_time > 0:
        d = font_mid.render(f"🏃 АВТОБУМ: {auto_boom_time:.1f}с", True, (100, 255, 150))
        screen.blit(d, d.get_rect(center=(WIDTH // 2, y_eff)))
        y_eff += 40
    if freeze_time > 0:
        d = font_mid.render(f"❄️ ЗАМОРОЗКА: {freeze_time:.1f}с", True, (150, 200, 255))
        screen.blit(d, d.get_rect(center=(WIDTH // 2, y_eff)))

    # --- Отрисовка клик-кнопок игроков (с анимацией) ---
    w = int(260 * p1["scale"])
    scaled1 = ed.transform.smoothscale(button_img, (w, w))
    screen.blit(scaled1, scaled1.get_rect(center=button1_rect.center))

    w = int(260 * p2["scale"])
    scaled2 = ed.transform.smoothscale(button_img2, (w, w))
    screen.blit(scaled2, scaled2.get_rect(center=button2_rect.center))

    # --- Информация о параметрах игроков под кнопками ---
    info1 = f"Сила:{p1['power']}  Авто:{p1['auto']}/с  Множ:x{p1['mult']:.2f}  Крит:{int(p1['crit']*100)}%"
    if p1["golden"] > 0:
        info1 += "  🌟"
    t = font_tiny.render(info1, True, (200, 200, 200))
    screen.blit(t, t.get_rect(center=(PLAYER1_X, 470)))

    info2 = f"Сила:{p2['power']}  Авто:{p2['auto']}/с  Множ:x{p2['mult']:.2f}  Крит:{int(p2['crit']*100)}%"
    if p2["golden"] > 0:
        info2 += "  🌟"
    t = font_tiny.render(info2, True, (200, 200, 200))
    screen.blit(t, t.get_rect(center=(PLAYER2_X, 470)))

    # --- Отрисовка кнопок улучшений ---
    for i in range(4):
        # Кнопка улучшения игрока 1
        rect = upgrade_rect(PLAYER1_X, i)
        affordable = p1["score"] >= p1["costs"][i]
        bg_col = (50, 70, 100) if affordable else (45, 45, 60)
        ed.draw.rect(screen, bg_col, rect, border_radius=10)
        border_col = COLOR_P1 if affordable else (80, 80, 100)
        ed.draw.rect(screen, border_col, rect, 2, border_radius=10)

        name1 = font_small.render(
            f"{UPGRADES[i]['name']} ур.{p1['levels'][i]}", True, COLOR_P1
        )
        screen.blit(name1, (rect.x + 8, rect.y + 4))
        cost1 = font_tiny.render(f"Цена: {p1['costs'][i]}", True, (220, 220, 220))
        screen.blit(cost1, (rect.x + 8, rect.y + 42))

        # Кнопка улучшения игрока 2
        rect = upgrade_rect(PLAYER2_X, i)
        affordable = p2["score"] >= p2["costs"][i]
        bg_col = (100, 60, 60) if affordable else (45, 45, 60)
        ed.draw.rect(screen, bg_col, rect, border_radius=10)
        border_col = COLOR_P2 if affordable else (80, 80, 100)
        ed.draw.rect(screen, border_col, rect, 2, border_radius=10)

        name2 = font_small.render(
            f"{UPGRADES[i]['name']} ур.{p2['levels'][i]}", True, COLOR_P2
        )
        screen.blit(name2, (rect.x + 8, rect.y + 4))
        cost2 = font_tiny.render(f"Цена: {p2['costs'][i]}", True, (220, 220, 220))
        screen.blit(cost2, (rect.x + 8, rect.y + 42))

    # --- Напоминание для 2-го игрока: как покупать ---
    hint2 = font_tiny.render("ПРОБЕЛ — клик   |   Z — купить улучшение", True, COLOR_P2)
    screen.blit(hint2, hint2.get_rect(center=(PLAYER2_X, 620)))

    # --- Плавающие всплывашки "+N" ---
    for p in popups[:]:
        p["life"] -= 1
        p["pos"][1] -= 1.5
        p["alpha"] = max(0, int(255 * (p["life"] / 60)))
        pop_surf = font_small.render(p["text"], True, p["color"])
        pop_surf.set_alpha(p["alpha"])
        screen.blit(pop_surf, p["pos"])
        if p["life"] <= 0:
            popups.remove(p)

    # --- Сообщение о последнем событии ---
    if event_message_timer > 0:
        alpha = min(255, int(event_message_timer * 255))
        msg = font_mid.render(event_message, True, COLOR_GOLD)
        msg.set_alpha(alpha)
        screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT - 90)))

    # --- Смена курсора на "руку" при наведении ---
    mouse_pos = ed.mouse.get_pos()
    hovering = False
    if button1_rect.collidepoint(mouse_pos):
        hovering = True
    else:
        for i in range(4):
            if upgrade_rect(PLAYER1_X, i).collidepoint(mouse_pos) or \
               upgrade_rect(PLAYER2_X, i).collidepoint(mouse_pos):
                hovering = True
                break
    if hovering:
        ed.mouse.set_cursor(ed.SYSTEM_CURSOR_HAND)
    else:
        ed.mouse.set_cursor(ed.SYSTEM_CURSOR_ARROW)

    # --- Подсказка снизу ---
    hint = font_tiny.render(
        "Игрок 1: мышь  |  Игрок 2: ПРОБЕЛ (клик) + Z (улучшение)  |  ENTER — выход  |  💾 автосохранение раз в 30 сек",
        True, COLOR_GRAY
    )
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 30)))

    # --- Показать кадр на экране ---
    ed.display.flip()

# ============================================================
# СОХРАНЕНИЕ ПРОГРЕССА ПРИ ВЫХОДЕ
# ============================================================
save_game()

# ============================================================
# ЗАВЕРШЕНИЕ РАБОТЫ ПРОГРАММЫ
# ============================================================
ed.quit()
sys.exit()