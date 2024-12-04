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
for template_path in [player_template_path, icon_template_path]:
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

def find_image_on_screen(template_path, threshold=0.8):
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

def summon_around_player(player_pos):
    """Вызов суммона вокруг игрока с зажатым CTRL (кликаем только один раз)."""
    global stitch_summoned  # Убедимся, что используем глобальную переменную
    if stitch_summoned:
        return  # Если стич уже вызван, не делаем ничего

    x, y = player_pos
    radius = 25  # Радиус области вокруг игрока

    run_ahk_script('ctrlDown')  # Зажимаем CTRL
    try:
        for dx in range(-radius, radius + 1, 20):
            for dy in range(-radius, radius + 1, 20):
                if dx**2 + dy**2 <= radius**2:
                    pyautogui.moveTo(x + dx, y + dy)
                    run_ahk_script('clickLeft')  # Кликаем один раз
                    print("Вызов стича")
                    stitch_summoned = True  # Помечаем, что стич был вызван
                    time.sleep(0.2)
                    return  # Выход из функции после первого клика, чтобы не кликать снова
    finally:
        run_ahk_script('ctrlUp')  # Отпускаем CTRL


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
            summon_around_player(player_position)  # Вызываем стича
        else:
            print("Стич уже вызван, продолжаем бой.")

        # Если стич уже вызван, начинаем цикл атак
        if stitch_summoned:
            for _ in range(20):
                print("Нажимаем 'д' и 'enter'")
                time.sleep(0.3)
                run_ahk_script('d')
                run_ahk_script('enter')

        print("Бой завершен, возвращаемся в шахту.")
        stitch_summoned = False  # Сбрасываем состояние для следующего боя
        current_state = STATE_MINE  # Переходим в шахту


def handle_mine():
    """Обработка состояния 'В ШАХТЕ'."""
    global click_offset, current_state
    time.sleep(0.2)
    icon_position = find_image_on_screen(icon_template_path)
    for _ in range(3):
         run_ahk_script('enter')
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
        time.sleep(2)
        continue

    states[current_state]()
    time.sleep(1)  # Задержка перед следующей проверкой

print("Скрипт завершен.")
