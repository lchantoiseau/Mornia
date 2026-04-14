# =============================================================================
#  MORNIA — components/animation.py
#  Gère les animations d'une entité à partir de spritesheets.
#
#  Principe :
#    - On définit des "animations" : nom → liste de frames + vitesse
#    - On joue une animation courante qui avance frame par frame
#    - On peut définir des transitions automatiques (ex: ATTACK → IDLE)
#    - Compatible avec le système de flip horizontal (facing)
# =============================================================================

import pygame
from entities.base_entity import Component


# =============================================================================
#  ANIMATION  —  une séquence de frames
# =============================================================================
class Animation:
    """
    Définit une animation : séquence de Surface pygame + timing.

    frames      : liste de pygame.Surface (découpées depuis une spritesheet)
    frame_rate  : nombre de frames de jeu par frame d'animation
                  (ex: 6 = change d'image toutes les 6 frames à 60fps)
    loop        : si False, se fige sur la dernière frame et déclenche on_finish
    """

    def __init__(
        self,
        frames      : list,
        frame_rate  : int  = 6,
        loop        : bool = True,
    ):
        if not frames:
            raise ValueError("[Animation] La liste de frames ne peut pas être vide.")

        self.frames     = frames
        self.frame_rate = frame_rate
        self.loop       = loop
        self.frame_count = len(frames)

    def __repr__(self):
        return (f"<Animation frames={self.frame_count} "
                f"rate={self.frame_rate} loop={self.loop}>")


