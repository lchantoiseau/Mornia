# =============================================================================
#  MORNIA — core/event_handler.py
#  Centralise la lecture et le dispatch de tous les événements pygame.
#  Le reste du jeu ne touche JAMAIS pygame.event directement —
#  tout passe par EventHandler.
#
#  Deux couches :
#    1. RawInput  — état brut des touches / souris à chaque frame
#    2. Actions   — actions abstraites (JUMP, ATTACK...) mappées aux touches
#       → permet de changer les keybinds sans toucher au code de gameplay
# =============================================================================

import pygame
from settings import GameState


# =============================================================================
#  ACTIONS ABSTRAITES
#  Constantes utilisées partout dans le code de gameplay.
#  On ne parle jamais de "K_SPACE" dans Player, seulement de "JUMP".
# =============================================================================
class Action:
    # Déplacement
    MOVE_LEFT       = "move_left"
    MOVE_RIGHT      = "move_right"
    MOVE_UP         = "move_up"       # Echelles / interactions
    MOVE_DOWN       = "move_down"     # Accroupi / trappe

    # Gameplay
    JUMP            = "jump"
    DASH            = "dash"
    ATTACK          = "attack"
    ATTACK_STRONG   = "attack_strong" # Attaque chargée / lourde
    PARRY           = "parry"
    CAST            = "cast"          # Lancer un sort
    INTERACT        = "interact"      # PNJ, levier, porte...
    USE_ITEM        = "use_item"      # Consommable rapide

    # UI
    PAUSE           = "pause"
    INVENTORY       = "inventory"
    MAP             = "map"
    CONFIRM         = "confirm"       # Valider dans les menus
    CANCEL          = "cancel"        # Retour / annuler


# =============================================================================
#  KEYBINDS PAR DEFAUT
#  Format : Action → touche pygame (ou liste de touches alternatives)
#  On pourra charger un keybinds.json pour écraser ces valeurs.
# =============================================================================
DEFAULT_KEYBINDS = {
    Action.MOVE_LEFT      : [pygame.K_LEFT,  pygame.K_q],
    Action.MOVE_RIGHT     : [pygame.K_RIGHT, pygame.K_d],
    Action.MOVE_UP        : [pygame.K_UP,    pygame.K_z],
    Action.MOVE_DOWN      : [pygame.K_DOWN,  pygame.K_s],

    Action.JUMP           : [pygame.K_SPACE, pygame.K_x],
    Action.DASH           : [pygame.K_LSHIFT],
    Action.ATTACK         : [pygame.K_j],
    Action.ATTACK_STRONG  : [pygame.K_k],
    Action.PARRY          : [pygame.K_l],
    Action.CAST           : [pygame.K_u],
    Action.INTERACT       : [pygame.K_e],
    Action.USE_ITEM       : [pygame.K_r],

    Action.PAUSE          : [pygame.K_ESCAPE, pygame.K_p],
    Action.INVENTORY      : [pygame.K_i],
    Action.MAP            : [pygame.K_m],
    Action.CONFIRM        : [pygame.K_RETURN, pygame.K_SPACE],
    Action.CANCEL         : [pygame.K_ESCAPE, pygame.K_BACKSPACE],
}


