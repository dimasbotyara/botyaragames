"""Pong - registration."""

from games.registry import register_game
from core.localization import register_strings

# Register localization strings for Pong
register_strings({
    "pong": {
        "en": "Pong",
        "ru": "Понг",
    },
    "pong_desc": {
        "en": "Classic paddle ball game",
        "ru": "Классический пинг-понг",
    },
    "pong_score": {
        "en": "{}  :  {}",
        "ru": "{}  :  {}",
    },
    "pong_player1": {
        "en": "Player 1",
        "ru": "Игрок 1",
    },
    "pong_player2": {
        "en": "Player 2",
        "ru": "Игрок 2",
    },
    "pong_bot": {
        "en": "Bot",
        "ru": "Бот",
    },
    "pong_controls_left": {
        "en": "W / S",
        "ru": "W / S",
    },
    "pong_controls_right": {
        "en": "↑ / ↓",
        "ru": "↑ / ↓",
    },
    "pong_wins": {
        "en": "{} wins!",
        "ru": "{} победил!",
    },
    "pong_first_to": {
        "en": "First to {} points",
        "ru": "До {} очков",
    },
    "pong_get_ready": {
        "en": "Get Ready!",
        "ru": "Приготовьтесь!",
    },
    "pong_go": {
        "en": "GO!",
        "ru": "ПОЕХАЛИ!",
    },
    "pong_round": {
        "en": "Round {}",
        "ru": "Раунд {}",
    },
    "pong_speed": {
        "en": "Speed: {:.0f}%",
        "ru": "Скорость: {:.0f}%",
    },
    "pong_difficulty": {
        "en": "Difficulty",
        "ru": "Сложность",
    },
    "pong_easy": {
        "en": "🟢  Easy",
        "ru": "🟢  Легко",
    },
    "pong_medium": {
        "en": "🟡  Medium",
        "ru": "🟡  Средне",
    },
    "pong_hard": {
        "en": "🔴  Hard",
        "ru": "🔴  Сложно",
    },
    "pong_paused": {
        "en": "PAUSED",
        "ru": "ПАУЗА",
    },
    "pong_press_space": {
        "en": "Press SPACE to start",
        "ru": "Нажмите ПРОБЕЛ для старта",
    },
    "pong_press_esc": {
        "en": "ESC - pause",
        "ru": "ESC - пауза",
    },
})


def _create(engine, mode, **kwargs):
    if mode == "bot":
        from games.pong.difficulty_select import PongDifficultySelect
        return PongDifficultySelect(engine, **kwargs)
    from games.pong.game import PongGame
    return PongGame(engine, mode, **kwargs)


register_game(
    game_id="pong",
    name_key="pong",
    desc_key="pong_desc",
    create_func=_create,
    supports_local=True,
    supports_bot=True,
    supports_network=True,
    network_protocol="udp",
)