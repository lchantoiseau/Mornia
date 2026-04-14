# =============================================================================
#  MORNIA — world/tilemap.py
#  Gère la grille de tiles : stockage, collisions, rendu.
#
#  Supporte deux modes :
#    1. Chargement depuis un dict Python (niveaux codés en dur pour les tests)
#    2. Chargement depuis un fichier JSON (format simple maison)
#
#  Chaque tile est un entier :
#    0  = vide (pas de collision, pas de rendu)
#    1+ = ID de tile (lookup dans le tileset)
#
#  Les tiles solides bloquent le mouvement (collision AABB).
#  D'autres types seront ajoutés : pente, plateforme traversable, danger...
# =============================================================================

import pygame
import json
import os
from settings import ASSETS_DIR


# =============================================================================
#  TYPES DE TILES
# =============================================================================
class TileType:
    EMPTY           = 0
    SOLID           = 1    # Bloque dans toutes les directions
    PLATFORM        = 2    # Traversable par le bas, solide par le dessus
    SPIKE           = 3    # Inflige des dégâts au contact
    LADDER          = 4    # Échelle (montée/descente)
    WATER           = 5    # Ralentit, pas de gravité normale
    LAVA            = 6    # Dégâts continus
    TRIGGER         = 7    # Déclenche un événement (changement de salle...)


# Tiles qui bloquent le mouvement
SOLID_TILES     = {TileType.SOLID}
PLATFORM_TILES  = {TileType.PLATFORM}
HAZARD_TILES    = {TileType.SPIKE, TileType.LAVA}


# =============================================================================
#  TILE DATA  —  propriétés d'un type de tile
# =============================================================================
class TileData:
    """Propriétés associées à un ID de tile (couleur, type, etc.)."""
    def __init__(
        self,
        tile_id     : int,
        tile_type   : int   = TileType.SOLID,
        color       : tuple = (80, 80, 80),    # Couleur placeholder
        sprite_x    : int   = 0,               # Position dans le tileset (px)
        sprite_y    : int   = 0,
        damage      : int   = 0,               # Dégâts par frame (hazards)
    ):
        self.tile_id    = tile_id
        self.tile_type  = tile_type
        self.color      = color
        self.sprite_x   = sprite_x
        self.sprite_y   = sprite_y
        self.damage     = damage

    def is_solid(self)    -> bool: return self.tile_type == TileType.SOLID
    def is_platform(self) -> bool: return self.tile_type == TileType.PLATFORM
    def is_hazard(self)   -> bool: return self.tile_type in (TileType.SPIKE, TileType.LAVA)
    def is_ladder(self)   -> bool: return self.tile_type == TileType.LADDER


# =============================================================================
#  TILE REGISTRY  —  dictionnaire global des tiles
# =============================================================================
TILE_REGISTRY: dict[int, TileData] = {
    TileType.EMPTY   : TileData(0, TileType.EMPTY,    (0,   0,   0)),
    TileType.SOLID   : TileData(1, TileType.SOLID,    (60,  55,  70)),
    TileType.PLATFORM: TileData(2, TileType.PLATFORM, (80, 110,  60)),
    TileType.SPIKE   : TileData(3, TileType.SPIKE,    (180, 40,  40), damage=15),
    TileType.LADDER  : TileData(4, TileType.LADDER,   (120, 90,  50)),
    TileType.WATER   : TileData(5, TileType.WATER,    (30,  80, 180)),
    TileType.LAVA    : TileData(6, TileType.LAVA,     (220,100,  20), damage=5),
    TileType.TRIGGER : TileData(7, TileType.TRIGGER,  (0,   0,   0)),
}


