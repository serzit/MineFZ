import time
from concurrent.futures import ThreadPoolExecutor
import cv2
import numpy as np
import pygetwindow as gw
import subprocess
import pyautogui
import keyboard  # Import the keyboard library
import threading  # Для многозадачности

# Параметры
warehouse_template_path = "warehouse.png"
player_cover_path = "player_covered.png"
player_template_path = 'player.png'  # Изображение игрока в бою
alt_icons = ["player_alt.png",
             "player_alt2.png",
             "player_alt3.png",
             "player_alt4.png",
             "player_alt5.png",
             "player_alt6.png",
             "player_alt7.png",
             "player_alt8.png",
             "player_alt9.png",
             "player_alt10.png",
             "player_alt11.png",
             "player_alt12.png",
             "player_alt13.png",
             "player_alt14.png",
             "player_alt15.png",
             "player_alt16.png",
             "player_alt17.png",
             "player_alt18.png",
             "player_black_corner.png",
             "player_fullBlack.png",
             "player_black_bottom.png",
             "player_black_left.png"]

icon_template_path = 'arrow_down.png'  # Изображение иконки игрока в шахте
alt_mine_icons = ["arrow_left.png", "arrow_right.png", "arrow_up.png"]
hex_template_path = 'empty_hex.png'  # Шаблон свободного гекса
ahk_scripts_path = r'C:\Bot\Core\HotKeys'  # Путь к AHK-скриптам

# Состояния
STATE_BATTLE = "В БОЮ"
STATE_MINE = "В ШАХТЕ"
STATE_CITY = "В ГОРОДЕ"
STATE_SYNC = "СИНХРОНИЗАЦИЯ"
current_state = STATE_MINE
stitch_summoned = False
MAX_X = 1200  # Максимальное значение X
MAX_Y = 1600   # Максимальное значение Y

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


