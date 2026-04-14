# =============================================================================
#  MORNIA — components/input.py
#  Traduit les actions de l'EventHandler en intentions de gameplay
#  pour le joueur. C'est la "cerveau" de contrôle du Player.
#
#  Ce composant NE modifie PAS directement la vélocité ou l'état —
#  il produit un snapshot d'intentions (InputSnapshot) que Player.update()
#  consomme pour décider quoi faire.
#
#  Avantage : on peut remplacer InputComponent par une IA (pour tester)
#  ou un replay (pour debug) sans toucher au Player.
# =============================================================================

from entities.base_entity import Component
from core.event_handler   import Action


# =============================================================================
#  INPUT SNAPSHOT  —  état des intentions pour une frame
# =============================================================================
class InputSnapshot:
    """
    Représente les intentions du joueur pour une frame donnée.
    Produit par InputComponent.update() et consommé par Player.update().
    """
    __slots__ = (
        "move_x",          # float : -1.0 / 0.0 / +1.0
        "move_y",          # float : -1.0 / 0.0 / +1.0  (échelles, interactions)
        "jump",            # bool  : appui saut (one-shot)
        "jump_held",       # bool  : saut maintenu (saut variable)
        "jump_released",   # bool  : relâchement saut (jump cut)
        "dash",            # bool  : appui dash (one-shot)
        "attack",          # bool  : appui attaque légère (one-shot)
        "attack_strong",   # bool  : appui attaque lourde (one-shot)
        "parry",           # bool  : appui parade (one-shot)
        "cast",            # bool  : appui sort (one-shot)
        "interact",        # bool  : appui interaction (one-shot)
        "use_item",        # bool  : appui item rapide (one-shot)
        "pause",           # bool  : appui pause (one-shot)
        "inventory",       # bool  : appui inventaire (one-shot)
    )

    def __init__(self):
        self.move_x        = 0.0
        self.move_y        = 0.0
        self.jump          = False
        self.jump_held     = False
        self.jump_released = False
        self.dash          = False
        self.attack        = False
        self.attack_strong = False
        self.parry         = False
        self.cast          = False
        self.interact      = False
        self.use_item      = False
        self.pause         = False
        self.inventory     = False

    def has_movement(self) -> bool:
        return self.move_x != 0.0 or self.move_y != 0.0

    def has_action(self) -> bool:
        """True si le joueur a appuyé sur n'importe quelle action ce frame."""
        return any([
            self.jump, self.dash, self.attack, self.attack_strong,
            self.parry, self.cast, self.interact, self.use_item,
        ])

    def __repr__(self):
        active = [k for k in self.__slots__ if getattr(self, k)]
        return f"<InputSnapshot {active}>"


