# =============================================================================
#  MORNIA — components/health.py
#  Gère les points de vie, l'invincibilité, la mort et les résistances
#  d'une entité.
# =============================================================================

from entities.base_entity import Component
from settings import PLAYER_IFRAMES


# =============================================================================
#  TYPES DE DÉGÂTS
#  Utilisés pour appliquer les résistances correctes.
# =============================================================================
class DamageType:
    PHYSICAL = "physical"
    MAGICAL  = "magical"
    POISON   = "poison"
    FIRE     = "fire"
    TRUE     = "true"     # Dégâts vrais — ignorent toutes les résistances


# =============================================================================
#  HEALTH COMPONENT
# =============================================================================
class HealthComponent(Component):
    """
    Gère :
      - PV actuels / max
      - Résistances physiques et magiques (en %)
      - Invincibility frames (iframes) après un coup
      - Mort et callback on_death
      - Historique des dégâts reçus (pour affichage de dégâts flottants)
      - Régénération de PV optionnelle
    """

    def __init__(
        self,
        hp_max          : int   = 100,
        phys_resistance : float = 0.0,   # % de réduction dégâts physiques (0-100)
        magic_resistance: float = 0.0,   # % de réduction dégâts magiques (0-100)
        iframes         : int   = PLAYER_IFRAMES,
        can_die         : bool  = True,
        regen_rate      : float = 0.0,   # PV regénérés par frame (0 = pas de regen)
        regen_delay     : int   = 300,   # Frames avant que la regen démarre
    ):
        super().__init__()

        # --- Stats ---
        self.hp_max           = hp_max
        self.hp               = hp_max
        self.phys_resistance  = min(100.0, max(0.0, phys_resistance))
        self.magic_resistance = min(100.0, max(0.0, magic_resistance))

        # --- Iframes ---
        self.iframes_max      = iframes
        self._iframe_timer    = 0         # Frames restantes d'invincibilité

        # --- Mort ---
        self.can_die          = can_die
        self.is_dead          = False

        # --- Régénération ---
        self.regen_rate       = regen_rate
        self.regen_delay      = regen_delay
        self._regen_timer     = 0         # Frames avant que la regen reprenne

        # --- Historique des dégâts (pour UI flottante) ---
        # Liste de dicts : {"amount": int, "type": str, "timer": int}
        self._damage_log      = []
        self._DAMAGE_LOG_TTL  = 90        # Frames avant suppression de l'entrée

        # --- Callbacks ---
        # Fonctions appelées sur certains événements — branchables de l'extérieur
        self.on_damaged_cb    = None   # fn(amount, damage_type, source)
        self.on_healed_cb     = None   # fn(amount)
        self.on_death_cb      = None   # fn(source)

    # ------------------------------------------------------------------
    # Propriétés
    # ------------------------------------------------------------------

    @property
    def hp_percent(self) -> float:
        """PV en pourcentage (0.0 → 1.0)."""
        return self.hp / self.hp_max if self.hp_max > 0 else 0.0

    @property
    def is_invincible(self) -> bool:
        return self._iframe_timer > 0

    @property
    def is_alive(self) -> bool:
        return not self.is_dead

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float):
        # Décompte des iframes
        if self._iframe_timer > 0:
            self._iframe_timer -= 1

        # Régénération de PV
        if self.regen_rate > 0 and not self.is_dead:
            if self._regen_timer > 0:
                self._regen_timer -= 1
            else:
                if self.hp < self.hp_max:
                    self.hp = min(self.hp_max, self.hp + self.regen_rate)

        # Nettoyage du log de dégâts
        self._damage_log = [
            entry for entry in self._damage_log
            if entry["timer"] > 0
        ]
        for entry in self._damage_log:
            entry["timer"] -= 1

    # ------------------------------------------------------------------
    # Prendre des dégâts
    # ------------------------------------------------------------------

    def take_damage(self, amount: int, damage_type: str = DamageType.PHYSICAL,
                    source=None, ignore_iframes: bool = False) -> int:
        """
        Inflige des dégâts à l'entité.

        amount       : dégâts bruts avant résistances
        damage_type  : DamageType.PHYSICAL / MAGICAL / POISON / TRUE
        source       : entité source des dégâts
        ignore_iframes : si True, inflige même pendant l'invincibilité

        Retourne les dégâts réels infligés (après résistances).
        Retourne 0 si invincible ou mort.
        """
        if self.is_dead:
            return 0
        if self.is_invincible and not ignore_iframes:
            return 0

        # Application des résistances
        real_damage = self._apply_resistance(amount, damage_type)
        real_damage = max(1, real_damage)   # Minimum 1 dégât toujours

        # Soustraction des PV
        self.hp = max(0, self.hp - real_damage)

        # Démarrage des iframes
        self._iframe_timer = self.iframes_max

        # Reset du timer de regen
        self._regen_timer = self.regen_delay

        # Log pour l'affichage
        self._damage_log.append({
            "amount" : real_damage,
            "type"   : damage_type,
            "timer"  : self._DAMAGE_LOG_TTL,
        })

        # Callback
        if self.on_damaged_cb:
            self.on_damaged_cb(real_damage, damage_type, source)

        # Notification à l'entité
        if self.owner:
            self.owner.on_hit(real_damage, source)

        # Mort
        if self.hp <= 0:
            self._trigger_death(source)

        return real_damage

    def _apply_resistance(self, amount: int, damage_type: str) -> int:
        """Applique les résistances et retourne les dégâts réduits."""
        if damage_type == DamageType.TRUE:
            return amount   # Dégâts vrais : aucune réduction

        if damage_type == DamageType.PHYSICAL:
            reduction = self.phys_resistance / 100.0
        elif damage_type in (DamageType.MAGICAL, DamageType.FIRE):
            reduction = self.magic_resistance / 100.0
        elif damage_type == DamageType.POISON:
            reduction = self.magic_resistance / 200.0   # Résistance partielle
        else:
            reduction = 0.0

        return int(amount * (1.0 - reduction))

    # ------------------------------------------------------------------
    # Soins
    # ------------------------------------------------------------------

    def heal(self, amount: int, overheal: bool = False) -> int:
        """
        Soigne l'entité.
        overheal : si True, peut dépasser le hp_max.
        Retourne les PV réellement récupérés.
        """
        if self.is_dead:
            return 0

        old_hp    = self.hp
        cap       = self.hp_max * 1.5 if overheal else self.hp_max
        self.hp   = min(cap, self.hp + amount)
        healed    = int(self.hp - old_hp)

        if healed > 0 and self.on_healed_cb:
            self.on_healed_cb(healed)

        return healed

    def full_heal(self):
        """Remet les PV au maximum."""
        self.hp      = self.hp_max
        self.is_dead = False

    # ------------------------------------------------------------------
    # Parry / Invincibilité
    # ------------------------------------------------------------------

    def grant_iframes(self, duration: int = None):
        """
        Accorde des frames d'invincibilité manuellement.
        Utile pour le dash, un parry réussi, une cutscene...
        """
        self._iframe_timer = duration if duration is not None else self.iframes_max

    def set_invincible(self, permanent: bool = True):
        """
        Invincibilité permanente (ex: pendant une cutscene).
        permanent=False remet les iframes à 0.
        """
        self._iframe_timer = 999999 if permanent else 0

    # ------------------------------------------------------------------
    # Mort
    # ------------------------------------------------------------------

    def _trigger_death(self, source=None):
        if not self.can_die:
            self.hp = 1   # Entité immortelle — reste à 1 PV minimum
            return

        self.hp      = 0
        self.is_dead = True

        if self.on_death_cb:
            self.on_death_cb(source)

        if self.owner:
            self.owner.on_death()

    def instant_kill(self, source=None):
        """Tue immédiatement l'entité (ignore les résistances et iframes)."""
        self.hp = 0
        self._trigger_death(source)

    # ------------------------------------------------------------------
    # Modification des stats (équipement / level up)
    # ------------------------------------------------------------------

    def set_max_hp(self, new_max: int, heal_diff: bool = True):
        """
        Modifie le HP max.
        heal_diff : si True, augmente aussi les PV actuels de la différence.
        """
        diff        = new_max - self.hp_max
        self.hp_max = new_max
        if heal_diff and diff > 0:
            self.hp = min(self.hp_max, self.hp + diff)

    def set_resistance(self, phys: float = None, magic: float = None):
        """Met à jour les résistances (valeurs en %, 0-100)."""
        if phys  is not None:
            self.phys_resistance  = min(100.0, max(0.0, phys))
        if magic is not None:
            self.magic_resistance = min(100.0, max(0.0, magic))

    # ------------------------------------------------------------------
    # Accesseurs pour l'UI
    # ------------------------------------------------------------------

    def get_recent_damage(self) -> list:
        """
        Retourne la liste des dégâts récents pour l'affichage flottant.
        Format : [{"amount": int, "type": str, "timer": int}, ...]
        """
        return list(self._damage_log)

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self):
        return (
            f"<HealthComponent hp={self.hp}/{self.hp_max} "
            f"dead={self.is_dead} iframes={self._iframe_timer}>"
        )