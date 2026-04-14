# =============================================================================
#  MORNIA — world/camera.py
#  Caméra 2D qui suit le joueur avec lerp, deadzone et limites de carte.
# =============================================================================

import pygame
from settings import (
    INTERNAL_WIDTH, INTERNAL_HEIGHT,
    CAMERA_LERP, CAMERA_DEADZONE_X, CAMERA_DEADZONE_Y,
)


class Camera:
    """
    Caméra 2D pour un jeu de plateforme.

    Expose camera_offset = (ox, oy) utilisé par toutes les entités
    et la tilemap pour calculer leur position à l'écran :
        screen_x = world_x - camera.ox
        screen_y = world_y - camera.oy

    Fonctionnalités :
      - Suivi smooth (lerp) d'une cible
      - Deadzone : la caméra ne bouge pas tant que la cible est
                   dans la zone centrale
      - Limites : la caméra ne sort pas des bords de la carte
      - Shake : effet de tremblement (coups reçus, explosions)
      - Lookahead : anticipe légèrement le mouvement horizontal
    """

    def __init__(
        self,
        map_width   : int,
        map_height  : int,
        lerp        : float = CAMERA_LERP,
        deadzone_x  : int   = CAMERA_DEADZONE_X,
        deadzone_y  : int   = CAMERA_DEADZONE_Y,
        lookahead   : float = 20.0,
    ):
        """
        map_width/height : dimensions de la carte en pixels internes
        lerp             : fluidité du suivi (0 = figée, 1 = instantanée)
        deadzone_x/y     : zone morte en pixels (la caméra ne bouge pas
                           tant que la cible reste dans cette zone)
        lookahead        : pixels d'anticipation dans la direction du mouvement
        """
        self.map_width   = map_width
        self.map_height  = map_height
        self.lerp        = lerp
        self.deadzone_x  = deadzone_x
        self.deadzone_y  = deadzone_y
        self.lookahead   = lookahead

        # Demi-dimensions de l'écran
        self._hw = INTERNAL_WIDTH  // 2
        self._hh = INTERNAL_HEIGHT // 2

        # Position courante (coin haut-gauche de la vue, en pixels monde)
        self.x   = 0.0
        self.y   = 0.0

        # Cible courante
        self._target     = None
        self._target_x   = 0.0
        self._target_y   = 0.0

        # Lookahead
        self._lookahead_x = 0.0

        # Shake
        self._shake_timer    = 0
        self._shake_intensity= 0.0
        self._shake_ox       = 0
        self._shake_oy       = 0

    # ------------------------------------------------------------------
    # Cible
    # ------------------------------------------------------------------

    def follow(self, target):
        """
        Définit la cible à suivre.
        target doit avoir .rect (pygame.Rect) ou .x/.y.
        """
        self._target = target
        # Snap immédiat à la cible au premier follow
        self._snap_to_target()

    def _snap_to_target(self):
        """Téléporte la caméra sur la cible (sans lerp)."""
        if not self._target:
            return
        tx, ty   = self._get_target_pos()
        self.x   = tx - self._hw
        self.y   = ty - self._hh
        self._clamp()

    def _get_target_pos(self) -> tuple:
        """Retourne le centre de la cible en pixels monde."""
        t = self._target
        if hasattr(t, "rect"):
            return (t.rect.centerx, t.rect.centery)
        return (t.x, t.y)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float):
        if self._target:
            self._update_follow()
        self._update_shake()

    def _update_follow(self):
        tx, ty = self._get_target_pos()

        # Lookahead horizontal (anticipation direction de mouvement)
        t = self._target
        if hasattr(t, "vel_x"):
            target_lookahead  = t.vel_x * self.lookahead * 0.3
            self._lookahead_x += (target_lookahead - self._lookahead_x) * 0.08

        # Position cible de la caméra (centre écran sur la cible + lookahead)
        desired_x = tx + self._lookahead_x - self._hw
        desired_y = ty - self._hh

        # Deadzone — ne bouge que si la cible sort de la zone morte
        current_cx = self.x + self._hw
        current_cy = self.y + self._hh

        if abs(tx - current_cx) > self.deadzone_x:
            self.x += (desired_x - self.x) * self.lerp
        if abs(ty - current_cy) > self.deadzone_y:
            self.y += (desired_y - self.y) * self.lerp

        self._clamp()

    def _clamp(self):
        """Empêche la caméra de sortir des limites de la carte."""
        max_x    = max(0.0, self.map_width  - INTERNAL_WIDTH)
        max_y    = max(0.0, self.map_height - INTERNAL_HEIGHT)
        self.x   = max(0.0, min(self.x, max_x))
        self.y   = max(0.0, min(self.y, max_y))

    # ------------------------------------------------------------------
    # Shake
    # ------------------------------------------------------------------

    def shake(self, intensity: float = 3.0, duration: int = 20):
        """
        Déclenche un tremblement de caméra.
        intensity : amplitude en pixels internes
        duration  : durée en frames
        Exemple : camera.shake(4.0, 15) pour un coup reçu
        """
        # Accumule si un shake est déjà en cours
        self._shake_intensity = max(self._shake_intensity, intensity)
        self._shake_timer     = max(self._shake_timer, duration)

    def _update_shake(self):
        if self._shake_timer <= 0:
            self._shake_ox = 0
            self._shake_oy = 0
            return

        import random
        decay             = self._shake_timer / 20.0
        amp               = self._shake_intensity * min(1.0, decay)
        self._shake_ox    = int(random.uniform(-amp, amp))
        self._shake_oy    = int(random.uniform(-amp, amp))
        self._shake_timer -= 1
        if self._shake_timer <= 0:
            self._shake_intensity = 0.0

    # ------------------------------------------------------------------
    # Offset exposé (utilisé par tous les draw)
    # ------------------------------------------------------------------

    @property
    def offset(self) -> tuple:
        """
        Retourne (ox, oy) — l'offset à soustraire aux coordonnées monde
        pour obtenir les coordonnées écran.

        screen_x = world_x - camera.offset[0]
        screen_y = world_y - camera.offset[1]
        """
        return (int(self.x) + self._shake_ox,
                int(self.y) + self._shake_oy)

    @property
    def ox(self) -> int:
        return int(self.x) + self._shake_ox

    @property
    def oy(self) -> int:
        return int(self.y) + self._shake_oy

    # ------------------------------------------------------------------
    # Viewport (zone visible du monde)
    # ------------------------------------------------------------------

    @property
    def viewport(self) -> pygame.Rect:
        """
        Retourne le pygame.Rect représentant la zone du monde visible.
        Utile pour frustum culling et TileMap.draw().
        """
        return pygame.Rect(
            int(self.x), int(self.y),
            INTERNAL_WIDTH, INTERNAL_HEIGHT
        )

    # ------------------------------------------------------------------
    # Conversion de coordonnées
    # ------------------------------------------------------------------

    def world_to_screen(self, wx: float, wy: float) -> tuple:
        """Convertit des coordonnées monde en coordonnées écran."""
        return (wx - self.ox, wy - self.oy)

    def screen_to_world(self, sx: float, sy: float) -> tuple:
        """Convertit des coordonnées écran en coordonnées monde."""
        return (sx + self.ox, sy + self.oy)

    def is_visible(self, rect: pygame.Rect, margin: int = 16) -> bool:
        """
        Retourne True si un rect monde est visible à l'écran.
        margin : marge supplémentaire pour éviter le pop-in.
        """
        vp = self.viewport.inflate(margin * 2, margin * 2)
        return vp.colliderect(rect)

    # ------------------------------------------------------------------
    # Configuration dynamique
    # ------------------------------------------------------------------

    def set_map_size(self, width: int, height: int):
        """Met à jour les limites de la carte (changement de niveau)."""
        self.map_width  = width
        self.map_height = height
        self._clamp()

    def set_lerp(self, lerp: float):
        """Change la fluidité du suivi (0.0 → 1.0)."""
        self.lerp = max(0.0, min(1.0, lerp))

    def teleport(self, wx: float, wy: float):
        """Téléporte instantanément la caméra à une position monde."""
        self.x = wx - self._hw
        self.y = wy - self._hh
        self._clamp()

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def draw_debug(self, surface: pygame.Surface):
        """Dessine la deadzone et les infos de caméra (mode debug)."""
        # Deadzone
        dz_rect = pygame.Rect(
            self._hw - self.deadzone_x,
            self._hh - self.deadzone_y,
            self.deadzone_x * 2,
            self.deadzone_y * 2,
        )
        pygame.draw.rect(surface, (0, 200, 200), dz_rect, 1)

    def __repr__(self):
        return (f"<Camera pos=({self.x:.1f},{self.y:.1f}) "
                f"offset={self.offset} "
                f"map={self.map_width}x{self.map_height}>")