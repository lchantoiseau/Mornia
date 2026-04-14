# =============================================================================
#  MORNIA — data/asset_loader.py
#  Singleton de chargement et mise en cache de tous les assets du jeu.
#  Règle d'or : on ne charge jamais un asset deux fois en mémoire.
#
#  Usage :
#      from data.asset_loader import AssetLoader
#      loader = AssetLoader.get_instance()
#      img  = loader.image("player/idle.png")
#      snd  = loader.sound("sfx/slash.wav")
#      font = loader.font("fonts/pixel.ttf", size=8)
# =============================================================================

import os
import pygame
from settings import SPRITES_DIR, SOUNDS_DIR, ASSETS_DIR


class AssetLoader:
    """
    Singleton — une seule instance pour toute la durée du jeu.
    Centralise le chargement et le cache de :
      - Images / spritesheets
      - Sons
      - Polices
      - Données brutes (JSON maps, etc.)
    """

    _instance = None

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if AssetLoader._instance is not None:
            raise RuntimeError(
                "AssetLoader est un singleton — utilise AssetLoader.get_instance()."
            )

        # Caches  { chemin_relatif : ressource }
        self._images    = {}
        self._sounds    = {}
        self._fonts     = {}   # { (chemin, size) : pygame.Font }
        self._raw       = {}   # Fichiers texte / JSON bruts

        # Compteurs pour le debug
        self._load_count = {"images": 0, "sounds": 0, "fonts": 0}

    # ------------------------------------------------------------------
    # IMAGES
    # ------------------------------------------------------------------

    def image(self, path: str, alpha: bool = True) -> pygame.Surface:
        """
        Charge et retourne une image depuis assets/.
        path  : chemin relatif depuis assets/  (ex: "sprites/player/idle.png")
        alpha : si True, conserve la transparence (convert_alpha).
        Le résultat est mis en cache — appels suivants = lookup dict O(1).
        """
        if path not in self._images:
            full = os.path.join(ASSETS_DIR, path)
            if not os.path.exists(full):
                print(f"[AssetLoader] ⚠ Image introuvable : {full}")
                self._images[path] = self._make_placeholder_image()
            else:
                surf = pygame.image.load(full)
                self._images[path] = surf.convert_alpha() if alpha else surf.convert()
                self._load_count["images"] += 1
        return self._images[path]

    def spritesheet(self, path: str) -> pygame.Surface:
        """
        Charge une spritesheet complète (même mécanisme que image()).
        On l'utilise ensuite avec slice_sheet() pour extraire les frames.
        """
        return self.image(path)

    def slice_sheet(
        self,
        sheet: pygame.Surface,
        frame_w: int,
        frame_h: int,
        row: int = 0,
        count: int = None,
        scale: int = 1
    ) -> list:
        """
        Découpe une spritesheet en liste de Surface.

        sheet   : surface retournée par spritesheet()
        frame_w : largeur d'une frame (en pixels)
        frame_h : hauteur d'une frame (en pixels)
        row     : numéro de ligne (0 = première ligne)
        count   : nombre de frames à extraire (None = toute la ligne)
        scale   : facteur d'agrandissement (utile si les sprites sont très petits)
        """
        sheet_w = sheet.get_width()
        max_frames = sheet_w // frame_w
        n = count if count is not None else max_frames

        frames = []
        for i in range(n):
            rect   = pygame.Rect(i * frame_w, row * frame_h, frame_w, frame_h)
            frame  = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), rect)
            if scale != 1:
                new_w = frame_w * scale
                new_h = frame_h * scale
                frame = pygame.transform.scale(frame, (new_w, new_h))
            frames.append(frame)
        return frames

    def _make_placeholder_image(self, w: int = 16, h: int = 16) -> pygame.Surface:
        """
        Retourne un carré magenta — indicateur visuel d'asset manquant,
        standard dans l'industrie (style Source Engine).
        """
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((255, 0, 255))
        return surf

    # ------------------------------------------------------------------
    # SONS
    # ------------------------------------------------------------------

    def sound(self, path: str) -> pygame.mixer.Sound | None:
        """
        Charge et retourne un effet sonore depuis assets/.
        path : chemin relatif depuis assets/ (ex: "sounds/sfx/slash.wav")
        Retourne None si le fichier est introuvable (pas de crash).
        """
        if path not in self._sounds:
            full = os.path.join(ASSETS_DIR, path)
            if not os.path.exists(full):
                print(f"[AssetLoader] ⚠ Son introuvable : {full}")
                self._sounds[path] = None
            else:
                self._sounds[path] = pygame.mixer.Sound(full)
                self._load_count["sounds"] += 1
        return self._sounds[path]

    # ------------------------------------------------------------------
    # POLICES
    # ------------------------------------------------------------------

    def font(self, path: str | None, size: int) -> pygame.font.Font:
        """
        Charge une police depuis assets/ ou la police système si path=None.
        path : chemin relatif depuis assets/ (ex: "fonts/pixel.ttf")
               ou None pour la police pygame par défaut.
        size : taille en points.
        Le cache utilise (path, size) comme clé.
        """
        key = (path, size)
        if key not in self._fonts:
            if path is None:
                self._fonts[key] = pygame.font.SysFont(None, size)
            else:
                full = os.path.join(ASSETS_DIR, path)
                if not os.path.exists(full):
                    print(f"[AssetLoader] ⚠ Police introuvable : {full}, "
                          f"utilisation police système.")
                    self._fonts[key] = pygame.font.SysFont(None, size)
                else:
                    self._fonts[key] = pygame.font.Font(full, size)
                    self._load_count["fonts"] += 1
        return self._fonts[key]

    def default_font(self, size: int = 8) -> pygame.font.Font:
        """Raccourci pour la police système par défaut."""
        return self.font(None, size)

    # ------------------------------------------------------------------
    # FICHIERS BRUTS (JSON, TXT...)
    # ------------------------------------------------------------------

    def raw(self, path: str) -> str | None:
        """
        Charge et retourne le contenu brut d'un fichier texte.
        Utile pour les maps JSON, dialogues, etc.
        """
        if path not in self._raw:
            full = os.path.join(ASSETS_DIR, path)
            if not os.path.exists(full):
                print(f"[AssetLoader] ! Fichier introuvable : {full}")
                self._raw[path] = None
            else:
                with open(full, "r", encoding="utf-8") as f:
                    self._raw[path] = f.read()
        return self._raw[path]

    # ------------------------------------------------------------------
    # Gestion du cache
    # ------------------------------------------------------------------

    def preload_images(self, paths: list):
        """
        Précharge une liste d'images d'un coup.
        Utile lors d'un écran de chargement pour éviter les freezes en jeu.
        """
        for path in paths:
            self.image(path)

    def clear_cache(self, keep_fonts: bool = True):
        """
        Vide le cache (libère la mémoire).
        keep_fonts : garder les polices (rechargement coûteux).
        Utile entre deux niveaux pour libérer les assets inutilisés.
        """
        self._images.clear()
        self._sounds.clear()
        self._raw.clear()
        if not keep_fonts:
            self._fonts.clear()
        self._load_count = {"images": 0, "sounds": 0, "fonts": 0}

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Retourne des statistiques sur le cache courant."""
        return {
            "images_cached" : len(self._images),
            "sounds_cached" : len(self._sounds),
            "fonts_cached"  : len(self._fonts),
            "total_loaded"  : self._load_count,
        }

    def __repr__(self):
        return f"<AssetLoader images={len(self._images)} sounds={len(self._sounds)}>"