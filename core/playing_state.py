# =============================================================================
#  MORNIA — core/playing_state.py
#  État de jeu actif — instancie et pilote le Level courant.
#  Remplace le _PlaceholderState de GameState.PLAYING.
# =============================================================================

import pygame
from core.state_machine import State
from settings import GameState, BLACK


class PlayingState(State):
    """
    État actif quand le joueur est en train de jouer.
    Crée le Level, le met à jour et le dessine.
    """

    def __init__(self, game):
        super().__init__(owner=game)
        self.game   = game
        self._level = None

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def on_enter(self):
        """Crée le niveau au moment où on entre dans cet état."""
        from world.level import Level
        self._level       = Level(self.game)
        self.game.current_level = self._level
        self.game.player        = self._level.player

    def on_exit(self):
        self._level = None
        self.game.current_level = None
        self.game.player        = None

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------

    def handle_input(self, events):
        # Les inputs joueur sont gérés directement par InputComponent
        # On écoute juste F1 pour le debug et F3 pour le retour menu
        eh = self.game.event_handler
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1 and self._level:
                    self._level.toggle_debug()
                if event.key == pygame.K_F3:
                    self.game.fsm.change(GameState.MAIN_MENU)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float):
        if self._level:
            self._level.update(dt)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface):
        """Rendu pixel art sur la canvas."""
        if self._level:
            self._level.draw(surface)
        else:
            surface.fill(BLACK)

    def draw_ui(self, surface: pygame.Surface, offset_x, offset_y, scale):
        """HUD net sur la ui_surface."""
        if self._level:
            self._level.draw_ui(surface, offset_x, offset_y, scale)


