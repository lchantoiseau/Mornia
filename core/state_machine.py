# =============================================================================
#  MORNIA — core/state_machine.py
#  Machine à états finis (FSM) générique et réutilisable.
#  Utilisée pour : le jeu global (menus, gameplay, pause...)
#                  le joueur (idle, walk, attack, dash...)
#                  les ennemis (patrol, chase, attack...)
# =============================================================================

class State:
    """
    Classe de base pour un état.
    Chaque état concret hérite de cette classe et surcharge les méthodes
    dont il a besoin. Toutes les méthodes sont optionnelles.
    """

    def __init__(self, owner):
        """
        owner : l'objet qui possède cette FSM (Game, Player, Enemy...)
        Permet à l'état d'accéder à son propriétaire pour modifier son contexte.
        """
        self.owner = owner

    def on_enter(self):
        """Appelé une seule fois quand on entre dans cet état."""
        pass

    def on_exit(self):
        """Appelé une seule fois quand on quitte cet état."""
        pass

    def handle_input(self, events):
        """
        Traite les événements pygame pour cet état.
        events : liste d'événements retournée par pygame.event.get()
        """
        pass

    def update(self, dt):
        """
        Logique de mise à jour, appelée chaque frame.
        dt : delta time en secondes (ou en frames selon le choix du projet)
        """
        pass

    def draw(self, surface):
        """
        Rendu spécifique à cet état.
        surface : la surface pygame sur laquelle dessiner.
        """
        pass

    def __repr__(self):
        return f"<State: {self.__class__.__name__}>"


# =============================================================================

class StateMachine:
    """
    Machine à états finis générique.

    Utilisation typique :
        fsm = StateMachine(owner)
        fsm.add_state("idle",   IdleState(owner))
        fsm.add_state("walk",   WalkState(owner))
        fsm.add_state("attack", AttackState(owner))
        fsm.change("idle")

        # Dans la boucle de jeu :
        fsm.handle_input(events)
        fsm.update(dt)
        fsm.draw(surface)
    """

    def __init__(self, owner):
        """
        owner      : l'objet propriétaire (Game, Player, Enemy...)
        """
        self.owner          = owner
        self._states        = {}          # { nom: instance State }
        self._current       = None        # State actif
        self._current_name  = None        # Nom de l'état actif (str)
        self._previous_name = None        # Nom de l'état précédent (str)
        self._history       = []          # Pile d'historique (pour retour arrière)
        self._locked        = False       # Verrou temporaire (ex: animation non interruptible)

    # ------------------------------------------------------------------
    # Enregistrement des états
    # ------------------------------------------------------------------

    def add_state(self, name: str, state: State):
        """Enregistre un état sous un nom. Peut être appelé à tout moment."""
        if not isinstance(state, State):
            raise TypeError(f"[FSM] '{name}' doit être une instance de State.")
        self._states[name] = state

    def add_states(self, states: dict):
        """
        Enregistre plusieurs états d'un coup.
        states : { "idle": IdleState(owner), "walk": WalkState(owner), ... }
        """
        for name, state in states.items():
            self.add_state(name, state)

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def change(self, name: str, force: bool = False):
        """
        Transition vers l'état 'name'.

        name  : clé de l'état cible (doit être enregistré via add_state)
        force : si True, ignore le verrou (_locked)

        Séquence :
            1. on_exit()  sur l'état actuel
            2. mémorisation de l'état précédent
            3. on_enter() sur le nouvel état
        """
        if self._locked and not force:
            return

        if name not in self._states:
            raise KeyError(f"[FSM] État inconnu : '{name}'. "
                           f"États disponibles : {list(self._states.keys())}")

        # Ne rien faire si on est déjà dans cet état
        if name == self._current_name:
            return

        # Quitter l'état actuel
        if self._current is not None:
            self._current.on_exit()
            self._previous_name = self._current_name
            self._history.append(self._current_name)

        # Entrer dans le nouvel état
        self._current_name = name
        self._current      = self._states[name]
        self._current.on_enter()

    def go_back(self):
        """Revient à l'état précédent (une seule profondeur)."""
        if self._previous_name:
            self.change(self._previous_name)

    def pop_history(self):
        """
        Revient à l'état précédent via la pile d'historique.
        Utile pour des retours imbriqués (ex: pause → inventaire → pause → jeu).
        """
        if len(self._history) > 1:
            self._history.pop()               # Retire l'état actuel
            self.change(self._history[-1], force=True)

    # ------------------------------------------------------------------
    # Verrou
    # ------------------------------------------------------------------

    def lock(self):
        """Verrouille la FSM — les appels à change() sont ignorés."""
        self._locked = True

    def unlock(self):
        """Déverrouille la FSM."""
        self._locked = False

    # ------------------------------------------------------------------
    # Boucle principale
    # ------------------------------------------------------------------

    def handle_input(self, events):
        """Délègue la gestion des inputs à l'état actif."""
        if self._current:
            self._current.handle_input(events)

    def update(self, dt):
        """Délègue la mise à jour à l'état actif."""
        if self._current:
            self._current.update(dt)

    def draw(self, surface):
        """Délègue le rendu à l'état actif."""
        if self._current:
            self._current.draw(surface)

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def is_in(self, name: str) -> bool:
        """Retourne True si l'état actif est 'name'."""
        return self._current_name == name

    def is_in_any(self, *names) -> bool:
        """Retourne True si l'état actif est dans la liste fournie."""
        return self._current_name in names

    @property
    def current_name(self) -> str:
        return self._current_name

    @property
    def previous_name(self) -> str:
        return self._previous_name

    def __repr__(self):
        return (f"<StateMachine owner={self.owner.__class__.__name__} "
                f"state='{self._current_name}' "
                f"locked={self._locked}>")