# =============================================================================
#  TILEMAP
# =============================================================================
class TileMap:
    """
    Grille 2D de tiles.

    tile_size   : taille d'une tile en pixels internes (ex: 16)
    data        : liste 2D [row][col] d'entiers (IDs de tiles)
    """

    def __init__(self, tile_size: int = 16):
        self.tile_size  = tile_size
        self._data      = []       # list[list[int]]
        self.width      = 0        # En tiles
        self.height     = 0        # En tiles
        self.px_width   = 0        # En pixels
        self.px_height  = 0
        self._tileset   = None     # pygame.Surface du tileset (optionnel)
        self._tile_cache= {}       # Cache des surfaces de tiles découpées

    # ------------------------------------------------------------------
    # Chargement
    # ------------------------------------------------------------------

    def load_from_data(self, data: list[list[int]]):
        """
        Charge la tilemap depuis une liste 2D Python.
        Idéal pour les niveaux de test codés en dur.

        Exemple :
            MAP = [
                [1,1,1,1,1],
                [1,0,0,0,1],
                [1,0,0,0,1],
                [1,1,1,1,1],
            ]
            tilemap.load_from_data(MAP)
        """
        self._data     = [list(row) for row in data]
        self.height    = len(self._data)
        self.width     = max(len(row) for row in self._data) if self._data else 0
        self.px_width  = self.width  * self.tile_size
        self.px_height = self.height * self.tile_size
        # Normalise les lignes de longueur inégale
        for row in self._data:
            while len(row) < self.width:
                row.append(TileType.EMPTY)

    def load_from_json(self, path: str):
        """
        Charge depuis un fichier JSON.
        Format attendu :
        {
            "tile_size": 16,
            "data": [[1,1,1,...], [1,0,0,...], ...]
        }
        """
        full = os.path.join(ASSETS_DIR, path)
        with open(full, "r") as f:
            raw = json.load(f)
        self.tile_size = raw.get("tile_size", self.tile_size)
        self.load_from_data(raw["data"])

    def load_tileset(self, tileset_surface: pygame.Surface, tile_size: int = None):
        """
        Charge le tileset graphique.
        tileset_surface : spritesheet des tiles chargée via AssetLoader.
        """
        self._tileset   = tileset_surface
        self._tile_cache = {}
        if tile_size:
            self.tile_size = tile_size

    # ------------------------------------------------------------------
    # Accès aux tiles
    # ------------------------------------------------------------------

    def get_tile(self, col: int, row: int) -> int:
        """Retourne l'ID de la tile à (col, row), ou 0 si hors limites."""
        if row < 0 or row >= self.height or col < 0 or col >= self.width:
            return TileType.EMPTY
        return self._data[row][col]

    def set_tile(self, col: int, row: int, tile_id: int):
        """Modifie une tile (utile pour les niveaux destructibles plus tard)."""
        if 0 <= row < self.height and 0 <= col < self.width:
            self._data[row][col] = tile_id

    def get_tile_data(self, col: int, row: int) -> TileData:
        """Retourne le TileData associé à la tile à (col, row)."""
        tile_id = self.get_tile(col, row)
        return TILE_REGISTRY.get(tile_id, TILE_REGISTRY[TileType.SOLID])

    def world_to_tile(self, wx: float, wy: float) -> tuple:
        """Convertit des coordonnées monde (px) en coordonnées tile (col, row)."""
        return (int(wx // self.tile_size), int(wy // self.tile_size))

    def tile_to_world(self, col: int, row: int) -> tuple:
        """Convertit des coordonnées tile en coordonnées monde (coin haut-gauche)."""
        return (col * self.tile_size, row * self.tile_size)

    def tile_rect(self, col: int, row: int) -> pygame.Rect:
        """Retourne le pygame.Rect monde d'une tile."""
        x, y = self.tile_to_world(col, row)
        return pygame.Rect(x, y, self.tile_size, self.tile_size)

    # ------------------------------------------------------------------
    # Collisions
    # ------------------------------------------------------------------

    def get_collisions(self, rect: pygame.Rect) -> list:
        """
        Retourne la liste des pygame.Rect des tiles SOLIDES
        qui chevauchent le rect donné.

        Optimisé : ne teste que les tiles dans la zone du rect.
        Appelé par PhysicsComponent chaque frame.
        """
        ts       = self.tile_size
        col_min  = max(0, rect.left   // ts)
        col_max  = min(self.width  - 1, rect.right  // ts)
        row_min  = max(0, rect.top    // ts)
        row_max  = min(self.height - 1, rect.bottom // ts)

        collisions = []
        for row in range(row_min, row_max + 1):
            for col in range(col_min, col_max + 1):
                tile_id = self._data[row][col]
                if tile_id in SOLID_TILES:
                    tr = pygame.Rect(col * ts, row * ts, ts, ts)
                    if rect.colliderect(tr):
                        collisions.append(tr)
        return collisions

    def get_platform_collisions(self, rect: pygame.Rect, vel_y: float) -> list:
        """
        Collisions avec les plateformes traversables.
        Actives uniquement si le joueur tombe (vel_y > 0) et
        si le bas du rect était au-dessus du haut de la plateforme.
        """
        if vel_y <= 0:
            return []

        ts      = self.tile_size
        col_min = max(0, rect.left  // ts)
        col_max = min(self.width - 1, rect.right // ts)
        row     = rect.bottom // ts

        if row < 0 or row >= self.height:
            return []

        collisions = []
        for col in range(col_min, col_max + 1):
            tile_id = self._data[row][col] if row < self.height else 0
            if tile_id in PLATFORM_TILES:
                tr = pygame.Rect(col * ts, row * ts, ts, ts)
                # Seulement si le bas du joueur traverse le haut de la plateforme
                if rect.bottom - vel_y <= tr.top and rect.colliderect(tr):
                    collisions.append(tr)
        return collisions

    def get_hazard_tiles(self, rect: pygame.Rect) -> list:
        """
        Retourne les TileData des tiles dangereuses qui touchent le rect.
        Utilisé pour infliger des dégâts de contact (pics, lave...).
        """
        ts      = self.tile_size
        col_min = max(0, rect.left  // ts)
        col_max = min(self.width - 1, rect.right // ts)
        row_min = max(0, rect.top   // ts)
        row_max = min(self.height - 1, rect.bottom // ts)

        hazards = []
        for row in range(row_min, row_max + 1):
            for col in range(col_min, col_max + 1):
                tile_id = self._data[row][col]
                if tile_id in {TileType.SPIKE, TileType.LAVA}:
                    tr = pygame.Rect(col * ts, row * ts, ts, ts)
                    if rect.colliderect(tr):
                        hazards.append(TILE_REGISTRY[tile_id])
        return hazards

    # ------------------------------------------------------------------
    # Rendu
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, camera_offset: tuple,
             viewport: pygame.Rect = None):
        """
        Dessine les tiles visibles à l'écran.
        camera_offset : (ox, oy) fourni par Camera
        viewport      : pygame.Rect de la zone visible (optimisation)
        """
        ox, oy = camera_offset
        ts     = self.tile_size

        # Zone de tiles à dessiner (seulement ce qui est visible)
        if viewport:
            col_min = max(0, (ox + viewport.left)   // ts)
            col_max = min(self.width  - 1,
                          (ox + viewport.right)  // ts + 1)
            row_min = max(0, (oy + viewport.top)    // ts)
            row_max = min(self.height - 1,
                          (oy + viewport.bottom) // ts + 1)
        else:
            col_min, col_max = 0, self.width  - 1
            row_min, row_max = 0, self.height - 1

        for row in range(row_min, row_max + 1):
            for col in range(col_min, col_max + 1):
                tile_id = self._data[row][col]
                if tile_id == TileType.EMPTY:
                    continue

                draw_x = col * ts - ox
                draw_y = row * ts - oy

                if self._tileset:
                    self._draw_tile_sprite(surface, tile_id, draw_x, draw_y)
                else:
                    self._draw_tile_color(surface, tile_id, draw_x, draw_y, ts)

    def _draw_tile_color(self, surface, tile_id, x, y, ts):
        """Rendu placeholder : rectangle coloré selon le type de tile."""
        data  = TILE_REGISTRY.get(tile_id)
        color = data.color if data else (255, 0, 255)
        pygame.draw.rect(surface, color, (x, y, ts, ts))
        # Bordure légère pour distinguer les tiles
        pygame.draw.rect(surface, (
            min(255, color[0] + 20),
            min(255, color[1] + 20),
            min(255, color[2] + 20)
        ), (x, y, ts, ts), 1)

    def _draw_tile_sprite(self, surface, tile_id, x, y):
        """Rendu depuis le tileset graphique."""
        ts = self.tile_size
        if tile_id not in self._tile_cache:
            data = TILE_REGISTRY.get(tile_id)
            if data:
                rect  = pygame.Rect(data.sprite_x, data.sprite_y, ts, ts)
                frame = pygame.Surface((ts, ts), pygame.SRCALPHA)
                frame.blit(self._tileset, (0, 0), rect)
                self._tile_cache[tile_id] = frame
        cached = self._tile_cache.get(tile_id)
        if cached:
            surface.blit(cached, (x, y))

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def find_spawn_point(self, spawn_tile_id: int = 9) -> tuple | None:
        """
        Cherche la première tile d'un ID donné et retourne sa position monde.
        Utile pour placer le joueur au spawn point du niveau.
        """
        for row in range(self.height):
            for col in range(self.width):
                if self._data[row][col] == spawn_tile_id:
                    return self.tile_to_world(col, row)
        return None

    def is_solid_at(self, wx: float, wy: float) -> bool:
        """Retourne True si la position monde (wx, wy) est dans une tile solide."""
        col, row = self.world_to_tile(wx, wy)
        return self.get_tile(col, row) in SOLID_TILES

    def __repr__(self):
        return (f"<TileMap {self.width}x{self.height} tiles "
                f"({self.px_width}x{self.px_height}px) "
                f"tile_size={self.tile_size}>")