def find_image_on_screen(
    screenshot_path,
    threshold=0.8,
    max_attempts=6,
    alt_template_paths=None,
    search_region=(0, 0, 1280, 1600)
):
    """
    Находит положение изображения в указанной области экрана.

    :param screenshot_path: Путь к основному шаблону
    :param threshold: Пороговое значение для совпадения
    :param max_attempts: Максимальное количество попыток поиска
    :param alt_template_paths: Список путей к альтернативным шаблонам (опционально)
    :param search_region: Координаты области поиска (x1, y1, x2, y2)
    :return: Координаты верхнего левого угла найденного изображения или None
    """

    def search_template(template_path, search_area, threshold):
        """Поиск изображения в переданной области поиска."""
        template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
        if template is None:
            raise ValueError(f"Шаблон не найден по пути: {template_path}")

        search_area_gray = cv2.cvtColor(search_area, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        result = cv2.matchTemplate(search_area_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        return max_val, max_loc

    def search_primary_attempts():
        """Основной цикл поиска по основному шаблону."""
        x1, y1, x2, y2 = search_region

        for attempt in range(max_attempts):
            print(f"Попытка {attempt + 1} поиска основного шаблона: {screenshot_path}")
            screenshot = pyautogui.screenshot()
            screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # Ограничиваем область поиска основной областью
            search_area = screenshot[y1:y2, x1:x2]

            max_val, max_loc = search_template(screenshot_path, search_area, threshold)
            print(f"Совпадение основного изображения: {max_val}")

            if max_val >= threshold:
                # Преобразуем координаты из локальной области в экранные координаты
                screen_loc = (max_loc[0] + x1, max_loc[1] + y1)
                print(f"Изображение найдено на координатах: {screen_loc}")
                return screen_loc

        print("Основное изображение не найдено после всех попыток.")
        return None

    def search_single_alternative():
        """Однократный поиск по альтернативным шаблонам."""
        x1, y1, x2, y2 = search_region

        for alt_path in alt_template_paths:
            print(f"Пробуем найти альтернативный шаблон: {alt_path}")
            screenshot = pyautogui.screenshot()
            screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # Ограничиваем область поиска для поиска альтернативного шаблона
            search_area = screenshot[y1:y2, x1:x2]
            match_val, match_loc = search_template(alt_path, search_area, threshold)
            print(f"Совпадение альтернативного изображения: {match_val}")

            if match_val >= threshold:
                screen_loc = (match_loc[0] + x1, match_loc[1] + y1)
                print(f"Альтернативное изображение найдено: {screen_loc}")
                return screen_loc

        print("Альтернативные шаблоны не сработали.")
        return None

    def search_deep_alternatives():
        """Углубленный поиск по всем альтернативным шаблонам."""
        x1, y1, x2, y2 = search_region
        best_match_val = -1
        best_match_loc = None

        for alt_path in alt_template_paths:
            print(f"Пробуем углубленный поиск по шаблону: {alt_path}")
            for attempt in range(3):  # Попытки повторного поиска
                print(f"Попытка {attempt + 1} для шаблона {alt_path}")
                screenshot = pyautogui.screenshot()
                screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

                search_area = screenshot[y1:y2, x1:x2]
                match_val, match_loc = search_template(alt_path, search_area, threshold)
                print(f"Совпадение альтернативного изображения: {match_val}")

                if match_val > best_match_val:
                    best_match_val = match_val
                    best_match_loc = match_loc

        if best_match_val >= threshold:
            screen_loc = (best_match_loc[0] + x1, best_match_loc[1] + y1)
            print(f"Углубленный поиск нашел изображение: {screen_loc}")
            return screen_loc

        print("Углубленный поиск не нашел изображение.")
        return None

    # 1. Попытка найти изображение основным методом
    location = search_primary_attempts()
    if location:
        return location

    # 2. Если не найдено, пробуем однократный альтернативный поиск
    if alt_template_paths:
        location = search_single_alternative()
        if location:
            return location

        # 3. Если и это не помогло, проводим углубленный поиск
        location = search_deep_alternatives()
        if location:
            return location

    # Если ничего не помогло
    print("Изображение не найдено ни одним из методов.")
    return None

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
    start_time = time.time()
    free_hex = check_hexes_around_player(player_pos, hex_template_path)
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Проверка гексов: {execution_time:.2f} секунд")
    print(f"Результат проверки гексов: {free_hex}")  # Лог результата проверки

    if free_hex is not None:
        # Проверяем, что координаты не выходят за допустимые пределы
        if free_hex[0] > MAX_X or free_hex[1] > MAX_Y:
            print(f"Гекс ({free_hex[0]}, {free_hex[1]}) выходит за пределы допустимых координат.")
            return  # Если координаты гекса выходят за пределы, прерываем выполнение

        print(f"Свободный гекс найден на координатах: {free_hex}")
        # Зажимаем CTRL, перемещаем мышку и кликаем
        run_ahk_script('ctrlDown')  # Зажимаем CTRL
        time.sleep(0.025)
        try:
            pyautogui.moveTo(free_hex[0], free_hex[1])  # Перемещаем курсор в свободный гекс
            run_ahk_script('clickLeft')  # Кликаем
            stitch_summoned = True  # Помечаем, что стич был вызван
        finally:
            run_ahk_script('ctrlUp')  # Отпускаем CTRL
    else:
        print("Свободных гексов не найдено. Стич не вызван.")


def is_hex_free(check_x, check_y, template_path, region_size=75):
    """Проверка, является ли гекс пустым, используя шаблон."""
    start_time = time.time()
    region_x1 = max(0, check_x - region_size)
    region_y1 = max(0, check_y - region_size)
    width = region_size * 2
    height = region_size * 2

    # Снимаем скриншот только нужного региона
    screenshot = pyautogui.screenshot(region=(region_x1, region_y1, width, height))
    screenshot_np = np.array(screenshot)

    # Преобразуем в оттенки серого
    screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)

    # Загружаем шаблон
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    # Сравниваем с шаблоном
    result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    print(f"Совпадение с шаблоном: {max_val}")

    end_time = time.time()
    print(f"Время выполнения: {end_time - start_time:.2f} секунд")
    return max_val


def is_hex_free(check_x, check_y, template, screenshot_gray, region_size=75):
    """Проверка, является ли гекс пустым, используя шаблон."""
    region_x1 = max(0, check_x - region_size)
    region_y1 = max(0, check_y - region_size)
    region_x2 = check_x + region_size
    region_y2 = check_y + region_size

    region = screenshot_gray[region_y1:region_y2, region_x1:region_x2]
    if region.size == 0:
        return -1  # Если регион пустой, возвращаем минимальное значение

    result = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val


def check_single_hex(args):
    """Функция для проверки одного гекса (для параллельной обработки)."""
    check_x, check_y, template, screenshot_gray = args
    return check_x, check_y, is_hex_free(check_x, check_y, template, screenshot_gray)


def check_hexes_around_player(player_pos, hex_template_path, early_stop_threshold=0.9):
    """Проверяем 6 гексов вокруг игрока и возвращаем тот, который имеет наибольшее совпадение."""
    x, y = player_pos
    x += 20
    y += 20

    # Снимаем один скриншот
    screenshot = pyautogui.screenshot()
    screenshot_np = np.array(screenshot)
    screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)

    # Загружаем шаблон один раз
    template = cv2.imread(hex_template_path, cv2.IMREAD_GRAYSCALE)

    # Смещения для гексов
    hex_offsets = [
        (30, -30),  # Правый-верхний гекс
        (-40, 0),   # Левый гекс
        (50, -5),   # Правый гекс
        (-25, 25),  # Левый-нижний гекс
    ]

    args = [(x + dx, y + dy, template, screenshot_gray) for dx, dy in hex_offsets]

    # Параллельная проверка гексов
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(check_single_hex, args))

    # Находим лучший результат
    best_match = -1
    best_coordinates = None
    for check_x, check_y, match_val in results:
        if match_val > best_match:
            best_match = match_val
            best_coordinates = (check_x, check_y)

    if best_coordinates:
        print(f"Лучший гекс: {best_coordinates} с совпадением {best_match}")
    else:
        print("Свободных гексов не найдено.")

    return best_coordinates


