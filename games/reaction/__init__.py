"""Reaction Game - registration."""

from games.registry import register_game
from core.localization import register_strings

register_strings({
    "reaction": {
        "en": "Reaction Duel",
        "ru": "Дуэль Реакции",
    },
    "reaction_desc": {
        "en": "Test your reflexes! Don't fall for fakes",
        "ru": "Проверь рефлексы! Не попадись на обманку",
    },
    "reaction_wait": {
        "en": "Wait for GREEN...",
        "ru": "Ждите ЗЕЛЁНЫЙ...",
    },
    "reaction_now": {
        "en": "NOW!!!",
        "ru": "СЕЙЧАС!!!",
    },
    "reaction_too_early": {
        "en": "Too early! -1 point",
        "ru": "Рано! -1 очко",
    },
    "reaction_fake": {
        "en": "FAKE! That was {}!",
        "ru": "ОБМАНКА! Это был {}!",
    },
    "reaction_p1_wins_round": {
        "en": "Player 1 wins! {:.0f}ms",
        "ru": "Игрок 1 выиграл! {:.0f}мс",
    },
    "reaction_p2_wins_round": {
        "en": "Player 2 wins! {:.0f}ms",
        "ru": "Игрок 2 выиграл! {:.0f}мс",
    },
    "reaction_bot_wins_round": {
        "en": "Bot wins! {:.0f}ms",
        "ru": "Бот выиграл! {:.0f}мс",
    },
    "reaction_you_wins_round": {
        "en": "You win! {:.0f}ms",
        "ru": "Вы выиграли! {:.0f}мс",
    },
    "reaction_p1_controls": {
        "en": "Player 1: SPACE",
        "ru": "Игрок 1: ПРОБЕЛ",
    },
    "reaction_p2_controls": {
        "en": "Player 2: ENTER",
        "ru": "Игрок 2: ENTER",
    },
    "reaction_first_to": {
        "en": "First to {} wins",
        "ru": "До {} побед",
    },
    "reaction_wins": {
        "en": "{} wins the duel!",
        "ru": "{} выигрывает дуэль!",
    },
    "reaction_your_time": {
        "en": "Your best: {:.0f}ms",
        "ru": "Ваш лучший: {:.0f}мс",
    },
    "reaction_avg_time": {
        "en": "Average: {:.0f}ms",
        "ru": "Среднее: {:.0f}мс",
    },
    "reaction_round": {
        "en": "Round {}",
        "ru": "Раунд {}",
    },
    "reaction_get_ready": {
        "en": "Get Ready...",
        "ru": "Приготовьтесь...",
    },
    "reaction_both_early": {
        "en": "Both too early!",
        "ru": "Оба поторопились!",
    },
    "reaction_color_red": {
        "en": "red",
        "ru": "красный",
    },
    "reaction_color_blue": {
        "en": "blue",
        "ru": "синий",
    },
    "reaction_color_yellow": {
        "en": "yellow",
        "ru": "жёлтый",
    },
    "reaction_color_purple": {
        "en": "purple",
        "ru": "фиолетовый",
    },
    "reaction_next_round": {
        "en": "Next round in {:.0f}s...",
        "ru": "Следующий раунд через {:.0f}с...",
    },
    "reaction_penalty": {
        "en": "{} gets a penalty!",
        "ru": "{} получает штраф!",
    },
})


def _create(engine, mode, **kwargs):
    from games.reaction.game import ReactionGame
    return ReactionGame(engine, mode, **kwargs)


register_game(
    game_id="reaction",
    name_key="reaction",
    desc_key="reaction_desc",
    create_func=_create,
    supports_local=True,
    supports_bot=True,
    supports_network=True,
    network_protocol="udp",
)
