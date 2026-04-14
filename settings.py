# =============================================================================
#  MORNIA — settings.py
#  Toutes les constantes globales du jeu. Ne jamais hardcoder ces valeurs
#  ailleurs : toujours importer depuis ce fichier.
# =============================================================================

# -----------------------------------------------------------------------------
# FENETRE
# -----------------------------------------------------------------------------
WINDOW_TITLE   = "Mornia"
SCREEN_WIDTH   = 1280
SCREEN_HEIGHT  = 720
FPS            = 60

# Résolution interne (pixel art rendu en basse résolution puis upscalé)
INTERNAL_WIDTH  = 320
INTERNAL_HEIGHT = 180
SCALE_FACTOR    = SCREEN_WIDTH // INTERNAL_WIDTH   # = 4

# -----------------------------------------------------------------------------
# COULEURS  (R, G, B)
# -----------------------------------------------------------------------------
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
RED         = (200,  30,  30)
DARK_RED    = (120,   0,   0)
GOLD        = (212, 175,  55)
DARK_GREY   = ( 30,  30,  30)
MID_GREY    = ( 80,  80,  80)
LIGHT_GREY  = (180, 180, 180)

# Couleurs UI / HUD
COLOR_HP_BAR        = (180,  30,  30)
COLOR_HP_BG         = ( 60,  10,  10)
COLOR_MANA_BAR      = ( 40,  80, 200)
COLOR_MANA_BG       = ( 10,  20,  60)
COLOR_STAMINA_BAR   = ( 50, 180,  50)
COLOR_STAMINA_BG    = ( 10,  40,  10)

# -----------------------------------------------------------------------------
# PHYSIQUE
# -----------------------------------------------------------------------------
GRAVITY         = 0.5     # Accélération vers le bas (px/frame²)
MAX_FALL_SPEED  = 12.0    # Vitesse de chute maximale (px/frame)
FRICTION        = 0.85    # Coefficient de friction au sol (0-1)

# -----------------------------------------------------------------------------
# JOUEUR — valeurs de base (avant bonus d'équipement / stats)
# -----------------------------------------------------------------------------
PLAYER_BASE_HP          = 100
PLAYER_BASE_MANA        = 80
PLAYER_BASE_STAMINA     = 100
PLAYER_BASE_PHYS_RES    = 0       # En pourcentage (0-100)
PLAYER_BASE_MAGIC_RES   = 0
PLAYER_BASE_WEIGHT_CAP  = 50.0    # Charge max avant malus de mobilité

PLAYER_WALK_SPEED       = 2.5
PLAYER_RUN_SPEED        = 4.5
PLAYER_JUMP_FORCE       = -10.0

# Dash
PLAYER_DASH_SPEED       = 9.0
PLAYER_DASH_DURATION    = 10      # En frames
PLAYER_DASH_COOLDOWN    = 40      # En frames
PLAYER_DASH_INVINCIBLE  = True    # Invincible pendant le dash 

# Parry
PLAYER_PARRY_WINDOW     = 12      # Frames où la parade est active
PLAYER_PARRY_COOLDOWN   = 50

# Stamina
STAMINA_REGEN_RATE      = 0.8     # Stamina récupérée par frame au repos
STAMINA_REGEN_DELAY     = 60      # Frames avant que la regen démarre
STAMINA_COST_DASH       = 25
STAMINA_COST_ATTACK     = 15
STAMINA_COST_PARRY      = 20

# Invincibility frames après avoir reçu un coup
PLAYER_IFRAMES          = 60

# -----------------------------------------------------------------------------
# STATS D'AMELIORATION — scaling des dégâts
# -----------------------------------------------------------------------------
# Multiplicateur de dégâts par point de stat
FORCE_DAMAGE_SCALE      = 0.05    # +5% dégâts armes lourdes par point de Force
DEX_DAMAGE_SCALE        = 0.05    # +5% dégâts armes légères par point de Dex
INT_MANA_SCALE          = 5       # +5 mana max par point d'Intelligence
ENDURANCE_WEIGHT_SCALE  = 2.0     # +2.0 charge max par point d'Endurance