def handle_battle():
    """Обработка состояния 'В БОЮ'."""
    global current_state, stitch_summoned
    start_time = time.time()

    player_position = find_image_on_screen(
        screenshot_path=player_template_path,  # Основной шаблон
        threshold=0.82,  # Порог совпадения
        alt_template_paths=alt_icons,  # Альтернативные шаблоны
        search_region=(300,150,1350,950)
    )
    endTime_image = time.time()
    exe_time = endTime_image - start_time
    print(f"Поиск персонажа в бою: {exe_time:.2f} секунд")

    #run_ahk_script('d')
    #time.sleep(0.1)

    if player_position:
        run_ahk_script('skills')

        if not stitch_summoned:
            print("Вызов стича...")
            start_time = time.time()
            summon_around_player(player_position, hex_template_path)
            end_time = time.time()
            execution_time = end_time - start_time
            print(f"Вызов стича: {execution_time:.2f} секунд")
        else:
            print("Стич уже вызван, продолжаем бой.")

        if stitch_summoned:
            run_ahk_script('5')
            run_ahk_script('8d')
            """for _ in range(8):
                if stop_program:
                    break
                print("Нажимаем 'д' и 'enter'")
                time.sleep(0.001)
                run_ahk_script('d')
                run_ahk_script('enter')"""

        print("Бой завершен, возвращаемся в шахту.")

        current_state = STATE_MINE  # Переходим в шахту
        stitch_summoned = False  # Сбрасываем состояние для следующего боя

def handle_mine():
    """Обработка состояния 'В ШАХТЕ'."""
    global stop_program, current_state
    start_time = time.time()

    run_ahk_script('enter_3')

    icon_position = find_image_on_screen(
        icon_template_path,
        threshold=0.85,
        max_attempts=1,
        alt_template_paths=alt_mine_icons,
        search_region=(300, 350, 850, 850))
    end_time_image = time.time()
    exe_time = end_time_image - start_time
    print(f"Поиск в шахте: {exe_time:.2f} секунд")

    if icon_position:
        x, y = icon_position
        pyautogui.moveTo(x, y)
        run_ahk_script('clickLeft')
        current_state = STATE_BATTLE
        print("Перемещаемся по шахте")
    else:
        current_state = STATE_SYNC

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Передвижение по шахте: {execution_time:.2f} секунд")

def handle_city():
    global current_state, stop_program

    print('Состояние город')
    run_ahk_script('enter_3')

    pyautogui.moveTo(2165, 200)
    run_ahk_script('clickLeft')

    time.sleep(8)
    if stop_program:
        return
    pyautogui.moveTo(2237, 279)
    run_ahk_script('clickLeft')

    time.sleep(8)
    if stop_program:
        return
    run_ahk_script('4')
    run_ahk_script('enter')
    run_ahk_script('enter')
    time.sleep(1)

    run_ahk_script('clickLeft')
    time.sleep(17)
    if stop_program:
        return

    run_ahk_script('4')
    run_ahk_script('enter')
    run_ahk_script('enter')
    run_ahk_script('clickLeft')
    pyautogui.moveTo(893, 361)
    time.sleep(0.5)
    run_ahk_script('clickLeft')

    current_state = STATE_MINE
    print('Дошли до шахты')

def handle_sync():
    global current_state

    print('Попытка синхронизации состояний')
    run_ahk_script('8d')

    warehouse_position = find_image_on_screen(warehouse_template_path, threshold=0.85, max_attempts=5)

    if warehouse_position:
        current_state = STATE_CITY
        return

    icon_position = find_image_on_screen(icon_template_path,
        threshold=0.85,
        max_attempts=1,
        alt_template_paths=alt_mine_icons,
        search_region=(300, 350, 850, 850))

    if icon_position:
        current_state = STATE_MINE
        return

    player_position = find_image_on_screen(
        screenshot_path=player_template_path,  # Основной шаблон
        threshold=0.82,  # Порог совпадения
        alt_template_paths=alt_icons,  # Альтернативные шаблоны
        search_region=(300,150,1350,950)
    )

    if player_position:
        current_state = STATE_BATTLE
        return


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
    STATE_MINE: handle_mine,
    STATE_BATTLE: handle_battle,
    STATE_CITY: handle_city,
    STATE_SYNC: handle_sync
}

while not stop_program:
    # Проверяем, если нужно остановить программу
    if stop_program:
        break  # Завершаем основной цикл, если установлен флаг остановки

    if not activate_game_window():
        continue

    # Замеряем время начала
    start_time = time.time()

    # Выполняем текущее состояние
    states[current_state]()

    # Замеряем время после выполнения состояния
    end_time = time.time()

    # Рассчитываем, сколько времени было затрачено
    elapsed_time = end_time - start_time
    print(f"Текущий статус: {current_state}, Время выполнения: {elapsed_time:.4f} сек")

print("Скрипт завершен.")
