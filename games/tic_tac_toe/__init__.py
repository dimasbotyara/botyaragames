"""Tic Tac Toe - registration."""

from games.registry import register_game


def _create(engine, mode, **kwargs):
    from games.tic_tac_toe.game import TicTacToeGame
    return TicTacToeGame(engine, mode, **kwargs)


register_game(
    game_id="tic_tac_toe",
    name_key="tic_tac_toe",
    desc_key="tic_tac_toe_desc",
    create_func=_create,
    supports_local=True,
    supports_bot=True,
    supports_network=True,
    network_protocol="tcp",
)