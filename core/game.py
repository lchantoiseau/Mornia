# =============================================================================
#  MORNIA — core/game.py
#  Classe principale du jeu.
#  Gère : la fenêtre pygame, la boucle principale, le delta time,
#         la FSM globale (menus ↔ jeu ↔ pause...) et le rendu upscalé.
# =============================================================================

import sys
import pygame

from settings import (
    WINDOW_TITLE, SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    INTERNAL_WIDTH, INTERNAL_HEIGHT, SCALE_FACTOR,
    BLACK, GameState
)
from core.state_machine  import StateMachine, State
from core.event_handler  import EventHandler


# =============================================================================
#  ETATS GLOBAUX DU JEU
#  Chaque état correspond à un "écran" ou "mode" du jeu.
#  Ils sont définis ici en classes internes légères ; les états complexes
#  (MainMenuState, PlayingState...) auront leurs propres fichiers plus tard.
# =============================================================================

class _BaseGameState(State):
    """
    Classe de base pour les états globaux du jeu.
    Hérite de State (state_machine.py) et donne accès à self.game.
    """

    def __init__(self, game):
        super().__init__(owner=game)
        self.game = game


class _LoadingState(_BaseGameState):
    """
    État de chargement affiché brièvement au lancement.
    Sera remplacé par un vrai écran de chargement avec barre de progression.
    """
    def on_enter(self):
        self._timer = 0

    def update(self, dt):
        self._timer += dt
        # Après 0.5s passe automatiquement au menu principal
        if self._timer >= 0.5:
            self.game.fsm.change(GameState.MAIN_MENU)

    def draw(self, surface):
        surface.fill(BLACK)


