# =============================================================================
#  MORNIA — world/level.py
#  Assemble tilemap, caméra, joueur et entités en un niveau jouable.
#  C'est le "chef d'orchestre" de tout ce qui se passe en jeu.
# =============================================================================

import pygame
from world.tilemap   import TileMap, TileType
from world.camera    import Camera
from entities.player import Player
from settings import (
    INTERNAL_WIDTH, INTERNAL_HEIGHT,
    BLACK, DARK_GREY, GameState,
)


# =============================================================================
#  CARTE DE TEST  —  niveau minimal pour valider le gameplay
#  0 = vide   1 = solide   2 = plateforme   3 = pic
# =============================================================================
TEST_MAP = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,2,2,2,2,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,2,2,2,2,2,0,0,0,0,2,2,2,2,2,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,3,3,3,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]


# =============================================================================
#  LEVEL
# =============================================================================
class Level:
    """
    Un niveau du jeu.

    Contient :
      - La TileMap (géométrie du monde)
      - La Camera (vue)
      - Le Player
      - Les entités (ennemis, PNJ, objets...)
      - La logique de mise à jour et de rendu

    Le Level est créé et géré par PlayingState.
    Il reçoit une référence à Game pour les transitions d'état.
    """

    def __init__(self, game, map_data: list = None):
        self.game       = game
        self._entities  = []          # Toutes les entités actives
        self._to_add    = []          # Entités à ajouter en fin de frame
        self.player     = None
        self.debug_mode = False        # Affiche les hitboxes et infos debug

        # ------------------------------------------------------------------
        # TileMap
        # ------------------------------------------------------------------
        self.tilemap = TileMap(tile_size=16)
        self.tilemap.load_from_data(map_data or TEST_MAP)

        # ------------------------------------------------------------------
        # Caméra
        # ------------------------------------------------------------------
        self.camera = Camera(
            map_width  = self.tilemap.px_width,
            map_height = self.tilemap.px_height,
        )

        # ------------------------------------------------------------------
        # Fond (dégradé généré une fois)
        # ------------------------------------------------------------------
        self._bg = self._make_bg()

        # ------------------------------------------------------------------
        # Spawn du joueur
        # ------------------------------------------------------------------
        self._spawn_player()

    # ------------------------------------------------------------------
    # Spawn
    # ------------------------------------------------------------------

    def _spawn_player(self):
        """Place le joueur au centre du niveau de test."""
        # Position de spawn : première tile vide de la 2ème ligne
        spawn_x = 2 * self.tilemap.tile_size
        spawn_y = (len(TEST_MAP) - 3) * self.tilemap.tile_size - 22

        self.player = Player(float(spawn_x), float(spawn_y))
        self.player.setup(
            event_handler = self.game.event_handler,
            tilemap       = self.tilemap,
            level         = self,
        )
        self.add_entity(self.player)
        self.camera.follow(self.player)

    # ------------------------------------------------------------------
    # Gestion des entités
    # ------------------------------------------------------------------

    def add_entity(self, entity):
        """Ajoute une entité au niveau."""
        entity.level = self
        entity.on_level_enter()
        self._entities.append(entity)

    def queue_entity(self, entity):
        """
        Met une entité en file d'attente pour ajout en fin de frame.
        Evite les modifications de liste pendant l'itération.
        """
        self._to_add.append(entity)

    def remove_entity(self, entity):
        entity.on_level_exit()
        if entity in self._entities:
            self._entities.remove(entity)

    def get_entities_with_tag(self, tag: str) -> list:
        """Retourne toutes les entités actives ayant ce tag."""
        return [e for e in self._entities
                if e.has_tag(tag) and e.active and not e.pending_destroy]

    def get_player(self) -> Player:
        return self.player

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float):
        # 1. Mise à jour des entités actives
        for entity in self._entities:
            if entity.active:
                entity.update(dt)

        # 2. Ajout des entités en attente
        for entity in self._to_add:
            self.add_entity(entity)
        self._to_add.clear()

        # 3. Suppression des entités marquées
        self._entities = [
            e for e in self._entities
            if not e.pending_destroy
        ]

        # 4. Dégâts des tiles dangereuses sur le joueur
        self._check_hazard_tiles()

        # 5. Caméra
        self.camera.update(dt)

    def _check_hazard_tiles(self):
        """Inflige des dégâts si le joueur touche des tiles dangereuses."""
        if not self.player or not self.player.active:
            return
        hazards = self.tilemap.get_hazard_tiles(self.player.rect)
        if hazards and self.player.health:
            from components.health import DamageType
            for tile_data in hazards:
                if tile_data.damage > 0:
                    self.player.health.take_damage(
                        tile_data.damage,
                        DamageType.TRUE,
                        ignore_iframes=False,
                    )

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface):
        """Rendu complet du niveau sur la canvas pixel art."""
        offset   = self.camera.offset
        viewport = self.camera.viewport

        # 1. Fond
        surface.blit(self._bg, (0, 0))

        # 2. Tilemap
        self.tilemap.draw(surface, offset, viewport)

        # 3. Entités (triées par Y pour un semblant de profondeur)
        visible = [
            e for e in self._entities
            if e.visible and self.camera.is_visible(e.rect)
        ]
        visible.sort(key=lambda e: e.rect.bottom)
        for entity in visible:
            entity.draw(surface, offset)

        # 4. Debug
        if self.debug_mode:
            self._draw_debug(surface, offset)

    def draw_ui(self, surface: pygame.Surface, offset_x, offset_y, scale):
        """HUD et textes nets sur la ui_surface pleine résolution."""
        self._draw_hud(surface, offset_x, offset_y, scale)

        if self.debug_mode:
            self._draw_debug_ui(surface, offset_x, offset_y, scale)

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------

    def _draw_hud(self, surface, ox, oy, scale):
        """Barres HP / Stamina / Mana en haut à gauche."""
        if not self.player:
            return

        from data.asset_loader import AssetLoader
        loader = AssetLoader.get_instance()
        font   = loader.default_font(int(7 * scale))

        p      = self.player
        health = p.health

        def sx(x): return int(ox + x * scale)
        def sy(y): return int(oy + y * scale)

        bar_x     = 6
        bar_y     = 6
        bar_w     = 50
        bar_h     = 5
        spacing   = 8

        # --- HP ---
        self._draw_bar(surface,
                       sx(bar_x), sy(bar_y),
                       int(bar_w * scale), int(bar_h * scale),
                       health.hp_percent if health else 1.0,
                       (180, 30, 30), (60, 10, 10),
                       label="HP", font=font)

        # --- Stamina ---
        st_pct = p.stamina / p.stamina_max if p.stamina_max > 0 else 1.0
        self._draw_bar(surface,
                       sx(bar_x), sy(bar_y + spacing),
                       int(bar_w * scale), int(bar_h * scale),
                       st_pct,
                       (50, 180, 50), (10, 40, 10),
                       label="ST", font=font)

        # --- Mana ---
        mn_pct = p.mana / p.mana_max if p.mana_max > 0 else 1.0
        self._draw_bar(surface,
                       sx(bar_x), sy(bar_y + spacing * 2),
                       int(bar_w * scale), int(bar_h * scale),
                       mn_pct,
                       (40, 80, 200), (10, 20, 60),
                       label="MP", font=font)

        # --- État debug (petit) ---
        state_txt = font.render(
            f"{p.fsm.current_name or ''}",
            True, (80, 80, 80)
        )
        surface.blit(state_txt, (sx(bar_x), sy(bar_y + spacing * 3 + 2)))

    def _draw_bar(self, surface, x, y, w, h, pct,
                  color_fg, color_bg, label=None, font=None):
        """Dessine une barre de ressource."""
        pct = max(0.0, min(1.0, pct))
        pygame.draw.rect(surface, color_bg,  (x, y, w, h))
        pygame.draw.rect(surface, color_fg,  (x, y, int(w * pct), h))
        pygame.draw.rect(surface, (100,100,100), (x, y, w, h), 1)
        if label and font:
            lbl = font.render(label, True, (180, 180, 180))
            surface.blit(lbl, (x - lbl.get_width() - 3, y))

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def _draw_debug(self, surface: pygame.Surface, offset: tuple):
        """Hitboxes et infos debug sur la canvas."""
        for entity in self._entities:
            entity.draw_debug(surface, offset)

    def _draw_debug_ui(self, surface, ox, oy, scale):
        """Infos debug textuelles sur ui_surface."""
        from data.asset_loader import AssetLoader
        font = AssetLoader.get_instance().default_font(int(6 * scale))

        def sx(x): return int(ox + x * scale)
        def sy(y): return int(oy + y * scale)

        if self.player:
            status = self.player.get_status()
            y = INTERNAL_HEIGHT - 60
            for key, val in status.items():
                txt = font.render(f"{key}: {val}", True, (0, 220, 0))
                surface.blit(txt, (sx(4), sy(y)))
                y += 8

        # FPS
        fps_txt = font.render(
            f"FPS: {self.game.clock.get_fps():.0f}",
            True, (0, 220, 0)
        )
        surface.blit(fps_txt, (sx(INTERNAL_WIDTH - 30), sy(4)))

    # ------------------------------------------------------------------
    # Fond
    # ------------------------------------------------------------------

    def _make_bg(self) -> pygame.Surface:
        """Génère un fond dégradé pour le niveau."""
        bg = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        top = (8, 8, 18)
        bot = (18, 8, 8)
        for y in range(INTERNAL_HEIGHT):
            t = y / INTERNAL_HEIGHT
            r = int(top[0] + (bot[0] - top[0]) * t)
            g = int(top[1] + (bot[1] - top[1]) * t)
            b = int(top[2] + (bot[2] - top[2]) * t)
            pygame.draw.line(bg, (r, g, b), (0, y), (INTERNAL_WIDTH, y))
        return bg

    # ------------------------------------------------------------------
    # Debug toggle
    # ------------------------------------------------------------------

    def toggle_debug(self):
        self.debug_mode = not self.debug_mode

    def __repr__(self):
        return (f"<Level entities={len(self._entities)} "
                f"map={self.tilemap.width}x{self.tilemap.height}>")