# =============================================================================
#  INPUT COMPONENT
# =============================================================================
class InputComponent(Component):
    """
    Lit l'EventHandler et produit un InputSnapshot chaque frame.

    Paramètres :
        run_threshold : vitesse à partir de laquelle on considère que
                        le joueur "court" (si on distingue marche/course)
    """

    def __init__(self, run_threshold: float = 0.5):
        super().__init__()
        self.run_threshold  = run_threshold

        # Le snapshot courant — mis à jour chaque frame
        self.snapshot       = InputSnapshot()

        # Référence à l'EventHandler — injectée par Player ou Game
        self._event_handler = None

        # Verrou externe — si True, toutes les entrées sont ignorées
        # (cutscene, dialogue, menu pause...)
        self._locked        = False

        # Buffer de saut — permet de pré-appuyer saut avant d'atterrir
        # (géré ici pour que PhysicsComponent n'ait pas à connaître l'input)
        self._jump_buffer_frames = 10
        self._jump_buffer_timer  = 0

        # Historique des dernières actions (utile pour les combos)
        # Liste de strings, taille max HISTORY_SIZE
        self._HISTORY_SIZE  = 8
        self._action_history= []

    # ------------------------------------------------------------------
    # Attachement
    # ------------------------------------------------------------------

    def on_attach(self):
        """Récupère l'EventHandler depuis le niveau / Game au moment de l'attachement."""
        # Sera injecté manuellement via set_event_handler() depuis Player
        pass

    def set_event_handler(self, event_handler):
        """Injecte l'EventHandler (appelé par Player lors de son initialisation)."""
        self._event_handler = event_handler

    # ------------------------------------------------------------------
    # Verrou
    # ------------------------------------------------------------------

    def lock(self):
        """Bloque tous les inputs (cutscene, dialogue...)."""
        self._locked = True
        self._reset_snapshot()

    def unlock(self):
        """Débloque les inputs."""
        self._locked = False

    @property
    def is_locked(self) -> bool:
        return self._locked

    # ------------------------------------------------------------------
    # Update principal
    # ------------------------------------------------------------------

    def update(self, dt: float):
        self._reset_snapshot()

        if self._locked or self._event_handler is None:
            return

        eh = self._event_handler
        s  = self.snapshot

        # --- Mouvement horizontal ---
        if eh.held(Action.MOVE_LEFT):
            s.move_x -= 1.0
        if eh.held(Action.MOVE_RIGHT):
            s.move_x += 1.0

        # --- Mouvement vertical (échelles, interactions haut/bas) ---
        if eh.held(Action.MOVE_UP):
            s.move_y -= 1.0
        if eh.held(Action.MOVE_DOWN):
            s.move_y += 1.0

        # --- Saut ---
        s.jump          = eh.pressed(Action.JUMP)
        s.jump_held     = eh.held(Action.JUMP)
        s.jump_released = eh.released(Action.JUMP)

        # Gestion du jump buffer
        if s.jump:
            self._jump_buffer_timer = self._jump_buffer_frames
        elif self._jump_buffer_timer > 0:
            self._jump_buffer_timer -= 1
            # Injecte un jump buffered si le timer est encore actif
            # (le PhysicsComponent le consommera à l'atterrissage)
            s.jump = True

        # --- Actions de combat ---
        s.dash          = eh.pressed(Action.DASH)
        s.attack        = eh.pressed(Action.ATTACK)
        s.attack_strong = eh.pressed(Action.ATTACK_STRONG)
        s.parry         = eh.pressed(Action.PARRY)
        s.cast          = eh.pressed(Action.CAST)

        # --- Interactions ---
        s.interact      = eh.pressed(Action.INTERACT)
        s.use_item      = eh.pressed(Action.USE_ITEM)

        # --- UI ---
        s.pause         = eh.pressed(Action.PAUSE)
        s.inventory     = eh.pressed(Action.INVENTORY)

        # --- Historique des actions ---
        self._update_history(s)

    def _reset_snapshot(self):
        """Remet le snapshot à zéro avant chaque frame."""
        s               = self.snapshot
        s.move_x        = 0.0
        s.move_y        = 0.0
        s.jump          = False
        s.jump_held     = False
        s.jump_released = False
        s.dash          = False
        s.attack        = False
        s.attack_strong = False
        s.parry         = False
        s.cast          = False
        s.interact      = False
        s.use_item      = False
        s.pause         = False
        s.inventory     = False

    def _update_history(self, snapshot: InputSnapshot):
        """
        Met à jour l'historique des actions pour la détection de combos.
        Seules les actions one-shot sont enregistrées.
        """
        actions = []
        if snapshot.attack:        actions.append("attack")
        if snapshot.attack_strong: actions.append("attack_strong")
        if snapshot.dash:          actions.append("dash")
        if snapshot.parry:         actions.append("parry")
        if snapshot.cast:          actions.append("cast")
        if snapshot.jump:          actions.append("jump")

        for a in actions:
            self._action_history.append(a)
            if len(self._action_history) > self._HISTORY_SIZE:
                self._action_history.pop(0)

    # ------------------------------------------------------------------
    # Détection de combos
    # ------------------------------------------------------------------

    def check_combo(self, sequence: list) -> bool:
        """
        Vérifie si la séquence d'actions se trouve en fin d'historique.
        ex: input.check_combo(["attack", "attack", "attack_strong"])

        Retourne True si la séquence correspond aux dernières actions.
        """
        if len(sequence) > len(self._action_history):
            return False
        return self._action_history[-len(sequence):] == sequence

    def clear_history(self):
        """Vide l'historique des actions (ex: après un changement d'état)."""
        self._action_history.clear()

    def consume_jump_buffer(self):
        """
        Consomme le jump buffer (appelé par PhysicsComponent à l'atterrissage).
        Evite un double-saut involontaire.
        """
        self._jump_buffer_timer = 0
        self.snapshot.jump      = False

    # ------------------------------------------------------------------
    # Accesseurs rapides (raccourcis lisibles dans Player)
    # ------------------------------------------------------------------

    @property
    def move_x(self) -> float:
        return self.snapshot.move_x

    @property
    def move_y(self) -> float:
        return self.snapshot.move_y

    @property
    def wants_jump(self) -> bool:
        return self.snapshot.jump

    @property
    def wants_dash(self) -> bool:
        return self.snapshot.dash

    @property
    def wants_attack(self) -> bool:
        return self.snapshot.attack

    @property
    def wants_attack_strong(self) -> bool:
        return self.snapshot.attack_strong

    @property
    def wants_parry(self) -> bool:
        return self.snapshot.parry

    @property
    def wants_cast(self) -> bool:
        return self.snapshot.cast

    @property
    def wants_interact(self) -> bool:
        return self.snapshot.interact

    @property
    def wants_pause(self) -> bool:
        return self.snapshot.pause

    @property
    def wants_inventory(self) -> bool:
        return self.snapshot.inventory

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self):
        return (
            f"<InputComponent locked={self._locked} "
            f"snapshot={self.snapshot}>"
        )