class _PlaceholderState(_BaseGameState):
    """
    État temporaire utilisé pour PLAYING, PAUSED, GAME_OVER
    tant que leurs vrais modules ne sont pas encore codés.
    Affiche juste un message centré.
    """
    def __init__(self, game, label: str, color):
        super().__init__(game)
        self._label = label
        self._color = color

    def handle_input(self, events):
        eh = self.game.event_handler
        if eh.pressed("pause") or eh.pressed("cancel"):
            # Retour au menu depuis n'importe quel placeholder
            self.game.fsm.change(GameState.MAIN_MENU)

    def draw(self, surface):
        surface.fill(BLACK)
        font = pygame.font.SysFont(None, 16)
        text = font.render(self._label, True, self._color)
        rect = text.get_rect(center=(INTERNAL_WIDTH // 2, INTERNAL_HEIGHT // 2))
        surface.blit(text, rect)

        hint = font.render("ESC → Menu", True, (100, 100, 100))
        surface.blit(hint, (4, INTERNAL_HEIGHT - 12))


# =============================================================================
#  CLASSE GAME
# =============================================================================

class Game:
    """
    Point central du jeu. Instanciée une seule fois dans main.py.

    Responsabilités :
      - Initialiser pygame et créer la fenêtre
      - Maintenir la boucle principale (events → update → draw)
      - Gérer le delta time et le framerate
      - Exposer les services globaux (event_handler, asset_loader,
        sound_manager, save_manager) aux états et entités
      - Upscaler la surface interne (pixel art) vers la fenêtre réelle
    """

    def __init__(self):
        # ------------------------------------------------------------------
        # Initialisation pygame
        # ------------------------------------------------------------------
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_caption(WINDOW_TITLE)

        # Fenêtre réelle (affichée à l'écran)
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.RESIZABLE
        )

        # Surface interne basse résolution (pixel art rendu ici)
        self.canvas = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))

        # Surface UI pleine résolution (texte net, HUD, menus)
        # Transparente — posée par-dessus le canvas upscalé
        self.ui_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        # Horloge
        self.clock  = pygame.time.Clock()
        self.dt     = 0.0      # Delta time en secondes
        self.running = True

        # ------------------------------------------------------------------
        # Services globaux
        # Instanciés ici pour être accessibles depuis n'importe quel état.
        # Les vrais modules seront branchés au fur et à mesure.
        # ------------------------------------------------------------------
        from data.asset_loader import AssetLoader
        self.event_handler  = EventHandler()
        self.asset_loader   = AssetLoader.get_instance()
        self.sound_manager  = None   # data/sound_manager.py (à venir)
        self.save_manager   = None   # data/save_manager.py  (à venir)

        # Données de session courante
        self.current_level  = None   # Level actif
        self.player         = None   # Instance Player active
        self.active_slot    = None   # Slot de sauvegarde sélectionné (1-3)

        # ------------------------------------------------------------------
        # Machine à états globale
        # ------------------------------------------------------------------
        self.fsm = StateMachine(self)
        self._register_states()
        self.fsm.change(GameState.LOADING)

    # ------------------------------------------------------------------
    # Enregistrement des états globaux
    # ------------------------------------------------------------------

    def _register_states(self):
        """
        Enregistre tous les états globaux dans la FSM.
        Quand un état aura son propre module (MainMenuState, PlayingState...),
        il suffira de remplacer le placeholder ici sans toucher au reste.
        """
        from settings import GOLD, WHITE

        self.fsm.add_states({
            GameState.LOADING  : _LoadingState(self),

            # Placeholders provisoires
            GameState.MAIN_MENU: _PlaceholderState(self, "MAIN MENU",  GOLD),
            GameState.PLAYING  : _PlaceholderState(self, "PLAYING",    WHITE),
            GameState.PAUSED   : _PlaceholderState(self, "PAUSED",     GOLD),
            GameState.GAME_OVER: _PlaceholderState(self, "GAME OVER",  (180, 30, 30)),
            GameState.CUTSCENE : _PlaceholderState(self, "CUTSCENE",   WHITE),
        })

    def replace_state(self, name: str, state):
        """
        Remplace un état placeholder par son implémentation réelle.
        Appelé depuis les modules au moment de leur initialisation.

        Exemple dans menu.py :
            game.replace_state(GameState.MAIN_MENU, MainMenuState(game))
        """
        self.fsm.add_state(name, state)

    # ------------------------------------------------------------------
    # Boucle principale
    # ------------------------------------------------------------------

    def run(self):
        """Lance la boucle principale. Bloque jusqu'à la fermeture du jeu."""
        while self.running:
            self._tick()
        self._shutdown()

    def _tick(self):
        """Une frame complète : events → update → draw."""
        # Delta time en secondes, plafonné pour éviter les gros sauts
        raw_dt      = self.clock.tick(FPS) / 1000.0
        self.dt     = min(raw_dt, 0.05)   # Max 50ms (= 20 FPS minimum)

        self._handle_events()
        self._update()
        self._draw()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _handle_events(self):
        self.event_handler.update()

        if self.event_handler.quit_requested:
            self.running = False
            return

        self.fsm.handle_input(self.event_handler.raw_events)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update(self):
        self.fsm.update(self.dt)

    # ------------------------------------------------------------------
    # Draw — rendu upscalé
    # ------------------------------------------------------------------

    def _draw(self):
        # 1. Pixel art — dessiné sur la canvas basse résolution
        self.fsm.draw(self.canvas)

        # 2. Upscale nearest-neighbor (pixel art net)
        win_w, win_h = self.screen.get_size()
        scale    = min(win_w / INTERNAL_WIDTH, win_h / INTERNAL_HEIGHT)
        scaled_w = int(INTERNAL_WIDTH  * scale)
        scaled_h = int(INTERNAL_HEIGHT * scale)
        offset_x = (win_w - scaled_w) // 2
        offset_y = (win_h - scaled_h) // 2

        scaled_canvas = pygame.transform.scale(self.canvas, (scaled_w, scaled_h))
        self.screen.fill(BLACK)
        self.screen.blit(scaled_canvas, (offset_x, offset_y))

        # 3. UI haute résolution — texte net par-dessus le pixel art
        #    Les états qui ont du texte implémentent draw_ui(surface, offset, scale)
        self.ui_surface.fill((0, 0, 0, 0))   # Reset transparent
        if hasattr(self.fsm._current, "draw_ui"):
            self.fsm._current.draw_ui(self.ui_surface, offset_x, offset_y, scale)
        self.screen.blit(self.ui_surface, (0, 0))

        pygame.display.flip()

    # ------------------------------------------------------------------
    # Transitions de haut niveau (appelées depuis les états)
    # ------------------------------------------------------------------

    def start_new_game(self, slot: int = 1):
        """Démarre une nouvelle partie sur le slot donné."""
        self.active_slot = slot
        # TODO : initialiser Player, Level, SaveManager
        self.fsm.change(GameState.PLAYING)

    def load_game(self, slot: int):
        """Charge une partie existante depuis un slot."""
        self.active_slot = slot
        # TODO : charger via SaveManager
        self.fsm.change(GameState.PLAYING)

    def pause(self):
        """Met le jeu en pause (si on est en train de jouer)."""
        if self.fsm.is_in(GameState.PLAYING):
            self.fsm.change(GameState.PAUSED)

    def resume(self):
        """Reprend le jeu depuis la pause."""
        if self.fsm.is_in(GameState.PAUSED):
            self.fsm.change(GameState.PLAYING)

    def game_over(self):
        """Déclenche l'écran de game over."""
        self.fsm.change(GameState.GAME_OVER)

    def quit(self):
        """Ferme proprement le jeu."""
        self.running = False

    # ------------------------------------------------------------------
    # Arrêt propre
    # ------------------------------------------------------------------

    def _shutdown(self):
        """Appelé une seule fois à la fermeture."""
        # TODO : sauvegarder les options, flusher les sauvegardes en cours...
        pygame.mixer.quit()
        pygame.quit()
        sys.exit()

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def get_debug_info(self) -> dict:
        """Retourne des infos utiles pour un overlay de debug."""
        return {
            "fps"   : round(self.clock.get_fps(), 1),
            "dt"    : round(self.dt * 1000, 2),    # En ms
            "state" : self.fsm.current_name,
        }