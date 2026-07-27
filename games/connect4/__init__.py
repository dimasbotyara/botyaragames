"""Connect Four - registration."""

from games.registry import register_game
from core.localization import register_strings

register_strings({
    "connect4": {
        "en": "Connect Four",
        "ru": "Четыре в ряд",
    },
    "connect4_desc": {
        "en": "Drop discs, connect 4 to win!",
        "ru": "Бросай фишки, собери 4 в ряд!",
    },
    "connect4_p1_turn": {
        "en": "🔴 Red's turn",
        "ru": "🔴 Ход красного",
    },
    "connect4_p2_turn": {
        "en": "🟡 Yellow's turn",
        "ru": "🟡 Ход жёлтого",
    },
    "connect4_p1_wins": {
        "en": "🔴 Red wins!",
        "ru": "🔴 Красный победил!",
    },
    "connect4_p2_wins": {
        "en": "🟡 Yellow wins!",
        "ru": "🟡 Жёлтый победил!",
    },
    "connect4_draw": {
        "en": "It's a draw!",
        "ru": "Ничья!",
    },
    "connect4_column_full": {
        "en": "Column is full!",
        "ru": "Столбец заполнен!",
    },
    "connect4_your_color": {
        "en": "You are: {}",
        "ru": "Вы играете: {}",
    },
    "connect4_red": {
        "en": "Red",
        "ru": "Красный",
    },
    "connect4_yellow": {
        "en": "Yellow",
        "ru": "Жёлтый",
    },
    "connect4_difficulty": {
        "en": "Difficulty",
        "ru": "Сложность",
    },
    "connect4_easy": {
        "en": "🟢  Easy",
        "ru": "🟢  Легко",
    },
    "connect4_medium": {
        "en": "🟡  Medium",
        "ru": "🟡  Средне",
    },
    "connect4_hard": {
        "en": "🔴  Hard",
        "ru": "🔴  Сложно",
    },
})


def _create(engine, mode, **kwargs):
    if mode == "bot":
        from games.connect4.difficulty_select import Connect4DifficultySelect
        return Connect4DifficultySelect(engine, **kwargs)
    from games.connect4.game import Connect4Game
    return Connect4Game(engine, mode, **kwargs)


register_game(
    game_id="connect4",
    name_key="connect4",
    desc_key="connect4_desc",
    create_func=_create,
    supports_local=True,
    supports_bot=True,
    supports_network=True,
    network_protocol="tcp",
)
