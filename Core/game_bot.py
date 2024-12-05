import time
import cv2
import numpy as np
import pygetwindow as gw
import subprocess
import pyautogui
import keyboard  # Import the keyboard library
import threading  # Для многозадачности

# Параметры
player_template_path = 'player.png'  # Изображение игрока в бою
icon_template_path = 'player_icon.png'  # Изображение иконки игрока в шахте
hex_template_path = 'empty_hex.png'  # Шаблон свободного гекса
click_offset = -50  # Начальное смещение для клика (левее)
ahk_scripts_path = r'C:\Bot\Core\HotKeys'  # Путь к AHK-скриптам

# Состояния
STATE_BATTLE = "В БОЮ"
STATE_MINE = "В ШАХТЕ"
current_state = STATE_MINE
stitch_summoned = False

# Флаг для остановки программы
stop_program = False
game_window_found = False  # Флаг, указывающий, найдено ли окно игры

# Проверка наличия шаблонов
for template_path in [player_template_path, icon_template_path, hex_template_path]:
    if not cv2.haveImageReader(template_path):
        raise FileNotFoundError(f"Шаблон не найден: {template_path}")

# Функция для запуска AHK скрипта
def run_ahk_script(key):
    ahk_script_path = f"{ahk_scripts_path}\\{key}.ahk"
    try:
        subprocess.run(ahk_script_path, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при запуске {key}.ahk: {e}")
        return False

def find_image_on_screen(template_path, threshold=0.6):
    """Находит положение изображения на экране."""
    screenshot = pyautogui.screenshot()
    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    # Загружаем шаблон
    template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if template is None:
        raise ValueError(f"Шаблон не найден по пути: {template_path}")

    # Приводим шаблон и скриншот к черно-белому формату
    screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    # Сравниваем изображения
    result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        return max_loc  # Верхний левый угол найденного изображения
    return None
    
def click_relative_to_icon(icon_pos, offset_x):
    """Кликает относительно найденной иконки."""
    if icon_pos:
        x, y = icon_pos
        pyautogui.moveTo(x + offset_x, y + 10)  # Передвигаем курсор
        run_ahk_script('clickLeft')  # Кликаем через AHK
        return True
    return False

def activate_game_window():
    """Активирует окно игры с названием 'TimeZero' только один раз."""
    global game_window_found
    if game_window_found:
        return True  # Если окно уже найдено, просто активируем его

    windows = gw.getWindowsWithTitle('TimeZero')
    if windows:
        game_window = windows[0]
        game_window.activate()
        print(f"Окно '{game_window.title}' активировано.")
        game_window_found = True  # Помечаем, что окно найдено
        return True
    else:
        print("Окно с названием 'TimeZero' не найдено.")
        return False

def summon_around_player(player_pos, hex_template_path):
    """
    Вызывает суммона вокруг игрока. Если найден свободный гекс, зажимается CTRL, курсор перемещается
    в точку свободного гекса, происходит клик, и CTRL отпускается.
    """
    global stitch_summoned  # Используем глобальную переменную
    if stitch_summoned:
        print("Стич уже вызван.")
        return  # Если стич уже вызван, ничего не делаем

    # Проверяем гексы вокруг игрока
    free_hex = check_hexes_around_player(player_pos, hex_template_path)
    print(f"Результат проверки гексов: {free_hex}")  # Лог результата проверки

    if free_hex is not None:
        print(f"Свободный гекс найден на координатах: {free_hex}")
        # Зажимаем CTRL, перемещаем мышку и кликаем
        run_ahk_script('ctrlDown')  # Зажимаем CTRL
        try:
            pyautogui.moveTo(free_hex[0], free_hex[1])  # Перемещаем курсор в свободный гекс
            run_ahk_script('clickLeft')  # Кликаем
            stitch_summoned = True  # Помечаем, что стич был вызван
        finally:
            run_ahk_script('ctrlUp')  # Отпускаем CTRL
    else:
        print("Свободных гексов не найдено. Стич не вызван.")


def is_hex_free(check_x, check_y, template_path, region_size=50):
    """Проверка, является ли гекс пустым, используя шаблон."""
    # Снимаем скриншот и преобразуем в numpy массив
    screenshot = pyautogui.screenshot()
    screenshot_np = np.array(screenshot)
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)  # Загружаем шаблон

    # Преобразуем скриншот в оттенки серого
    screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)

    # Определяем регион вокруг координат
    region_x1, region_y1 = max(0, check_x - region_size), max(0, check_y - region_size)
    region_x2, region_y2 = check_x + region_size, check_y + region_size

    # Проверяем границы изображения
    region = screenshot_gray[region_y1:region_y2, region_x1:region_x2]
    if region.shape[0] == 0 or region.shape[1] == 0:
        print(f"Область ({region_x1}, {region_y1}, {region_x2}, {region_y2}) вне экрана.")
        return False

    # Сравниваем с шаблоном
    result = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    print(f"Совпадение с шаблоном для региона ({region_x1}, {region_y1}, {region_x2}, {region_y2}): {max_val}")
    return max_val >= 0.45  # Совпадение более 45% означает, что гекс пустой


