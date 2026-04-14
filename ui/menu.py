# =============================================================================
#  MORNIA — ui/menu.py
#  Menu principal du jeu.
#  Remplace le _PlaceholderState via game.replace_state(GameState.MAIN_MENU, ...)
#
#  Contient :
#    - MainMenuState   : écran principal (titre + items + perso animé)
#    - LoadMenuState   : sous-menu de sélection des 3 slots de sauvegarde
# =============================================================================

import pygame
import math
from core.state_machine import State
from data.asset_loader  import AssetLoader
from settings import (
    INTERNAL_WIDTH, INTERNAL_HEIGHT,
    BLACK, WHITE, GOLD, DARK_GREY, MID_GREY, LIGHT_GREY, DARK_RED,
    GameState, SAVE_SLOTS,
    MENU_FONT_SIZE_TITLE, MENU_FONT_SIZE_ITEM, MENU_ITEM_SPACING,
)


# =============================================================================
#  CONSTANTES LOCALES AU MENU
# =============================================================================
COLOR_BG_TOP        = (5,  5,  10)    # Dégradé fond haut
COLOR_BG_BOT        = (15, 5,  5)     # Dégradé fond bas
COLOR_ITEM_NORMAL   = (160, 140, 110) # Texte item non sélectionné
COLOR_ITEM_SELECTED = GOLD            # Texte item sélectionné
COLOR_ITEM_DISABLED = (60,  55,  45)  # Texte item grisé (ex: Continuer sans save)
COLOR_CURSOR        = GOLD
COLOR_VIGNETTE      = (0, 0, 0, 180)  # RGBA — assombrissement bords

# Positions (coordonnées internes 320×180)
TITLE_X         = INTERNAL_WIDTH  // 2
TITLE_Y         = 38
MENU_START_X    = 38
MENU_START_Y    = 90
CHAR_X          = 240
CHAR_Y          = 110


# =============================================================================
#  PARTICULES D'AMBIANCE  (cendres / braises qui flottent)
# =============================================================================
import random

class _Particle:
    def __init__(self):
        self.reset(spawn=True)

    def reset(self, spawn=False):
        self.x    = random.uniform(0, INTERNAL_WIDTH)
        self.y    = INTERNAL_HEIGHT + 4 if not spawn else random.uniform(0, INTERNAL_HEIGHT)
        self.vy   = random.uniform(-0.15, -0.5)   # Remonte doucement
        self.vx   = random.uniform(-0.1,  0.1)
        self.life = random.uniform(0.3, 1.0)       # Alpha initial
        self.size = random.choice([1, 1, 1, 2])
        r = random.randint(0, 2)
        if r == 0:
            self.color = (220, 160,  40)  # Braise dorée
        elif r == 1:
            self.color = (180,  60,  20)  # Braise rouge
        else:
            self.color = (140, 130, 120)  # Cendre grise

    def update(self):
        self.x    += self.vx
        self.y    += self.vy
        self.life -= 0.003
        if self.life <= 0 or self.y < -4:
            self.reset()

    def draw(self, surface):
        alpha = max(0, min(255, int(self.life * 255)))
        col   = (*self.color, alpha)
        s     = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        s.fill(col)
        surface.blit(s, (int(self.x), int(self.y)))


