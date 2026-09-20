# ============================================================
# ДВУХИГРОВОЙ КЛИКЕР С УЛУЧШЕНИЯМИ И РАНДОМНЫМИ СОБЫТИЯМИ
# Игрок 1 — мышь
# Игрок 2 — ПРОБЕЛ (клик) + Z (покупка самого дешёвого улучшения)
# Прогресс сохраняется в файл save.json при выходе
# DELETE — сброс прогресса (с подтверждением)
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
try:
    button_img = ed.image.load("igrok.png").convert_alpha()
    button_img = ed.transform.smoothscale(button_img, (260, 260))
except FileNotFoundError:
    button_img = ed.Surface((260, 260), ed.SRCALPHA)
    ed.draw.circle(button_img, (110, 193, 255), (130, 130), 130)
    print("ты зыбыл фел периминавать")

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
UPGRADES = [
    {"name": "Клик",  "base_cost": 10,  "cost_mult": 1.5},
    {"name": "Авто",  "base_cost": 50,  "cost_mult": 1.7},
    {"name": "Множ",  "base_cost": 200, "cost_mult": 2.2},
    {"name": "Крит",  "base_cost": 150, "cost_mult": 1.9},
]

# ============================================================
# СОЗДАНИЕ ИГРОКОВ
# ============================================================
def make_player():
    """Создаёт словарь с состоянием игрока"""
    return {
        "score": 0,
        "power": 1,
        "auto": 0,
        "mult": 1.0,
        "crit": 0.0,
        "levels": [0, 0, 0, 0],
        "costs": [10, 50, 200, 150],
        "scale": 1.0,
        "auto_acc": 0.0,
        "golden": 0,
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

def reset_game():
    """Полностью стирает прогресс — и файл, и оба игрока"""
    # Удаляем файл сохранения
    try:
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
            print("🗑️ Файл сохранения удалён")
    except Exception as e:
        print("Не удалось удалить файл:", e)

    # Сбрасываем игроков
    for player, template in ((p1, make_player()), (p2, make_player())):
        for k, v in template.items():
            player[k] = v

    # Сбрасываем таймеры и эффекты
    global event_timer, double_time, freeze_time, auto_boom_time
    global event_message, event_message_timer, autosave_timer
    event_timer = EVENT_INTERVAL
    double_time = 0.0
    freeze_time = 0.0
    auto_boom_time = 0.0
    event_message = ""
    event_message_timer = 0.0
    autosave_timer = AUTOSAVE_INTERVAL

    popups.clear()
    print("♻️ Прогресс сброшен")

# ---------- ЗАГРУЖАЕМ ПРОГРЕСС СРАЗУ ПОСЛЕ СОЗДАНИЯ ИГРОКОВ ----------
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

# ============================================================
# ВСПЛЫВАЮЩИЕ "+N" ПРИ КЛИКЕ
# ============================================================
popups = []

# ============================================================
# ПЕРЕМЕННЫЕ ДЛЯ СОБЫТИЙ И ТАЙМЕРОВ
# ============================================================
EVENT_INTERVAL = 20.0
event_timer = EVENT_INTERVAL
double_time = 0.0
freeze_time = 0.0
auto_boom_time = 0.0
event_message = ""
event_message_timer = 0.0

# ---------- АВТОСОХРАНЕНИЕ РАЗ В 30 СЕКУНД ----------
AUTOSAVE_INTERVAL = 30.0
autosave_timer = AUTOSAVE_INTERVAL

# ============================================================
# РЕЖИМ ПОДТВЕРЖДЕНИЯ СБРОСА ПРОГРЕССА
# ============================================================
confirm_reset = False   # True — показываем окно "точно сбросить?"

# ============================================================
# ФУНКЦИЯ ПОЛУЧЕНИЯ ПРЯМОУГОЛЬНИКА КНОПКИ УЛУЧШЕНИЯ
# ============================================================
def upgrade_rect(player_x, idx):
    col = idx % 2
    row = idx // 2
    cx = player_x + (-125 if col == 0 else 125)
    cy = 530 + row * 85
    return ed.Rect(cx - 120, cy - 37, 240, 75)

# ============================================================
# ФУНКЦИЯ РАСЧЁТА УРОНА ОТ КЛИКА
# ============================================================
def compute_damage(player):
    dmg = player["power"] * player["mult"]

    if double_time > 0:
        dmg *= 2

    is_crit = random.random() < player["crit"]
    if is_crit:
        dmg *= 5

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
    player["scale"] = 0.9

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
    cost = player["costs"][idx]
    if player["score"] < cost:
        return False

    player["score"] -= cost
    player["levels"][idx] += 1
    player["costs"][idx] = int(player["costs"][idx] * UPGRADES[idx]["cost_mult"])

    if idx == 0:
        player["power"] += 1
    elif idx == 1:
        player["auto"] += 1
    elif idx == 2:
        player["mult"] *= 1.15
    elif idx == 3:
        player["crit"] = min(1.0, player["crit"] + 0.05)

    return True

# ============================================================
# ФУНКЦИЯ СЛУЧАЙНОГО СОБЫТИЯ
# ============================================================
def trigger_event():
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
    dt = clock.tick(FPS) / 1000.0

    # ========================================================
    # БЛОК ОБРАБОТКИ СОБЫТИЙ ВВОДА
    # ========================================================
    for event in ed.event.get():
        if event.type == ed.QUIT:
            running = False

        elif event.type == ed.KEYDOWN:

            # ================================================
            # ЕСЛИ ОТКРЫТО ОКНО ПОДТВЕРЖДЕНИЯ СБРОСА —
            # обрабатываем только его (остальное игнорируем)
            # ================================================
            if confirm_reset:
                if event.key in (ed.K_y, ed.K_RETURN, ed.K_DELETE):
                    # Подтверждение — стираем всё
                    reset_game()
                    confirm_reset = False
                elif event.key in (ed.K_n, ed.K_ESCAPE):
                    # Отмена
                    confirm_reset = False
                continue  # пропускаем остальную логику

            # ================================================
            # ОБЫЧНОЕ УПРАВЛЕНИЕ (когда окно не открыто)
            # ================================================
            if event.key == ed.K_RETURN:
                running = False

            # DELETE — вызвать окно подтверждения сброса
            elif event.key == ed.K_DELETE:
                confirm_reset = True

            elif event.key == ed.K_SPACE:
                do_click(p2, button2_rect.center, COLOR_P2)

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

        # --- Клики мышью (только если окно не открыто) ---
        elif event.type == ed.MOUSEBUTTONDOWN and event.button == 1 and not confirm_reset:
            pos = event.pos

            if button1_rect.collidepoint(pos):
                do_click(p1, pos, COLOR_P1)
            else:
                bought = False
                for i in range(4):
                    if upgrade_rect(PLAYER1_X, i).collidepoint(pos):
                        buy(p1, i)
                        bought = True
                        break
                if not bought:
                    for i in range(4):
                        if upgrade_rect(PLAYER2_X, i).collidepoint(pos):
                            buy(p2, i)
                            break

    # ========================================================
    # БЛОК ОБНОВЛЕНИЯ (только если НЕ открыто окно сброса)
    # ========================================================
    if not confirm_reset:
        # --- Анимация нажатия ---
        for p in (p1, p2):
            if p["scale"] < 1.0:
                p["scale"] = min(1.0, p["scale"] + 0.05)

        # --- Автоклики ---
        for p in (p1, p2):
            if p["auto"] > 0:
                rate = p["auto"]
                if auto_boom_time > 0:
                    rate *= 3
                p["auto_acc"] += rate * dt
                while p["auto_acc"] >= 1:
                    p["auto_acc"] -= 1
                    p["score"] += max(1, int(p["power"] * p["mult"]))

        # --- Таймер события ---
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
    # БЛОК ОТРИСОВКИ
    # ========================================================
    screen.fill(COLOR_BG)

    # --- Разделительная линия ---
    ed.draw.line(screen, (60, 60, 90), (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 2)

    # --- Счёт игроков ---
    s1 = font_big.render(f"Игрок 1: {p1['score']}", True, COLOR_P1)
    screen.blit(s1, s1.get_rect(center=(PLAYER1_X, 50)))
    s2 = font_big.render(f"Игрок 2: {p2['score']}", True, COLOR_P2)
    screen.blit(s2, s2.get_rect(center=(PLAYER2_X, 50)))

    # --- Полоска таймера события ---
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

    # --- Индикаторы эффектов ---
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

    # --- Кнопки игроков ---
    w = int(260 * p1["scale"])
    scaled1 = ed.transform.smoothscale(button_img, (w, w))
    screen.blit(scaled1, scaled1.get_rect(center=button1_rect.center))

    w = int(260 * p2["scale"])
    scaled2 = ed.transform.smoothscale(button_img2, (w, w))
    screen.blit(scaled2, scaled2.get_rect(center=button2_rect.center))

    # --- Инфа о параметрах игроков ---
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

    # --- Кнопки улучшений ---
    for i in range(4):
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

    # --- Подсказка для 2-го игрока ---
    hint2 = font_tiny.render("ПРОБЕЛ — клик   |   Z — купить улучшение", True, COLOR_P2)
    screen.blit(hint2, hint2.get_rect(center=(PLAYER2_X, 620)))

    # --- Всплывашки "+N" ---
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
        "Игрок 1: мышь  |  Игрок 2: ПРОБЕЛ + Z  |  ENTER — выход  |  DELETE — стереть прогресс",
        True, COLOR_GRAY
    )
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 30)))

    # ========================================================
    # ОКНО ПОДТВЕРЖДЕНИЯ СБРОСА (поверх всего)
    # ========================================================
    if confirm_reset:
        # Полупрозрачная затемняющая подложка
        overlay = ed.Surface((WIDTH, HEIGHT), ed.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Рамка окна
        box_w, box_h = 900, 340
        box = ed.Rect(WIDTH // 2 - box_w // 2, HEIGHT // 2 - box_h // 2, box_w, box_h)
        ed.draw.rect(screen, (40, 20, 30), box, border_radius=20)
        ed.draw.rect(screen, COLOR_RED, box, 4, border_radius=20)

        # Заголовок
        t1 = font_big.render("⚠️ СТЕРЕТЬ ПРОГРЕСС?", True, COLOR_RED)
        screen.blit(t1, t1.get_rect(center=(WIDTH // 2, box.y + 70)))

        # Пояснение
        t2 = font_mid.render(
            "Весь прогресс и файл save.json будут удалены!",
            True, (255, 220, 220)
        )
        screen.blit(t2, t2.get_rect(center=(WIDTH // 2, box.y + 150)))

        # Инструкция
        t3 = font_small.render(
            "Y / ENTER — подтвердить    |    N / ESC — отмена",
            True, COLOR_GOLD
        )
        screen.blit(t3, t3.get_rect(center=(WIDTH // 2, box.y + 230)))

        # Мигающее предупреждение снизу окна
        blink = (ed.time.get_ticks() // 400) % 2
        if blink:
            t4 = font_tiny.render(
                "Это действие необратимо!",
                True, (255, 120, 120)
            )
            screen.blit(t4, t4.get_rect(center=(WIDTH // 2, box.y + 290)))

    # --- Показать кадр ---
    ed.display.flip()

# ============================================================
# СОХРАНЕНИЕ ПРОГРЕССА ПРИ ВЫХОДЕ
# ============================================================
# Если открыто окно сброса и игрок жмёт закрыть окно — не сохраняем
# старый прогресс, но и не стираем. Просто сохраняем как есть.
save_game()

# ============================================================
# ЗАВЕРШЕНИЕ РАБОТЫ ПРОГРАММЫ
# ============================================================
ed.quit()
sys.exit()