# =============================================================================
#  ANIMATION COMPONENT
# =============================================================================
class AnimationComponent(Component):
    """
    Gère la lecture des animations d'une entité.

    Usage typique :
        anim = AnimationComponent()
        anim.add("idle",   Animation(idle_frames,   frame_rate=8))
        anim.add("walk",   Animation(walk_frames,   frame_rate=5))
        anim.add("attack", Animation(attack_frames, frame_rate=4, loop=False))
        anim.add("hurt",   Animation(hurt_frames,   frame_rate=6, loop=False))
        entity.add_component(anim)

        # Chaque frame :
        anim.play("walk")          # Déclenche l'animation walk si pas déjà active
        anim.update(dt)
        surface.blit(anim.current_frame, pos)
    """

    def __init__(self, default_anim: str = None):
        super().__init__()

        self._animations    = {}          # { nom: Animation }
        self._current_name  = None        # Nom de l'animation courante
        self._current_anim  = None        # Instance Animation courante
        self._frame_index   = 0           # Index de la frame courante
        self._frame_timer   = 0           # Compteur de frames de jeu
        self._finished      = False       # True si animation non-loop terminée
        self._default       = default_anim

        # Flip horizontal (facing)
        self._flip_x        = False
        self._flip_y        = False

        # Transitions automatiques : { "attack": "idle", "hurt": "idle" }
        self._transitions   = {}

        # Callbacks
        self.on_finish_cb   = None   # fn(anim_name) — fin d'une anim non-loop
        self.on_frame_cb    = None   # fn(anim_name, frame_index) — chaque frame

        # Placeholder (carré magenta) si aucune frame n'est dispo
        self._placeholder   = self._make_placeholder()

    # ------------------------------------------------------------------
    # Enregistrement
    # ------------------------------------------------------------------

    def add(self, name: str, animation: Animation):
        """Enregistre une animation sous un nom."""
        self._animations[name] = animation
        if self._default is None:
            self._default = name
        return self   # Chaînable

    def add_transition(self, from_anim: str, to_anim: str):
        """
        Définit une transition automatique quand une animation non-loop se termine.
        ex: anim.add_transition("attack", "idle")
        """
        self._transitions[from_anim] = to_anim
        return self

    def add_transitions(self, transitions: dict):
        """
        Définit plusieurs transitions d'un coup.
        ex: anim.add_transitions({"attack": "idle", "hurt": "idle", "dash": "idle"})
        """
        self._transitions.update(transitions)
        return self

    # ------------------------------------------------------------------
    # Contrôle de lecture
    # ------------------------------------------------------------------

    def play(self, name: str, force: bool = False):
        """
        Joue l'animation 'name'.
        Si elle est déjà en cours, ne la redémarre pas (sauf si force=True).

        name  : clé de l'animation (doit être enregistrée via add())
        force : si True, redémarre même si déjà active
        """
        if name not in self._animations:
            return   # Animation inconnue — pas de crash

        if self._current_name == name and not force:
            return   # Déjà en cours

        self._current_name  = name
        self._current_anim  = self._animations[name]
        self._frame_index   = 0
        self._frame_timer   = 0
        self._finished      = False

    def restart(self):
        """Redémarre l'animation courante depuis le début."""
        if self._current_name:
            self.play(self._current_name, force=True)

    def stop(self):
        """Fige l'animation sur la frame courante."""
        self._current_anim = None

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float):
        if not self._current_anim or self._finished:
            # Si transition définie après fin d'animation
            if self._finished and self._current_name in self._transitions:
                self.play(self._transitions[self._current_name])
            return

        self._frame_timer += 1

        if self._frame_timer >= self._current_anim.frame_rate:
            self._frame_timer = 0
            self._advance_frame()

    def _advance_frame(self):
        anim = self._current_anim
        self._frame_index += 1

        # Callback par frame
        if self.on_frame_cb:
            self.on_frame_cb(self._current_name, self._frame_index)

        if self._frame_index >= anim.frame_count:
            if anim.loop:
                self._frame_index = 0   # Boucle
            else:
                self._frame_index = anim.frame_count - 1   # Fige sur dernière frame
                self._finished    = True

                if self.on_finish_cb:
                    self.on_finish_cb(self._current_name)

                # Transition automatique
                if self._current_name in self._transitions:
                    self.play(self._transitions[self._current_name])

    # ------------------------------------------------------------------
    # Frame courante
    # ------------------------------------------------------------------

    @property
    def current_frame(self) -> pygame.Surface:
        """
        Retourne la Surface de la frame courante, avec flip appliqué.
        Si aucune animation n'est définie, retourne un placeholder magenta.
        """
        if not self._current_anim:
            return self._placeholder

        frame = self._current_anim.frames[self._frame_index]

        if self._flip_x or self._flip_y:
            frame = pygame.transform.flip(frame, self._flip_x, self._flip_y)

        return frame

    @property
    def current_name(self) -> str:
        return self._current_name

    @property
    def is_finished(self) -> bool:
        """True si l'animation non-loop a atteint sa dernière frame."""
        return self._finished

    @property
    def frame_index(self) -> int:
        return self._frame_index

    def is_playing(self, name: str) -> bool:
        return self._current_name == name

    def is_playing_any(self, *names) -> bool:
        return self._current_name in names

    # ------------------------------------------------------------------
    # Flip / Direction
    # ------------------------------------------------------------------

    def set_flip(self, flip_x: bool = False, flip_y: bool = False):
        """Définit le flip de la frame courante (direction du personnage)."""
        self._flip_x = flip_x
        self._flip_y = flip_y

    def face_right(self):
        self._flip_x = False

    def face_left(self):
        self._flip_x = True

    def update_facing(self, facing: int):
        """
        Met à jour le flip depuis la direction de l'entité.
        facing : +1 = droite (pas de flip), -1 = gauche (flip X)
        """
        self._flip_x = (facing == -1)

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def get_frame_size(self) -> tuple:
        """Retourne (w, h) de la frame courante."""
        f = self.current_frame
        return f.get_size()

    def on_enter_default(self):
        """Joue l'animation par défaut — utile dans on_attach."""
        if self._default:
            self.play(self._default)

    def on_attach(self):
        """Démarre l'animation par défaut dès que le composant est attaché."""
        self.on_enter_default()

    def has_animation(self, name: str) -> bool:
        return name in self._animations

    def list_animations(self) -> list:
        return list(self._animations.keys())

    # ------------------------------------------------------------------
    # Placeholder
    # ------------------------------------------------------------------

    def _make_placeholder(self, w: int = 16, h: int = 24) -> pygame.Surface:
        """
        Carré magenta — affiché si aucune animation n'est disponible.
        Indique visuellement un asset manquant sans crash.
        """
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((255, 0, 255, 200))
        return surf

    def set_placeholder_size(self, w: int, h: int):
        """Redimensionne le placeholder (utile selon la taille du perso)."""
        self._placeholder = self._make_placeholder(w, h)

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self):
        return (
            f"<AnimationComponent "
            f"current='{self._current_name}' "
            f"frame={self._frame_index} "
            f"finished={self._finished}>"
        )


# =============================================================================
#  HELPER — Construit des animations depuis une spritesheet chargée
# =============================================================================
def build_animations_from_sheet(
    loader,
    sheet_path  : str,
    definitions : dict,
) -> dict:
    """
    Construit un dict { nom: Animation } depuis une spritesheet unique.

    loader      : AssetLoader.get_instance()
    sheet_path  : chemin relatif depuis assets/ (ex: "sprites/player/player.png")
    definitions : dict décrivant chaque animation :
        {
            "idle":   {"row": 0, "count": 4, "w": 16, "h": 24, "rate": 8},
            "walk":   {"row": 1, "count": 6, "w": 16, "h": 24, "rate": 5},
            "attack": {"row": 2, "count": 5, "w": 32, "h": 24, "rate": 4, "loop": False},
        }

    Retourne :
        { "idle": Animation(...), "walk": Animation(...), ... }
    """
    sheet      = loader.spritesheet(sheet_path)
    animations = {}

    for name, d in definitions.items():
        frames = loader.slice_sheet(
            sheet,
            frame_w = d["w"],
            frame_h = d["h"],
            row     = d.get("row", 0),
            count   = d.get("count"),
            scale   = d.get("scale", 1),
        )
        animations[name] = Animation(
            frames     = frames,
            frame_rate = d.get("rate", 6),
            loop       = d.get("loop", True),
        )

    return animations