# =============================================================================
#  PERSONNAGE PLACEHOLDER ANIME
#  Sera remplacé par de vrais sprites quand les assets seront prêts.
#  Simule un idle avec respiration (bob vertical) et effet de cape.
# =============================================================================
class _AnimatedCharPlaceholder:
    def __init__(self):
        self.t      = 0.0
        self.x      = CHAR_X
        self.y      = CHAR_Y
        # Couleurs du personnage
        self.C_BODY = (50,  45,  60)
        self.C_CAPE = (80,  20,  20)
        self.C_HEAD = (200, 170, 130)
        self.C_GLOW = (180, 120,  40)

    def update(self, dt):
        self.t += dt

    def draw(self, surface):
        t      = self.t
        bob    = math.sin(t * 2.0) * 1.5          # Respiration verticale
        cape_w = 10 + math.sin(t * 1.5) * 2       # Ondulation cape
        glow   = 80 + int(math.sin(t * 3.0) * 30) # Pulsation lueur

        cx = self.x
        cy = int(self.y + bob)

        # --- Lueur au sol ---
        for r in range(14, 0, -3):
            alpha = max(0, glow - r * 10)
            gs    = pygame.Surface((r * 2, r), pygame.SRCALPHA)
            gs.fill((180, 100, 20, alpha))
            surface.blit(gs, (cx - r, cy + 18))

        # --- Cape (derrière le corps) ---
        cape_pts = [
            (cx - 5,         cy - 8),
            (cx - 5 - int(cape_w), cy + 20),
            (cx + 3,         cy + 18),
            (cx + 3,         cy - 6),
        ]
        pygame.draw.polygon(surface, self.C_CAPE, cape_pts)

        # --- Corps ---
        pygame.draw.rect(surface, self.C_BODY, (cx - 4, cy - 8, 8, 14))

        # --- Tête ---
        pygame.draw.rect(surface, self.C_HEAD, (cx - 3, cy - 16, 6, 7))

        # --- Capuche ---
        pygame.draw.polygon(surface, self.C_CAPE, [
            (cx - 4, cy - 14),
            (cx + 3, cy - 14),
            (cx + 4, cy - 9),
            (cx - 5, cy - 9),
        ])

        # --- Arme (épée) ---
        sword_x = cx + 5
        sword_y = cy - 4
        pygame.draw.line(surface, (160, 160, 180),
                         (sword_x, sword_y),
                         (sword_x + 1, sword_y + 12), 1)
        pygame.draw.line(surface, GOLD,
                         (sword_x - 2, sword_y + 2),
                         (sword_x + 3, sword_y + 2), 1)


# =============================================================================
#  ITEM DE MENU
# =============================================================================
class _MenuItem:
    def __init__(self, label: str, action: str, enabled: bool = True):
        self.label   = label
        self.action  = action    # Identifiant de l'action à déclencher
        self.enabled = enabled