# =============================================================================
#  PAUSED STATE
# =============================================================================
class PausedState(State):
    """
    Superpose un écran de pause par-dessus le niveau.
    Le niveau reste visible en arrière-plan (semi-transparent).
    """

    def __init__(self, game):
        super().__init__(owner=game)
        self.game    = game
        self._cursor = 0
        self._items  = ["Reprendre", "Options", "Menu Principal", "Quitter"]
        self._font   = None
        self._overlay= None

    def on_enter(self):
        from data.asset_loader import AssetLoader
        from settings import SCALE_FACTOR
        self._font    = AssetLoader.get_instance().default_font(10 * SCALE_FACTOR)
        self._cursor  = 0
        self._overlay = self._make_overlay()

    def _make_overlay(self):
        from settings import INTERNAL_WIDTH, INTERNAL_HEIGHT
        s = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 140))
        return s

    def handle_input(self, events):
        eh = self.game.event_handler
        if eh.pressed("cancel") or eh.pressed("pause"):
            self.game.resume()
            return
        if eh.pressed("move_up"):
            self._cursor = (self._cursor - 1) % len(self._items)
        elif eh.pressed("move_down"):
            self._cursor = (self._cursor + 1) % len(self._items)
        elif eh.pressed("confirm"):
            self._confirm()

    def _confirm(self):
        action = self._items[self._cursor]
        if action == "Reprendre":
            self.game.resume()
        elif action == "Menu Principal":
            self.game.fsm.change(GameState.MAIN_MENU)
        elif action == "Quitter":
            self.game.quit()

    def update(self, dt):
        pass

    def draw(self, surface: pygame.Surface):
        """Dessine le niveau en arrière-plan + overlay sombre."""
        # Redessine le level derrière
        if self.game.current_level:
            self.game.current_level.draw(surface)
        surface.blit(self._overlay, (0, 0))

    def draw_ui(self, surface: pygame.Surface, offset_x, offset_y, scale):
        from settings import INTERNAL_WIDTH, INTERNAL_HEIGHT, GOLD
        from data.asset_loader import AssetLoader

        def sx(x): return int(offset_x + x * scale)
        def sy(y): return int(offset_y + y * scale)

        # Titre PAUSE
        title = self._font.render("— PAUSE —", True, GOLD)
        surface.blit(title, title.get_rect(
            centerx=sx(INTERNAL_WIDTH // 2),
            centery=sy(INTERNAL_HEIGHT // 2 - 30)
        ))

        # Items
        for i, item in enumerate(self._items):
            color = GOLD if i == self._cursor else (140, 120, 90)
            txt   = self._font.render(item, True, color)
            surface.blit(txt, txt.get_rect(
                centerx=sx(INTERNAL_WIDTH // 2),
                centery=sy(INTERNAL_HEIGHT // 2 - 5 + i * 14)
            ))

            if i == self._cursor:
                cur = self._font.render(">", True, GOLD)
                surface.blit(cur, (
                    sx(INTERNAL_WIDTH // 2) - txt.get_width() // 2 - cur.get_width() - 4,
                    txt.get_rect(centery=sy(INTERNAL_HEIGHT // 2 - 5 + i * 14)).y
                ))


# =============================================================================
#  GAME OVER STATE
# =============================================================================
class GameOverState(State):
    """Ecran de game over avec options Réessayer / Menu."""

    def __init__(self, game):
        super().__init__(owner=game)
        self.game    = game
        self._timer  = 0
        self._cursor = 0
        self._items  = ["Réessayer", "Menu Principal"]
        self._font   = None
        self._ready  = False   # Attend 1s avant d'accepter les inputs

    def on_enter(self):
        from data.asset_loader import AssetLoader
        from settings import SCALE_FACTOR
        self._font   = AssetLoader.get_instance().default_font(10 * SCALE_FACTOR)
        self._timer  = 0
        self._ready  = False
        self._cursor = 0

    def handle_input(self, events):
        if not self._ready:
            return
        eh = self.game.event_handler
        if eh.pressed("move_up"):
            self._cursor = (self._cursor - 1) % len(self._items)
        elif eh.pressed("move_down"):
            self._cursor = (self._cursor + 1) % len(self._items)
        elif eh.pressed("confirm"):
            self._confirm()

    def _confirm(self):
        if self._items[self._cursor] == "Réessayer":
            self.game.fsm.change(GameState.PLAYING)
        else:
            self.game.fsm.change(GameState.MAIN_MENU)

    def update(self, dt):
        self._timer += dt
        if self._timer > 1.0:
            self._ready = True

    def draw(self, surface: pygame.Surface):
        surface.fill((5, 0, 0))

    def draw_ui(self, surface: pygame.Surface, offset_x, offset_y, scale):
        from settings import INTERNAL_WIDTH, INTERNAL_HEIGHT, DARK_RED
        import math

        def sx(x): return int(offset_x + x * scale)
        def sy(y): return int(offset_y + y * scale)

        alpha = min(255, int(self._timer * 200))

        title = self._font.render("VOUS ÊTES MORT", True, (180, 20, 20))
        title.set_alpha(alpha)
        surface.blit(title, title.get_rect(
            centerx=sx(INTERNAL_WIDTH  // 2),
            centery=sy(INTERNAL_HEIGHT // 2 - 25)
        ))

        if self._ready:
            for i, item in enumerate(self._items):
                color = (220, 180, 60) if i == self._cursor else (120, 90, 70)
                txt   = self._font.render(item, True, color)
                surface.blit(txt, txt.get_rect(
                    centerx=sx(INTERNAL_WIDTH  // 2),
                    centery=sy(INTERNAL_HEIGHT // 2 + i * 16)
                ))


# =============================================================================
#  HELPER — installe les vrais états de jeu
# =============================================================================
def install_playing_states(game):
    """
    Remplace les placeholders PLAYING, PAUSED, GAME_OVER.
    Appelé dans main.py après install_menus().
    """
    game.replace_state(GameState.PLAYING,  PlayingState(game))
    game.replace_state(GameState.PAUSED,   PausedState(game))
    game.replace_state(GameState.GAME_OVER,GameOverState(game))