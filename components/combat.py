# =============================================================================
#  MORNIA — components/combat.py
#  Gère les hitboxes d'attaque, les dégâts infligés, le knockback,
#  les fenêtres d'attaque et le système de parry/riposte.
#
#  Vocabulaire :
#    Hurtbox  : zone où l'entité PEUT être touchée  (= son rect de collision)
#    Hitbox   : zone active quand l'entité ATTAQUE  (générée temporairement)
# =============================================================================

import pygame
from entities.base_entity import Component
from components.health    import DamageType


# =============================================================================
#  ATTACK DATA  —  définition d'une attaque
# =============================================================================
class AttackData:
    """
    Décrit une attaque : dégâts, hitbox relative, knockback, frames actives.

    offset_x/y  : position de la hitbox relative au centre de l'entité
    width/height: dimensions de la hitbox
    damage_min/max : plage de dégâts (valeur aléatoire entre les deux)
    damage_type : DamageType (PHYSICAL par défaut)
    knockback_x/y : force du knockback appliqué à la cible
    active_start  : frame du moveset où la hitbox devient active
    active_end    : frame du moveset où la hitbox disparaît
    stat_scaling  : "strength" ou "dexterity" — stat utilisée pour le scaling
    stun_frames   : frames de stun infligées à la cible (0 = pas de stun)
    can_parry     : si True, cette attaque peut être parée
    """

    def __init__(
        self,
        name          : str,
        offset_x      : int   = 16,
        offset_y      : int   = 0,
        width         : int   = 16,
        height        : int   = 20,
        damage_min    : int   = 10,
        damage_max    : int   = 15,
        damage_type   : str   = DamageType.PHYSICAL,
        knockback_x   : float = 3.0,
        knockback_y   : float = 2.0,
        active_start  : int   = 2,     # Frame d'anim où la hitbox apparaît
        active_end    : int   = 4,     # Frame d'anim où elle disparaît
        stat_scaling  : str   = "strength",
        stun_frames   : int   = 0,
        can_parry     : bool  = True,
    ):
        self.name         = name
        self.offset_x     = offset_x
        self.offset_y     = offset_y
        self.width        = width
        self.height       = height
        self.damage_min   = damage_min
        self.damage_max   = damage_max
        self.damage_type  = damage_type
        self.knockback_x  = knockback_x
        self.knockback_y  = knockback_y
        self.active_start = active_start
        self.active_end   = active_end
        self.stat_scaling = stat_scaling
        self.stun_frames  = stun_frames
        self.can_parry    = can_parry

    def get_hitbox(self, owner_rect: pygame.Rect, facing: int) -> pygame.Rect:
        """
        Calcule le pygame.Rect de la hitbox dans le monde.
        facing : +1 droite, -1 gauche (flips l'offset X)
        """
        cx = owner_rect.centerx + (self.offset_x * facing)
        cy = owner_rect.centery + self.offset_y
        return pygame.Rect(
            cx - self.width  // 2,
            cy - self.height // 2,
            self.width,
            self.height,
        )

    def __repr__(self):
        return (f"<AttackData '{self.name}' "
                f"dmg={self.damage_min}-{self.damage_max} "
                f"active={self.active_start}-{self.active_end}>")


# =============================================================================
#  PARRY DATA  —  résultat d'une parade
# =============================================================================
class ParryResult:
    SUCCESS  = "success"   # Parade réussie dans la fenêtre
    BLOCKED  = "blocked"   # Bloqué mais hors fenêtre parfaite (garde)
    FAILED   = "failed"    # Pas de parade