# =============================================================================
#  MAIN MENU STATE
# =============================================================================
class MainMenuState(State):
    """
    État du menu principal.
    S'installe via : game.replace_state(GameState.MAIN_MENU, MainMenuState(game))
    """

    def __init__(self, game):
        super().__init__(owner=game)
        self.game    = game
        self.loader  = AssetLoader.get_instance()

        # Polices (chargées en on_enter pour s'assurer que pygame est init)
        self._font_title  = None
        self._font_item   = None
        self._font_hint   = None

        # Items du menu
        self._items       = []
        self._cursor      = 0     # Index de l'item sélectionné

        # Visuels
        self._particles   = [_Particle() for _ in range(40)]
        self._char        = _AnimatedCharPlaceholder()
        self._bg          = None  # Surface dégradé (générée une seule fois)
        self._vignette    = None  # Surface vignette (générée une seule fois)

        # Animation d'entrée
        self._enter_alpha = 0     # Fade-in depuis le noir
        self._fading_in   = True

        # Animation de sélection
        self._confirm_timer = 0   # Délai avant transition après confirmation
        self._confirming    = False

        # Timer pour le clignotement du curseur
        self._blink_t     = 0.0

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def on_enter(self):
        # Polices chargées à PLEINE résolution (×SCALE_FACTOR)
        # Elles seront dessinées sur ui_surface (1280×720), pas sur la canvas
        from settings import SCALE_FACTOR
        self._scale     = SCALE_FACTOR
        self._font_title = self.loader.default_font(MENU_FONT_SIZE_TITLE * SCALE_FACTOR)
        self._font_item  = self.loader.default_font(MENU_FONT_SIZE_ITEM  * SCALE_FACTOR)
        self._font_hint  = self.loader.default_font(7 * SCALE_FACTOR)

        self._build_items()
        self._cursor      = 0
        self._fading_in   = True
        self._enter_alpha = 0
        self._confirming  = False
        self._confirm_timer = 0

        self._bg        = self._make_bg()
        self._vignette  = self._make_vignette()

    def on_exit(self):
        pass

    # ------------------------------------------------------------------
    # Construction des items
    # ------------------------------------------------------------------

    def _build_items(self):
        """
        Construit la liste d'items selon l'état des sauvegardes.
        'Continuer' est désactivé s'il n'y a aucune sauvegarde.
        """
        has_save = self._check_any_save()
        self._items = [
            _MenuItem("Nouvelle Partie",  "new_game"),
            _MenuItem("Continuer",        "continue",   enabled=has_save),
            _MenuItem("Charger Partie",   "load_game",  enabled=has_save),
            _MenuItem("Options",          "options"),
            _MenuItem("Quitter",          "quit"),
        ]
        # Placer le curseur sur le premier item activé
        self._cursor = next(
            (i for i, it in enumerate(self._items) if it.enabled), 0
        )

    def _check_any_save(self) -> bool:
        """Vérifie si au moins un slot de sauvegarde existe."""
        import os
        from settings import SAVE_DIR, SAVE_FILE_PREFIX
        for slot in range(1, SAVE_SLOTS + 1):
            path = os.path.join(SAVE_DIR, f"{SAVE_FILE_PREFIX}{slot}.json")
            if os.path.exists(path):
                return True
        return False

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------

    def handle_input(self, events):
        if self._fading_in or self._confirming:
            return

        eh = self.game.event_handler

        if eh.pressed("move_up"):
            self._move_cursor(-1)
        elif eh.pressed("move_down"):
            self._move_cursor(1)
        elif eh.pressed("confirm"):
            self._confirm()

    def _move_cursor(self, direction: int):
        n = len(self._items)
        for _ in range(n):
            self._cursor = (self._cursor + direction) % n
            if self._items[self._cursor].enabled:
                break
        self._blink_t = 0.0   # Reset clignotement à chaque mouvement

    def _confirm(self):
        item = self._items[self._cursor]
        if not item.enabled:
            return
        self._confirming    = True
        self._confirm_timer = 0

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt):
        # Fade-in
        if self._fading_in:
            self._enter_alpha = min(255, self._enter_alpha + 6)
            if self._enter_alpha >= 255:
                self._fading_in = False

        # Particules & perso
        for p in self._particles:
            p.update()
        self._char.update(dt)
        self._blink_t += dt

        # Délai après confirmation avant transition
        if self._confirming:
            self._confirm_timer += dt
            if self._confirm_timer >= 0.35:
                self._trigger_action(self._items[self._cursor].action)
                self._confirming = False

    def _trigger_action(self, action: str):
        if action == "new_game":
            self.game.start_new_game(slot=1)
        elif action == "continue":
            self.game.load_game(slot=self._latest_save_slot())
        elif action == "load_game":
            self.game.replace_state(GameState.MAIN_MENU,
                                    LoadMenuState(self.game, back_state=GameState.MAIN_MENU))
            self.game.fsm.change(GameState.MAIN_MENU)
        elif action == "options":
            pass   # TODO : OptionsState
        elif action == "quit":
            self.game.quit()

    def _latest_save_slot(self) -> int:
        """Retourne le slot le plus récent (par date de modif)."""
        import os
        from settings import SAVE_DIR, SAVE_FILE_PREFIX
        latest, latest_t = 1, 0
        for slot in range(1, SAVE_SLOTS + 1):
            path = os.path.join(SAVE_DIR, f"{SAVE_FILE_PREFIX}{slot}.json")
            if os.path.exists(path):
                t = os.path.getmtime(path)
                if t > latest_t:
                    latest, latest_t = slot, t
        return latest

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface):
        # Canvas pixel art : fond, particules, personnage, séparateur
        surface.blit(self._bg, (0, 0))
        for p in self._particles:
            p.draw(surface)
        self._char.draw(surface)
        self._draw_separator(surface)

        # Vignette
        surface.blit(self._vignette, (0, 0))

    def draw_ui(self, surface, offset_x, offset_y, scale):
        """
        Texte rendu à pleine résolution sur la ui_surface de Game.
        offset_x/y : décalage letterbox   scale : facteur d'upscale courant
        """
        def sx(x): return int(offset_x + x * scale)   # Coordonnée X interne → écran
        def sy(y): return int(offset_y + y * scale)   # Coordonnée Y interne → écran

        # --- Titre ---
        shadow = self._font_title.render("MORNIA", True, (20, 5, 5))
        sr     = shadow.get_rect(centerx=sx(TITLE_X) + 2, centery=sy(TITLE_Y) + 2)
        surface.blit(shadow, sr)
        title  = self._font_title.render("MORNIA", True, GOLD)
        tr     = title.get_rect(centerx=sx(TITLE_X), centery=sy(TITLE_Y))
        surface.blit(title, tr)
        sub    = self._font_hint.render("Le Monde Oublié", True, (120, 100, 70))
        subr   = sub.get_rect(centerx=sx(TITLE_X), centery=sy(TITLE_Y + 14))
        surface.blit(sub, subr)

        # --- Items ---
        for i, item in enumerate(self._items):
            y = MENU_START_Y + i * MENU_ITEM_SPACING
            if not item.enabled:
                color = COLOR_ITEM_DISABLED
            elif i == self._cursor:
                pulse = 0.85 + 0.15 * math.sin(self._blink_t * 6.0)
                color = (int(GOLD[0]*pulse), int(GOLD[1]*pulse), int(GOLD[2]*pulse))
            else:
                color = COLOR_ITEM_NORMAL

            if i == self._cursor and item.enabled:
                cur = self._font_item.render(">", True, COLOR_CURSOR)
                surface.blit(cur, (sx(MENU_START_X - 8), sy(y)))

            text = self._font_item.render(item.label, True, color)
            surface.blit(text, (sx(MENU_START_X), sy(y)))

        # --- Hint ---
        hint = self._font_hint.render(
            "↑↓ Naviguer    Entrée Confirmer", True, (60, 55, 45)
        )
        surface.blit(hint, (sx(4), sy(INTERNAL_HEIGHT - 8)))

        # --- Fade-in / Fade-out ---
        if self._fading_in or self._confirming:
            fade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            alpha = 255 - self._enter_alpha if self._fading_in else \
                    int(self._confirm_timer / 0.35 * 200)
            fade.fill((0, 0, 0, min(255, alpha)))
            surface.blit(fade, (0, 0))

    def _draw_separator(self, surface):
        y   = TITLE_Y + 22
        col = (60, 45, 25)
        pygame.draw.line(surface, col, (20, y), (INTERNAL_WIDTH - 20, y), 1)
        # Points décoratifs aux extrémités
        pygame.draw.rect(surface, GOLD, (18, y - 1, 3, 3))
        pygame.draw.rect(surface, GOLD, (INTERNAL_WIDTH - 21, y - 1, 3, 3))

    # ------------------------------------------------------------------
    # Surfaces statiques (générées une seule fois)
    # ------------------------------------------------------------------

    def _make_bg(self) -> pygame.Surface:
        """Génère un fond dégradé vertical du haut (presque noir) au bas (rouge sombre)."""
        bg = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        for y in range(INTERNAL_HEIGHT):
            t   = y / INTERNAL_HEIGHT
            r   = int(COLOR_BG_TOP[0] + (COLOR_BG_BOT[0] - COLOR_BG_TOP[0]) * t)
            g   = int(COLOR_BG_TOP[1] + (COLOR_BG_BOT[1] - COLOR_BG_TOP[1]) * t)
            b   = int(COLOR_BG_TOP[2] + (COLOR_BG_BOT[2] - COLOR_BG_TOP[2]) * t)
            pygame.draw.line(bg, (r, g, b), (0, y), (INTERNAL_WIDTH, y))
        return bg

    def _make_vignette(self) -> pygame.Surface:
        """Génère une vignette (assombrissement progressif sur les bords)."""
        vig = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        cx  = INTERNAL_WIDTH  // 2
        cy  = INTERNAL_HEIGHT // 2
        for y in range(INTERNAL_HEIGHT):
            for x in range(INTERNAL_WIDTH):
                dx = (x - cx) / cx
                dy = (y - cy) / cy
                d  = min(1.0, (dx * dx + dy * dy) ** 0.5)
                a  = int(d * d * 160)
                vig.set_at((x, y), (0, 0, 0, a))
        return vig