def check_hexes_around_player(player_pos, hex_template_path):
    """Проверяем 6 гексов вокруг игрока на пустоту."""
    x, y = player_pos
    x += 25  # Сдвигаем центр координат на игрока
    y += 25

    print(f"Координаты игрока: ({x}, {y})")  # Выводим координаты игрока

    # Смещения для 6 гексов вокруг
    hex_offsets = [
        (-50, 0),    # Левый гекс
        (50, 0),     # Правый гекс
        (25, 25),    # Правый-нижний гекс
        (-25, 25),   # Левый-нижний гекс
        (25, -25),   # Правый-верхний гекс
        (-25, -25),  # Левый-верхний гекс
    ]

    for counter, (dx, dy) in enumerate(hex_offsets, start=1):
        check_x, check_y = x + dx, y + dy
        print(f"Проверка {counter} на гекс с координатами: ({check_x}, {check_y})")

        # Проверяем, пустой ли гекс
        if is_hex_free(check_x, check_y, hex_template_path):
            print(f"Пустой гекс найден на координатах: ({check_x}, {check_y})")
            return (check_x, check_y)  # Возвращаем координаты первого найденного пустого гекса

    print("Свободных гексов не найдено.")
    return None  # Если не нашли пустой гекс



def handle_battle():
    """Обработка состояния 'В БОЮ'."""
    global current_state, stitch_summoned
    player_position = find_image_on_screen(player_template_path)
    
    if player_position:
        run_ahk_script('1')
        time.sleep(0.05)
        run_ahk_script('a')
        time.sleep(0.05)
        run_ahk_script('2')
        time.sleep(0.05)
        run_ahk_script('a')
        time.sleep(0.05)
        run_ahk_script('3')
       
        if not stitch_summoned:
            print("Вызов стича...")
            summon_around_player(player_position, hex_template_path)
        else:
            print("Стич уже вызван, продолжаем бой.")

        print("Бой завершен, возвращаемся в шахту.")
        stitch_summoned = False  # Сбрасываем состояние для следующего боя
        current_state = STATE_MINE  # Переходим в шахту

def handle_mine():
    """Обработка состояния 'В ШАХТЕ'."""
    global click_offset, current_state
    
    time.sleep(0.2)
    
    for _ in range(3):
        run_ahk_script('enter')
        
    icon_position = find_image_on_screen(icon_template_path)
    if icon_position:
        click_relative_to_icon(icon_position, click_offset)
        click_offset = -50 if click_offset > 0 else 100  # Чередование направлений
        print("Перемещаемся по шахте")
    else:
        print("Иконка игрока в шахте не найдена.")
        current_state = STATE_BATTLE  # Переходим к поиску боя

# Функция для отслеживания нажатия клавиши 'S'
def listen_for_stop():
    global stop_program
    while True:
        if keyboard.is_pressed('s'):  # Если нажата клавиша 'S'
            print("Программа остановлена.")
            stop_program = True  # Устанавливаем флаг остановки
            break  # Выход из потока

# Запуск потока для отслеживания клавиши
stop_thread = threading.Thread(target=listen_for_stop)
stop_thread.daemon = True  # Устанавливаем поток как фоновый
stop_thread.start()

# Основной цикл
states = {
    STATE_BATTLE: handle_battle,
    STATE_MINE: handle_mine,
}

while not stop_program:
    # Проверяем, если нужно остановить программу
    if stop_program:
        break  # Завершаем основной цикл, если установлен флаг остановки

    if not activate_game_window():
        continue

    states[current_state]()
    time.sleep(1)  # Задержка перед следующей проверкой

print("Скрипт завершен.")