# -----------------------------------------------------------------------------
# ARMES — catégories et propriétés de base
# -----------------------------------------------------------------------------
WEAPON_TYPES = {
    "dagger": {
        "range"         : 30,
        "attack_speed"  : 8,    # Frames par frame d'attaque (plus bas = plus rapide)
        "damage_min"    : 5,
        "damage_max"    : 10,
        "stat_scaling"  : "dexterity",
        "weight"        : 3.0,
    },
    "sword": {
        "range"         : 55,
        "attack_speed"  : 14,
        "damage_min"    : 12,
        "damage_max"    : 20,
        "stat_scaling"  : "strength",
        "weight"        : 8.0,
    },
    "greatsword": {
        "range"         : 80,
        "attack_speed"  : 24,
        "damage_min"    : 25,
        "damage_max"    : 45,
        "stat_scaling"  : "strength",
        "weight"        : 18.0,
    },
    # D'autres types seront ajoutés (hache, lance, catalyseur magique...)
}

# -----------------------------------------------------------------------------
# MAGIE
# -----------------------------------------------------------------------------
MANA_REGEN_RATE     = 0.2     # Mana récupéré par frame (hors combat)
MANA_REGEN_DELAY    = 120     # Frames avant regen (après dernier sort)

# -----------------------------------------------------------------------------
# ENNEMIS — valeurs génériques (overridées dans chaque classe)
# -----------------------------------------------------------------------------
ENEMY_BASE_HP           = 40
ENEMY_BASE_DAMAGE       = 8
ENEMY_BASE_AGGRO_RANGE  = 150   # Distance à partir de laquelle l'ennemi attaque
ENEMY_BASE_PATROL_RANGE = 80    # Distance de patrouille

# -----------------------------------------------------------------------------
# CAMERA
# -----------------------------------------------------------------------------
CAMERA_LERP         = 0.1     # Fluidité du suivi (0 = statique, 1 = instantané)
CAMERA_DEADZONE_X   = 40      # Pixels de marge avant que la caméra bouge (axe X)
CAMERA_DEADZONE_Y   = 30

# -----------------------------------------------------------------------------
# SAUVEGARDES
# -----------------------------------------------------------------------------
SAVE_SLOTS          = 3
SAVE_DIR            = "saves"
SAVE_FILE_PREFIX    = "mornia_save_"   # → mornia_save_1.json, etc.

# -----------------------------------------------------------------------------
# UI / HUD
# -----------------------------------------------------------------------------
HUD_MARGIN          = 8       # Marge depuis le bord de l'écran (px internes)
HUD_BAR_WIDTH       = 60
HUD_BAR_HEIGHT      = 6
HUD_BAR_SPACING     = 4       # Espace entre les barres HP / Mana / Stamina

# Menu
MENU_FONT_SIZE_TITLE = 24
MENU_FONT_SIZE_ITEM  = 10
MENU_ITEM_SPACING    = 14

# -----------------------------------------------------------------------------
# AUDIO
# -----------------------------------------------------------------------------
MUSIC_VOLUME        = 0.5     # 0.0 → 1.0
SFX_VOLUME          = 0.8

# -----------------------------------------------------------------------------
# CHEMINS ASSETS
# -----------------------------------------------------------------------------
ASSETS_DIR      = "assets"
SPRITES_DIR     = f"{ASSETS_DIR}/sprites"
TILESETS_DIR    = f"{ASSETS_DIR}/tilesets"
SOUNDS_DIR      = f"{ASSETS_DIR}/sounds"
MAPS_DIR        = f"{ASSETS_DIR}/maps"

# -----------------------------------------------------------------------------
# ETATS DU JEU (utilisés par la StateMachine)
# -----------------------------------------------------------------------------
class GameState:
    MAIN_MENU   = "main_menu"
    PLAYING     = "playing"
    PAUSED      = "paused"
    GAME_OVER   = "game_over"
    LOADING     = "loading"
    CUTSCENE    = "cutscene"

# -----------------------------------------------------------------------------
# ETATS DU JOUEUR (utilisés par la StateMachine interne au Player)
# -----------------------------------------------------------------------------
class PlayerState:
    IDLE        = "idle"
    WALK        = "walk"
    RUN         = "run"
    JUMP        = "jump"
    FALL        = "fall"
    DASH        = "dash"
    ATTACK      = "attack"
    PARRY       = "parry"
    PARRY_SUCCESS = "parry_success"
    HURT        = "hurt"
    DEAD        = "dead"
    CAST        = "cast"

# -----------------------------------------------------------------------------
# ETATS DES ENNEMIS
# -----------------------------------------------------------------------------
class EnemyState:
    IDLE        = "idle"
    PATROL      = "patrol"
    CHASE       = "chase"
    ATTACK      = "attack"
    HURT        = "hurt"
    DEAD        = "dead"
    STUNNED     = "stunned"