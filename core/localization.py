"""Localization system."""

_STRINGS = {
    # === General ===
    "app_title": {
        "en": "botyaragames",
        "ru": "botyaragames",
    },
    "back": {
        "en": "Back",
        "ru": "Назад",
    },
    "start": {
        "en": "Start",
        "ru": "Начать",
    },
    "cancel": {
        "en": "Cancel",
        "ru": "Отмена",
    },
    "ok": {
        "en": "OK",
        "ru": "ОК",
    },
    "yes": {
        "en": "Yes",
        "ru": "Да",
    },
    "no": {
        "en": "No",
        "ru": "Нет",
    },
    "error": {
        "en": "Error",
        "ru": "Ошибка",
    },
    "waiting": {
        "en": "Waiting...",
        "ru": "Ожидание...",
    },

    # === Language selection ===
    "choose_language": {
        "en": "Choose Language",
        "ru": "Выберите язык",
    },
    "english": {
        "en": "English",
        "ru": "English",
    },
    "russian": {
        "en": "Русский",
        "ru": "Русский",
    },

    # === Main menu ===
    "main_menu_title": {
        "en": "Mini Games",
        "ru": "Мини Игры",
    },
    "settings": {
        "en": "Settings",
        "ru": "Настройки",
    },
    "statistics": {
        "en": "Statistics",
        "ru": "Статистика",
    },
    "quit": {
        "en": "Quit",
        "ru": "Выход",
    },
    "no_games": {
        "en": "No games available",
        "ru": "Нет доступных игр",
    },

    # === Mode selection ===
    "select_mode": {
        "en": "Select Mode",
        "ru": "Выберите режим",
    },
    "mode_local": {
        "en": "🎮  Local (Same PC)",
        "ru": "🎮  Локально (Один ПК)",
    },
    "mode_bot": {
        "en": "🤖  vs Bot",
        "ru": "🤖  Против бота",
    },
    "mode_lan": {
        "en": "🌐  LAN Network",
        "ru": "🌐  По сети (LAN)",
    },

    # === Network ===
    "network_title": {
        "en": "Network Game",
        "ru": "Сетевая игра",
    },
    "create_server": {
        "en": "Create Server",
        "ru": "Создать сервер",
    },
    "join_server": {
        "en": "Join Server",
        "ru": "Подключиться",
    },
    "enter_ip": {
        "en": "Enter IP address:",
        "ru": "Введите IP адрес:",
    },
    "enter_port": {
        "en": "Port:",
        "ru": "Порт:",
    },
    "waiting_for_player": {
        "en": "Waiting for player...",
        "ru": "Ожидание игрока...",
    },
    "connecting": {
        "en": "Connecting...",
        "ru": "Подключение...",
    },
    "connected": {
        "en": "Connected!",
        "ru": "Подключено!",
    },
    "connection_failed": {
        "en": "Connection failed!",
        "ru": "Не удалось подключиться!",
    },
    "your_ip": {
        "en": "Your IP: {}",
        "ru": "Ваш IP: {}",
    },
    "protocol": {
        "en": "Protocol: {}",
        "ru": "Протокол: {}",
    },

    # === Network status ===
    "player_disconnected": {
        "en": "Player disconnected!",
        "ru": "Игрок отключился!",
    },
    "connection_lost": {
        "en": "Connection lost!",
        "ru": "Соединение потеряно!",
    },
    "reconnecting": {
        "en": "Reconnecting... ({}/{})",
        "ru": "Переподключение... ({}/{})",
    },
    "reconnect_failed": {
        "en": "Could not reconnect",
        "ru": "Не удалось переподключиться",
    },
    "reconnected": {
        "en": "Reconnected!",
        "ru": "Переподключено!",
    },
    "opponent_reconnecting": {
        "en": "Opponent is reconnecting...",
        "ru": "Противник переподключается...",
    },
    "timeout_warning": {
        "en": "Connection unstable ({:.0f}s)",
        "ru": "Соединение нестабильно ({:.0f}с)",
    },
    "ping": {
        "en": "Ping: {}ms",
        "ru": "Пинг: {}мс",
    },
    "return_to_menu": {
        "en": "Return to Menu",
        "ru": "Вернуться в меню",
    },
    "wait_reconnect": {
        "en": "Wait for Reconnect",
        "ru": "Ждать переподключения",
    },
    "network_error": {
        "en": "Network Error",
        "ru": "Ошибка сети",
    },
    "server_closed": {
        "en": "Server closed",
        "ru": "Сервер закрыт",
    },

    # === Settings ===
    "settings_title": {
        "en": "Settings",
        "ru": "Настройки",
    },
    "language_label": {
        "en": "Language",
        "ru": "Язык",
    },
    "resolution_label": {
        "en": "Resolution",
        "ru": "Разрешение",
    },
    "fullscreen_label": {
        "en": "Fullscreen",
        "ru": "Полный экран",
    },
    "particles_label": {
        "en": "Particles",
        "ru": "Частицы",
    },
    "apply": {
        "en": "Apply",
        "ru": "Применить",
    },
    "on": {
        "en": "ON",
        "ru": "ВКЛ",
    },
    "off": {
        "en": "OFF",
        "ru": "ВЫКЛ",
    },

    # === Stats ===
    "stats_title": {
        "en": "Statistics",
        "ru": "Статистика",
    },
    "wins": {
        "en": "Wins",
        "ru": "Победы",
    },
    "losses": {
        "en": "Losses",
        "ru": "Поражения",
    },
    "draws": {
        "en": "Draws",
        "ru": "Ничьи",
    },
    "total_games": {
        "en": "Total Games",
        "ru": "Всего игр",
    },
    "no_stats": {
        "en": "No statistics yet",
        "ru": "Статистики пока нет",
    },
    "reset_stats": {
        "en": "Reset Statistics",
        "ru": "Сбросить статистику",
    },

    # === Tic Tac Toe ===
    "tic_tac_toe": {
        "en": "Tic Tac Toe",
        "ru": "Крестики-Нолики",
    },
    "tic_tac_toe_desc": {
        "en": "Classic 3x3 board game",
        "ru": "Классическая игра 3×3",
    },
    "player_x_turn": {
        "en": "Player X's turn",
        "ru": "Ход игрока X",
    },
    "player_o_turn": {
        "en": "Player O's turn",
        "ru": "Ход игрока O",
    },
    "player_x_wins": {
        "en": "Player X wins!",
        "ru": "Игрок X победил!",
    },
    "player_o_wins": {
        "en": "Player O wins!",
        "ru": "Игрок O победил!",
    },
    "draw": {
        "en": "It's a draw!",
        "ru": "Ничья!",
    },
    "play_again": {
        "en": "Play Again",
        "ru": "Играть снова",
    },
    "your_turn": {
        "en": "Your turn",
        "ru": "Ваш ход",
    },
    "opponent_turn": {
        "en": "Opponent's turn",
        "ru": "Ход противника",
    },
    "bot_thinking": {
        "en": "Bot is thinking...",
        "ru": "Бот думает...",
    },
    "you_win": {
        "en": "You win!",
        "ru": "Вы победили!",
    },
    "you_lose": {
        "en": "You lose!",
        "ru": "Вы проиграли!",
    },
}

_current_lang = "en"


def set_language(lang):
    global _current_lang
    _current_lang = lang


def get_language():
    return _current_lang


def get_text(key, lang=None, *args):
    """Get localized text. Supports format args."""
    if lang is None:
        lang = _current_lang
    entry = _STRINGS.get(key, {})
    text = entry.get(lang, entry.get("en", f"[{key}]"))
    if args:
        try:
            text = text.format(*args)
        except (IndexError, KeyError):
            pass
    return text


def register_strings(new_strings):
    """Register additional localization strings (used by games)."""
    _STRINGS.update(new_strings)