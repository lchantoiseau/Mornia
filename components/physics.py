# =============================================================================
#  MORNIA — components/physics.py
#  Gère la physique d'une entité : gravité, vélocité, friction,
#  sauts, dash, et résolution des collisions avec les tiles.
# =============================================================================

import pygame
from entities.base_entity import Component
from settings import (
    GRAVITY, MAX_FALL_SPEED, FRICTION,
    PLAYER_JUMP_FORCE, PLAYER_DASH_SPEED, PLAYER_DASH_DURATION,
    PLAYER_DASH_COOLDOWN,
)


class PhysicsComponent(Component):
    """
    Applique la physique à une entité frame par frame.

    Gère :
      - Gravité et chute
      - Vélocité X/Y avec friction
      - Saut (simple + coyote time + jump buffer)
      - Dash directionnel
      - Détection sol / plafond / murs (via CollisionSystem)
      - État au sol / en l'air
    """

    def __init__(
        self,
        has_gravity     : bool  = True,
        gravity_scale   : float = 1.0,
        can_jump        : bool  = True,
        can_dash        : bool  = True,
        jump_force      : float = PLAYER_JUMP_FORCE,
        max_jumps       : int   = 1,      # 1 = saut simple, 2 = double saut
        dash_speed      : float = PLAYER_DASH_SPEED,
        dash_duration   : int   = PLAYER_DASH_DURATION,
        dash_cooldown   : int   = PLAYER_DASH_COOLDOWN,
    ):
        super().__init__()

        # --- Configuration ---
        self.has_gravity    = has_gravity
        self.gravity_scale  = gravity_scale
        self.can_jump       = can_jump
        self.can_dash       = can_dash
        self.jump_force     = jump_force
        self.max_jumps      = max_jumps
        self.dash_speed     = dash_speed
        self.dash_duration  = dash_duration
        self.dash_cooldown  = dash_cooldown

        # --- État interne ---
        self.on_ground      = False
        self.on_wall_left   = False
        self.on_wall_right  = False
        self.on_ceiling     = False

        # Sauts
        self._jumps_left    = max_jumps
        self._coyote_timer  = 0      # Frames de "grâce" après avoir quitté une plateforme
        self._jump_buffer   = 0      # Frames où le joueur a appuyé saut avant d'atterrir
        self._COYOTE_FRAMES = 8
        self._JUMP_BUFFER_FRAMES = 10

        # Dash
        self._dashing           = False
        self._dash_timer        = 0
        self._dash_cooldown_timer = 0
        self._dash_dir          = 1      # Direction du dash (+1 / -1)
        self._dash_available    = True

        # Knockback
        self._knockback_timer   = 0
        self._knockback_frames  = 0

        # Référence à la tilemap (injectée par Level)
        self.tilemap = None

    # ------------------------------------------------------------------
    # Propriétés publiques
    # ------------------------------------------------------------------

    @property
    def is_dashing(self) -> bool:
        return self._dashing

    @property
    def dash_on_cooldown(self) -> bool:
        return self._dash_cooldown_timer > 0

    @property
    def can_act(self) -> bool:
        """False pendant un knockback — bloque les inputs."""
        return self._knockback_timer <= 0

    # ------------------------------------------------------------------
    # Update principal
    # ------------------------------------------------------------------

    def update(self, dt: float):
        owner = self.owner

        # 1. Dash
        self._update_dash()

        # 2. Gravité (désactivée pendant le dash horizontal)
        if self.has_gravity and not self._dashing:
            owner.vel_y += GRAVITY * self.gravity_scale
            owner.vel_y  = min(owner.vel_y, MAX_FALL_SPEED)

        # 3. Friction au sol sur X (hors dash, hors knockback)
        if self.on_ground and not self._dashing and self._knockback_timer <= 0:
            owner.vel_x *= FRICTION

        # 4. Knockback
        if self._knockback_timer > 0:
            self._knockback_timer -= 1

        # 5. Coyote time
        if self.on_ground:
            self._coyote_timer = self._COYOTE_FRAMES
            self._jumps_left   = self.max_jumps
            self._dash_available = True
        elif self._coyote_timer > 0:
            self._coyote_timer -= 1

        # 6. Jump buffer
        if self._jump_buffer > 0:
            self._jump_buffer -= 1

        # 7. Dash cooldown
        if self._dash_cooldown_timer > 0:
            self._dash_cooldown_timer -= 1

        # 8. Déplacement + résolution collisions
        self._move_and_collide()

    # ------------------------------------------------------------------
    # Mouvement + collisions tiles
    # ------------------------------------------------------------------

    def _move_and_collide(self):
        owner = self.owner

        # Reset flags de contact
        self.on_ground      = False
        self.on_ceiling     = False
        self.on_wall_left   = False
        self.on_wall_right  = False

        # --- Axe X ---
        owner.x += owner.vel_x
        owner.sync_rect()

        if self.tilemap:
            collisions_x = self.tilemap.get_collisions(owner.rect)
            for tile_rect in collisions_x:
                if owner.vel_x > 0:
                    owner.rect.right  = tile_rect.left
                    self.on_wall_right = True
                elif owner.vel_x < 0:
                    owner.rect.left   = tile_rect.right
                    self.on_wall_left  = True
                owner.vel_x = 0
                owner.x     = float(owner.rect.x)

        # --- Axe Y ---
        owner.y += owner.vel_y
        owner.sync_rect()

        if self.tilemap:
            collisions_y = self.tilemap.get_collisions(owner.rect)
            for tile_rect in collisions_y:
                if owner.vel_y > 0:
                    owner.rect.bottom = tile_rect.top
                    self.on_ground    = True
                elif owner.vel_y < 0:
                    owner.rect.top    = tile_rect.bottom
                    self.on_ceiling   = True
                owner.vel_y = 0
                owner.y     = float(owner.rect.y)

        owner.sync_rect()

    # ------------------------------------------------------------------
    # Saut
    # ------------------------------------------------------------------

    def jump(self):
        """
        Tente d'effectuer un saut.
        Prend en compte le coyote time et le jump buffer.
        """
        if not self.can_jump:
            return

        # On autorise le saut si :
        # - on est au sol (ou dans la fenêtre coyote)
        # - ou on a encore des sauts disponibles (double saut)
        can_jump_now = (self.on_ground or self._coyote_timer > 0)

        if can_jump_now or self._jumps_left > 0:
            self.owner.vel_y    = self.jump_force
            self._jumps_left    = max(0, self._jumps_left - 1)
            self._coyote_timer  = 0   # Consomme le coyote time
        else:
            # Pas encore au sol : on met en mémoire tampon
            self._jump_buffer = self._JUMP_BUFFER_FRAMES

    def jump_cut(self):
        """
        Coupe le saut si le bouton est relâché tôt (saut variable).
        Donne un contrôle précis de la hauteur de saut.
        """
        if self.owner.vel_y < 0:
            self.owner.vel_y *= 0.5

    # ------------------------------------------------------------------
    # Dash
    # ------------------------------------------------------------------

    def dash(self, direction: int = None):
        """
        Déclenche un dash dans la direction donnée.
        direction : +1 droite, -1 gauche. None = utilise owner.facing.
        """
        if not self.can_dash:
            return
        if self._dashing or self._dash_cooldown_timer > 0:
            return
        if not self._dash_available:
            return

        self._dash_dir            = direction if direction is not None else self.owner.facing
        self._dashing             = True
        self._dash_timer          = self.dash_duration
        self._dash_available      = False   # Un seul dash en l'air
        self.owner.vel_y          = 0       # Neutralise la gravité pendant le dash

    def _update_dash(self):
        if not self._dashing:
            return

        self._dash_timer -= 1
        self.owner.vel_x  = self._dash_dir * self.dash_speed
        self.owner.vel_y  = 0   # Reste horizontal pendant le dash

        if self._dash_timer <= 0:
            self._dashing             = False
            self._dash_cooldown_timer = self.dash_cooldown
            # Réduit la vélocité en sortie de dash pour un feel plus propre
            self.owner.vel_x *= 0.3

    # ------------------------------------------------------------------
    # Knockback
    # ------------------------------------------------------------------

    def apply_knockback(self, direction: int, force_x: float, force_y: float, duration: int = 12):
        """
        Projette l'entité (reçoit un coup).
        direction : +1 ou -1 (direction depuis laquelle vient le coup)
        force_x/y : intensité du knockback
        duration  : frames pendant lesquelles les inputs sont bloqués
        """
        self.owner.vel_x       = direction * force_x
        self.owner.vel_y       = -force_y   # Légère élévation
        self._knockback_timer  = duration
        self._knockback_frames = duration

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def move(self, direction: int, speed: float):
        """
        Applique une vélocité horizontale.
        Ignoré pendant un dash ou un knockback.
        """
        if self._dashing or self._knockback_timer > 0:
            return
        self.owner.vel_x = direction * speed

    def stop_x(self):
        """Arrête le mouvement horizontal (sans dash)."""
        if not self._dashing:
            self.owner.vel_x = 0

    def is_falling(self) -> bool:
        return self.owner.vel_y > 0 and not self.on_ground

    def is_rising(self) -> bool:
        return self.owner.vel_y < 0

    def set_tilemap(self, tilemap):
        """Injecte la référence à la tilemap (appelé par Level)."""
        self.tilemap = tilemap

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self):
        return (
            f"<PhysicsComponent "
            f"vel=({self.owner.vel_x:.2f},{self.owner.vel_y:.2f}) "
            f"ground={self.on_ground} dashing={self._dashing}>"
        )