# =============================================================================
#  LOAD MENU STATE  —  Sélection du slot de sauvegarde
# =============================================================================
class LoadMenuState(State):
    """
    Sous-menu affiché quand le joueur choisit "Charger Partie".
    Affiche les 3 slots avec leurs infos (niveau, zone, temps de jeu).
    """

    def __init__(self, game, back_state: str = GameState.MAIN_MENU):
        super().__init__(owner=game)
        self.game        = game
        self.back_state  = back_state
        self._cursor     = 0
        self._slots      = []
        self._font_title = None
        self._font_item  = None
        self._font_info  = None

    def on_enter(self):
        from settings import SCALE_FACTOR
        loader           = AssetLoader.get_instance()
        self._scale      = SCALE_FACTOR
        self._font_title = loader.default_font(MENU_FONT_SIZE_ITEM * SCALE_FACTOR)
        self._font_item  = loader.default_font(MENU_FONT_SIZE_ITEM * SCALE_FACTOR)
        self._font_info  = loader.default_font(7 * SCALE_FACTOR)
        self._slots      = self._load_slot_data()
        self._cursor     = 0

    def _load_slot_data(self) -> list:
        """
        Retourne une liste de 3 dicts avec les infos de chaque slot.
        Si le fichier n'existe pas, le slot est marqué vide.
        """
        import os, json
        from settings import SAVE_DIR, SAVE_FILE_PREFIX
        slots = []
        for i in range(1, SAVE_SLOTS + 1):
            path = os.path.join(SAVE_DIR, f"{SAVE_FILE_PREFIX}{i}.json")
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    slots.append({
                        "slot"     : i,
                        "empty"    : False,
                        "level"    : data.get("player_level", 1),
                        "zone"     : data.get("zone_name",    "Inconnue"),
                        "playtime" : data.get("playtime",     0),
                    })
                except Exception:
                    slots.append({"slot": i, "empty": True})
            else:
                slots.append({"slot": i, "empty": True})
        return slots

    def handle_input(self, events):
        eh = self.game.event_handler
        if eh.pressed("move_up"):
            self._cursor = (self._cursor - 1) % SAVE_SLOTS
        elif eh.pressed("move_down"):
            self._cursor = (self._cursor + 1) % SAVE_SLOTS
        elif eh.pressed("confirm"):
            slot = self._slots[self._cursor]
            if not slot["empty"]:
                self.game.load_game(slot["slot"])
        elif eh.pressed("cancel"):
            # Retour au menu principal
            self.game.replace_state(
                GameState.MAIN_MENU,
                MainMenuState(self.game)
            )
            self.game.fsm.change(GameState.MAIN_MENU)

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill(BLACK)

    def draw_ui(self, surface, offset_x, offset_y, scale):
        def sx(x): return int(offset_x + x * scale)
        def sy(y): return int(offset_y + y * scale)

        # Titre
        title = self._font_title.render("— Charger Partie —", True, GOLD)
        surface.blit(title, title.get_rect(centerx=sx(INTERNAL_WIDTH // 2), centery=sy(25)))

        # Slots
        for i, slot in enumerate(self._slots):
            y        = 55 + i * 38
            selected = (i == self._cursor)
            col_box  = (40, 30, 20) if selected else (20, 15, 10)
            col_bord = GOLD         if selected else (60, 45, 25)

            box = pygame.Rect(sx(20), sy(y), sx(INTERNAL_WIDTH - 40) - sx(20), int(30 * scale))
            pygame.draw.rect(surface, col_box,  box)
            pygame.draw.rect(surface, col_bord, box, 1)

            if selected:
                cur = self._font_item.render(">", True, GOLD)
                surface.blit(cur, (sx(10), sy(y + 10)))

            if slot["empty"]:
                label = self._font_item.render(f"Slot {slot['slot']} — Vide", True, MID_GREY)
                surface.blit(label, (sx(28), sy(y + 10)))
            else:
                label = self._font_item.render(
                    f"Slot {slot['slot']}  —  Niv. {slot['level']}  —  {slot['zone']}",
                    True, COLOR_ITEM_NORMAL
                )
                surface.blit(label, (sx(28), sy(y + 5)))
                pt       = slot["playtime"]
                h, m     = divmod(int(pt) // 60, 60)
                t_surf   = self._font_info.render(f"{h:02d}h{m:02d}", True, (80, 70, 55))
                surface.blit(t_surf, (sx(28), sy(y + 18)))

        hint = self._font_info.render(
            "↑↓ Naviguer    Entrée Charger    Échap Retour", True, (60, 55, 45)
        )
        surface.blit(hint, (sx(4), sy(INTERNAL_HEIGHT - 8)))


# =============================================================================
#  HELPER — Installe les vrais menus dans le jeu
#  Appelé depuis main.py après Game()
# =============================================================================
def install_menus(game):
    """
    Remplace les placeholders de menu par les vraies implémentations.
    Appeler cette fonction dans main.py juste après game = Game().

    from ui.menu import install_menus
    install_menus(game)
    """
    game.replace_state(GameState.MAIN_MENU, MainMenuState(game))