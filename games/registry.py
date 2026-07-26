"""Game registry - auto-discovery and registration of mini-games."""

_REGISTRY = {}


def register_game(game_id, name_key, desc_key, create_func,
                   supports_local=True, supports_bot=True,
                   supports_network=True, network_protocol="tcp"):
    """Register a mini-game.

    Args:
        game_id: Unique string ID
        name_key: Localization key for name
        desc_key: Localization key for description
        create_func: Function(engine, mode, **kwargs) -> Scene
        supports_local: Can play on same PC
        supports_bot: Can play vs AI
        supports_network: Can play over LAN
        network_protocol: "tcp" or "udp"
    """
    _REGISTRY[game_id] = {
        "name_key": name_key,
        "desc_key": desc_key,
        "create_func": create_func,
        "supports_local": supports_local,
        "supports_bot": supports_bot,
        "supports_network": supports_network,
        "network_protocol": network_protocol,
    }


def get_registered_games():
    """Get all registered games."""
    return _REGISTRY.copy()


def create_game(game_id, engine, mode, **kwargs):
    """Create a game scene instance."""
    info = _REGISTRY.get(game_id)
    if info:
        return info["create_func"](engine, mode, **kwargs)
    return None