# =============================================================================
#  EVENT HANDLER
# =============================================================================
class EventHandler:
    """
    Collecte tous les événements pygame une fois par frame et expose :

      • is_action_held(action)    → True tant que la touche est enfoncée
      • is_action_pressed(action) → True uniquement la frame où la touche
                                    est appuyée (one-shot)
      • is_action_released(action)→ True uniquement la frame où la touche
                                    est relâchée (one-shot)
      • quit_requested            → True si l'utilisateur ferme la fenêtre
      • raw_events                → liste brute pour les états qui en ont besoin
                                    (menus, saisie de texte...)
    """

    def __init__(self, keybinds: dict = None):
        """
        keybinds : dictionnaire Action → [touches]. Si None, utilise DEFAULT_KEYBINDS.
        """
        self.keybinds       = keybinds or DEFAULT_KEYBINDS

        # État des actions
        self._held          = set()   # Actions actuellement maintenues
        self._just_pressed  = set()   # Actions pressées cette frame uniquement
        self._just_released = set()   # Actions relâchées cette frame uniquement

        # Événements bruts de la frame courante
        self.raw_events     = []

        # Flags système
        self.quit_requested = False

        # Inverse du keybind map : touche → liste d'actions
        # Précalculé une seule fois pour de meilleures perfs
        self._key_to_actions = self._build_key_map()

    # ------------------------------------------------------------------
    # Construction de la map inversée
    # ------------------------------------------------------------------

    def _build_key_map(self) -> dict:
        """
        Construit { pygame_key: [action1, action2, ...] }
        depuis le dict keybinds { action: [key1, key2, ...] }.
        Permet un lookup O(1) à chaque événement clavier.
        """
        key_map = {}
        for action, keys in self.keybinds.items():
            for key in keys:
                key_map.setdefault(key, []).append(action)
        return key_map

    # ------------------------------------------------------------------
    # Mise à jour — à appeler UNE FOIS par frame, avant tout update()
    # ------------------------------------------------------------------

    def update(self):
        """
        Lit tous les événements pygame et met à jour les états internes.
        Doit être appelé en tout premier dans la boucle de jeu.
        """
        # Reset des one-shots
        self._just_pressed.clear()
        self._just_released.clear()
        self.quit_requested = False

        self.raw_events = pygame.event.get()

        for event in self.raw_events:

            if event.type == pygame.QUIT:
                self.quit_requested = True

            elif event.type == pygame.KEYDOWN:
                actions = self._key_to_actions.get(event.key, [])
                for action in actions:
                    if action not in self._held:
                        self._just_pressed.add(action)
                    self._held.add(action)

            elif event.type == pygame.KEYUP:
                actions = self._key_to_actions.get(event.key, [])
                for action in actions:
                    self._held.discard(action)
                    self._just_released.add(action)

    # ------------------------------------------------------------------
    # API publique — requêtes d'état
    # ------------------------------------------------------------------

    def is_action_held(self, action: str) -> bool:
        """True tant que la touche associée à 'action' est enfoncée."""
        return action in self._held

    def is_action_pressed(self, action: str) -> bool:
        """True uniquement la frame où la touche est appuyée (one-shot)."""
        return action in self._just_pressed

    def is_action_released(self, action: str) -> bool:
        """True uniquement la frame où la touche est relâchée (one-shot)."""
        return action in self._just_released

    # Raccourcis lisibles
    def held(self, action: str)    -> bool: return self.is_action_held(action)
    def pressed(self, action: str) -> bool: return self.is_action_pressed(action)
    def released(self, action: str)-> bool: return self.is_action_released(action)

    # ------------------------------------------------------------------
    # Keybinds dynamiques
    # ------------------------------------------------------------------

    def remap(self, action: str, keys: list):
        """
        Remplace les touches d'une action à la volée.
        keys : liste de codes pygame (ex: [pygame.K_SPACE, pygame.K_x])
        Utile pour le menu Options.
        """
        self.keybinds[action] = keys
        self._key_to_actions  = self._build_key_map()

    def load_keybinds(self, keybinds: dict):
        """
        Charge un dictionnaire keybinds complet (ex: depuis un fichier JSON).
        Les actions manquantes gardent leur valeur par défaut.
        """
        for action, keys in keybinds.items():
            self.keybinds[action] = keys
        self._key_to_actions = self._build_key_map()

    def reset_keybinds(self):
        """Remet les touches par défaut."""
        self.keybinds        = dict(DEFAULT_KEYBINDS)
        self._key_to_actions = self._build_key_map()

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def get_active_actions(self) -> set:
        """Retourne toutes les actions actuellement maintenues. Utile pour le debug."""
        return set(self._held)

    def __repr__(self):
        return (f"<EventHandler held={self._held} "
                f"pressed={self._just_pressed}>")