# =============================================================================
#  COMBAT COMPONENT
# =============================================================================
class CombatComponent(Component):
    """
    Gère le système de combat d'une entité.

    Responsabilités :
      - Stocker les AttackData disponibles
      - Activer / désactiver la hitbox selon la frame d'animation
      - Calculer les dégâts (avec scaling de stats)
      - Gérer la fenêtre de parry
      - Enregistrer les entités déjà touchées (évite les double-hits)
      - Cooldown entre les attaques
    """

    def __init__(
        self,
        attacks         : dict  = None,   # { "light": AttackData, ... }
        parry_window    : int   = 12,     # Frames de parade parfaite
        parry_cooldown  : int   = 50,
        attack_cooldown : int   = 0,      # Frames min entre deux attaques
    ):
        super().__init__()

        self._attacks           = attacks or {}
        self._parry_window      = parry_window
        self._parry_cooldown    = parry_cooldown
        self._attack_cooldown   = attack_cooldown

        # --- État courant ---
        self._current_attack    = None    # AttackData active
        self._active_hitbox     = None    # pygame.Rect actif (ou None)
        self._hit_this_swing    = set()   # IDs des entités déjà touchées ce swing
        self._is_attacking      = False
        self._attack_frame      = 0       # Frame courante du swing

        # Cooldowns
        self._attack_cd_timer   = 0
        self._parry_cd_timer    = 0

        # --- Parry ---
        self._parrying          = False
        self._parry_timer       = 0       # Frames restantes de fenêtre parfaite
        self._parry_success     = False   # True pendant quelques frames après un parry réussi
        self._parry_success_timer = 0
        self._PARRY_SUCCESS_FRAMES = 20

        # --- Stats de l'owner (injectées depuis Player) ---
        # Permettent de calculer le scaling des dégâts
        self.strength           = 10
        self.dexterity          = 10

        # Callbacks
        self.on_hit_landed_cb   = None   # fn(target, damage, attack_data)
        self.on_parry_success_cb= None   # fn(attacker)
        self.on_attack_start_cb = None   # fn(attack_name)
        self.on_attack_end_cb   = None   # fn(attack_name)

    # ------------------------------------------------------------------
    # Enregistrement des attaques
    # ------------------------------------------------------------------

    def add_attack(self, name: str, attack_data: AttackData):
        self._attacks[name] = attack_data
        return self

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float):
        # Cooldowns
        if self._attack_cd_timer > 0:
            self._attack_cd_timer -= 1
        if self._parry_cd_timer > 0:
            self._parry_cd_timer  -= 1

        # Parry window
        if self._parrying:
            self._parry_timer -= 1
            if self._parry_timer <= 0:
                self._parrying = False

        # Parry success flash
        if self._parry_success_timer > 0:
            self._parry_success_timer -= 1
            if self._parry_success_timer <= 0:
                self._parry_success = False

        # Mise à jour de la hitbox active selon la frame d'animation courante
        self._update_hitbox()

    def _update_hitbox(self):
        """Active ou désactive la hitbox selon la frame d'animation courante."""
        if not self._is_attacking or not self._current_attack:
            self._active_hitbox = None
            return

        atk   = self._current_attack
        owner = self.owner

        # Récupère la frame courante depuis AnimationComponent
        frame = 0
        anim  = owner.get_component_by_name("AnimationComponent")
        if anim:
            frame = anim.frame_index

        if atk.active_start <= frame <= atk.active_end:
            self._active_hitbox = atk.get_hitbox(owner.rect, owner.facing)
        else:
            self._active_hitbox = None

    # ------------------------------------------------------------------
    # Déclencher une attaque
    # ------------------------------------------------------------------

    def start_attack(self, attack_name: str) -> bool:
        """
        Démarre une attaque.
        Retourne True si l'attaque a pu démarrer, False sinon.
        """
        if attack_name not in self._attacks:
            return False
        if self._attack_cd_timer > 0:
            return False
        if self._is_attacking:
            return False

        self._current_attack  = self._attacks[attack_name]
        self._is_attacking    = True
        self._attack_frame    = 0
        self._hit_this_swing  = set()
        self._active_hitbox   = None

        if self.on_attack_start_cb:
            self.on_attack_start_cb(attack_name)

        return True

    def end_attack(self):
        """Termine l'attaque courante (appelé par AnimationComponent.on_finish_cb)."""
        if not self._is_attacking:
            return

        attack_name           = self._current_attack.name if self._current_attack else ""
        self._is_attacking    = False
        self._current_attack  = None
        self._active_hitbox   = None
        self._hit_this_swing  = set()

        if self._attack_cooldown > 0:
            self._attack_cd_timer = self._attack_cooldown

        if self.on_attack_end_cb:
            self.on_attack_end_cb(attack_name)

    # ------------------------------------------------------------------
    # Résolution des hits
    # ------------------------------------------------------------------

    def check_hits(self, targets: list):
        """
        Vérifie si la hitbox active touche des entités dans la liste.
        targets : liste d'Entity à tester (ennemis si owner = joueur, etc.)

        Appelle take_damage() sur chaque cible touchée.
        Chaque cible n'est touchée qu'une seule fois par swing.
        """
        if not self._active_hitbox or not self._is_attacking:
            return

        for target in targets:
            if target.id in self._hit_this_swing:
                continue
            if not target.active or target.pending_destroy:
                continue
            if not self._active_hitbox.colliderect(target.rect):
                continue

            self._register_hit(target)

    def _register_hit(self, target):
        """Applique les dégâts et le knockback à une cible."""
        import random
        atk    = self._current_attack
        health = target.get_component_by_name("HealthComponent")
        if not health:
            return

        # Calcul des dégâts avec scaling de stats
        base   = random.randint(atk.damage_min, atk.damage_max)
        damage = self._apply_stat_scaling(base, atk.stat_scaling)

        # Inflige les dégâts
        real_dmg = health.take_damage(damage, atk.damage_type, source=self.owner)

        # Knockback
        physics = target.get_component_by_name("PhysicsComponent")
        if physics and atk.knockback_x > 0:
            direction = self.owner.direction_to(target)
            physics.apply_knockback(
                direction,
                atk.knockback_x,
                atk.knockback_y,
                duration=atk.stun_frames if atk.stun_frames > 0 else 12,
            )

        self._hit_this_swing.add(target.id)

        if self.on_hit_landed_cb:
            self.on_hit_landed_cb(target, real_dmg, atk)

    def _apply_stat_scaling(self, base_damage: int, stat: str) -> int:
        """Applique le scaling de stat au dégât de base."""
        from settings import FORCE_DAMAGE_SCALE, DEX_DAMAGE_SCALE
        if stat == "strength":
            return int(base_damage * (1 + self.strength * FORCE_DAMAGE_SCALE))
        elif stat == "dexterity":
            return int(base_damage * (1 + self.dexterity * DEX_DAMAGE_SCALE))
        return base_damage

    # ------------------------------------------------------------------
    # Parry
    # ------------------------------------------------------------------

    def start_parry(self) -> bool:
        """
        Démarre la fenêtre de parade.
        Retourne True si la parade a pu démarrer.
        """
        if self._parry_cd_timer > 0:
            return False
        if self._is_attacking:
            return False

        self._parrying    = True
        self._parry_timer = self._parry_window
        return True

    def try_parry(self, incoming_attack: AttackData, attacker) -> str:
        """
        Tente de parer une attaque entrante.
        Retourne un ParryResult.

        incoming_attack : l'AttackData de l'attaquant
        attacker        : l'entité qui attaque
        """
        if not incoming_attack.can_parry:
            return ParryResult.FAILED

        if self._parrying and self._parry_timer > 0:
            # Parade parfaite !
            self._parrying            = False
            self._parry_timer         = 0
            self._parry_cd_timer      = self._parry_cooldown
            self._parry_success       = True
            self._parry_success_timer = self._PARRY_SUCCESS_FRAMES

            # Stun de l'attaquant
            physics = attacker.get_component_by_name("PhysicsComponent")
            if physics:
                physics.apply_knockback(-attacker.facing, 2.0, 1.0, duration=25)

            if self.on_parry_success_cb:
                self.on_parry_success_cb(attacker)

            return ParryResult.SUCCESS

        return ParryResult.FAILED

    def end_parry(self):
        """Termine manuellement la parade (bouton relâché ou état changé)."""
        if self._parrying:
            self._parrying        = False
            self._parry_timer     = 0
            self._parry_cd_timer  = self._parry_cooldown // 2

    # ------------------------------------------------------------------
    # Propriétés publiques
    # ------------------------------------------------------------------

    @property
    def is_attacking(self) -> bool:
        return self._is_attacking

    @property
    def is_parrying(self) -> bool:
        return self._parrying

    @property
    def parry_success(self) -> bool:
        return self._parry_success

    @property
    def active_hitbox(self) -> pygame.Rect | None:
        return self._active_hitbox

    @property
    def can_attack(self) -> bool:
        return not self._is_attacking and self._attack_cd_timer <= 0

    @property
    def can_parry(self) -> bool:
        return self._parry_cd_timer <= 0 and not self._is_attacking

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def draw_debug(self, surface: pygame.Surface, camera_offset: tuple):
        """Dessine la hitbox active en rouge (mode debug)."""
        if self._active_hitbox:
            ox, oy = camera_offset
            r = pygame.Rect(
                self._active_hitbox.x - ox,
                self._active_hitbox.y - oy,
                self._active_hitbox.w,
                self._active_hitbox.h,
            )
            pygame.draw.rect(surface, (255, 50, 50), r, 1)

        # Hurtbox en bleu
        if self.owner:
            ox, oy = camera_offset
            hr = pygame.Rect(
                self.owner.rect.x - ox,
                self.owner.rect.y - oy,
                self.owner.rect.w,
                self.owner.rect.h,
            )
            pygame.draw.rect(surface, (50, 50, 255), hr, 1)

    def __repr__(self):
        return (
            f"<CombatComponent attacking={self._is_attacking} "
            f"parrying={self._parrying} "
            f"hitbox={self._active_hitbox}>"
        )