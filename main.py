# =============================================================================
#  MORNIA — main.py
#  Point d'entrée unique du jeu. Ne contient aucune logique.
#  Lance simplement la classe Game et démarre la boucle principale.
# =============================================================================

from core.game           import Game
from ui.menu             import install_menus
from core.playing_state  import install_playing_states
from data.asset_loader   import AssetLoader


def main():
    game = Game()

    # Initialise le singleton AssetLoader
    AssetLoader.get_instance()

    # Installe les vrais états (menu + gameplay)
    install_menus(game)
    install_playing_states(game)

    game.run()


if __name__ == "__main__":
    main()