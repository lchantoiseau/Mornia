# =============================================================================
#  MORNIA — entities/player.py
#  Le joueur — assemble tous les composants et orchestre leur interaction.
#
#  Composants utilisés :
#    - InputComponent    → intentions du joueur
#    - PhysicsComponent  → déplacement, gravité, dash
#    - HealthComponent   → PV, iframes, mort
#    - AnimationComponent→ sprites animés
#    - CombatComponent   → hitboxes, dégâts, parry
# =============================================================================

import pygame
from entities.base_entity   import Entity
from components.physics     import PhysicsComponent
from components.health      import HealthComponent, DamageType
from components.animation   import AnimationComponent, Animation
from components.input       import InputComponent
from components.combat      import CombatComponent, AttackData
from core.state_machine     import StateMachine, State
from settings import (
    PLAYER_BASE_HP, PLAYER_BASE_MANA, PLAYER_BASE_STAMINA,
    PLAYER_BASE_PHYS_RES, PLAYER_BASE_MAGIC_RES, PLAYER_BASE_WEIGHT_CAP,
    PLAYER_WALK_SPEED, PLAYER_RUN_SPEED, PLAYER_JUMP_FORCE,
    PLAYER_DASH_SPEED, PLAYER_DASH_DURATION, PLAYER_DASH_COOLDOWN,
    PLAYER_IFRAMES, PLAYER_PARRY_WINDOW, PLAYER_PARRY_COOLDOWN,
    STAMINA_COST_DASH, STAMINA_COST_ATTACK, STAMINA_COST_PARRY,
    STAMINA_REGEN_RATE, STAMINA_REGEN_DELAY,
    PlayerState,
)


# =============================================================================
#  PLACEHOLDER VISUEL
# =============================================================================
def _make_placeholder_frames(w, h, color, count=1):
    """Génère des frames colorées pour tester sans sprites."""
    frames = []
    for _ in range(count):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill(color)
        frames.append(surf)
    return frames


# =============================================================================
#  ETATS DU JOUEUR
# =============================================================================

class _PlayerState(State):
    """Base pour tous les états du joueur."""
    def __init__(self, player):
        super().__init__(owner=player)
        self.player = player

    @property
    def physics(self): return self.player.physics
    @property
    def anim(self):    return self.player.anim
    @property
    def combat(self):  return self.player.combat
    @property
    def inp(self):     return self.player.inp


class IdleState(_PlayerState):
    def on_enter(self):
        self.anim.play("idle")
        self.physics.stop_x()

    def update(self, dt):
        inp = self.inp
        if inp.wants_dash and self.player.has_stamina(STAMINA_COST_DASH):
            self.player.fsm.change(PlayerState.DASH)
        elif inp.wants_attack and self.player.has_stamina(STAMINA_COST_ATTACK):
            self.player.fsm.change(PlayerState.ATTACK)
        elif inp.wants_parry and self.player.has_stamina(STAMINA_COST_PARRY):
            self.player.fsm.change(PlayerState.PARRY)
        elif inp.wants_cast:
            self.player.fsm.change(PlayerState.CAST)
        elif inp.wants_jump:
            self.player.fsm.change(PlayerState.JUMP)
        elif inp.move_x != 0:
            self.player.fsm.change(PlayerState.WALK)


class WalkState(_PlayerState):
    def on_enter(self):
        self.anim.play("walk")

    def update(self, dt):
        inp = self.inp
        p   = self.physics

        if inp.wants_dash and self.player.has_stamina(STAMINA_COST_DASH):
            self.player.fsm.change(PlayerState.DASH)
            return
        if inp.wants_attack and self.player.has_stamina(STAMINA_COST_ATTACK):
            self.player.fsm.change(PlayerState.ATTACK)
            return
        if inp.wants_parry and self.player.has_stamina(STAMINA_COST_PARRY):
            self.player.fsm.change(PlayerState.PARRY)
            return
        if inp.wants_jump:
            self.player.fsm.change(PlayerState.JUMP)
            return
        if inp.move_x == 0:
            self.player.fsm.change(PlayerState.IDLE)
            return
        if not p.on_ground:
            self.player.fsm.change(PlayerState.FALL)
            return

        speed = PLAYER_RUN_SPEED if abs(inp.move_x) > 0.8 else PLAYER_WALK_SPEED
        p.move(int(inp.move_x), speed)
        self.player.facing = int(inp.move_x)
        self.anim.update_facing(self.player.facing)


class JumpState(_PlayerState):
    def on_enter(self):
        self.anim.play("jump")
        self.physics.jump()

    def update(self, dt):
        inp = self.inp
        p   = self.physics

        if inp.jump_released:
            p.jump_cut()

        if inp.wants_dash and self.player.has_stamina(STAMINA_COST_DASH):
            self.player.fsm.change(PlayerState.DASH)
            return
        if inp.wants_attack and self.player.has_stamina(STAMINA_COST_ATTACK):
            self.player.fsm.change(PlayerState.ATTACK)
            return

        if inp.move_x != 0:
            p.move(int(inp.move_x), PLAYER_WALK_SPEED * 0.85)
            self.player.facing = int(inp.move_x)
            self.anim.update_facing(self.player.facing)

        if p.on_ground:
            self.player.fsm.change(PlayerState.IDLE)
        elif p.is_falling():
            self.player.fsm.change(PlayerState.FALL)


class FallState(_PlayerState):
    def on_enter(self):
        self.anim.play("fall")

    def update(self, dt):
        inp = self.inp
        p   = self.physics

        if inp.wants_dash and self.player.has_stamina(STAMINA_COST_DASH):
            self.player.fsm.change(PlayerState.DASH)
            return
        if inp.wants_attack and self.player.has_stamina(STAMINA_COST_ATTACK):
            self.player.fsm.change(PlayerState.ATTACK)
            return
        if inp.wants_jump:
            p.jump()

        if inp.move_x != 0:
            p.move(int(inp.move_x), PLAYER_WALK_SPEED * 0.85)
            self.player.facing = int(inp.move_x)
            self.anim.update_facing(self.player.facing)

        if p.on_ground:
            self.player.fsm.change(PlayerState.IDLE)


class DashState(_PlayerState):
    def on_enter(self):
        self.anim.play("dash", force=True)
        self.physics.dash(self.player.facing)
        self.player.use_stamina(STAMINA_COST_DASH)
        health = self.player.get_component(HealthComponent)
        if health:
            health.grant_iframes(PLAYER_DASH_DURATION + 5)

    def update(self, dt):
        if not self.physics.is_dashing:
            if self.physics.on_ground:
                self.player.fsm.change(PlayerState.IDLE)
            else:
                self.player.fsm.change(PlayerState.FALL)


class AttackState(_PlayerState):
    def on_enter(self):
        self.anim.play("attack", force=True)
        self.combat.start_attack("light")
        self.player.use_stamina(STAMINA_COST_ATTACK)
        self.anim.on_finish_cb = self._on_anim_finish

    def on_exit(self):
        self.anim.on_finish_cb = None
        self.combat.end_attack()

    def _on_anim_finish(self, anim_name):
        self.combat.end_attack()
        self.player.fsm.change(PlayerState.IDLE)

    def update(self, dt):
        inp = self.inp
        if inp.move_x != 0:
            self.physics.move(int(inp.move_x), PLAYER_WALK_SPEED * 0.3)
            self.player.facing = int(inp.move_x)
            self.anim.update_facing(self.player.facing)

        if self.player.level:
            enemies = self.player.level.get_entities_with_tag("enemy")
            self.combat.check_hits(enemies)


class ParryState(_PlayerState):
    def on_enter(self):
        self.anim.play("parry", force=True)
        self.combat.start_parry()
        self.player.use_stamina(STAMINA_COST_PARRY)
        self._timer = PLAYER_PARRY_WINDOW + 10

    def update(self, dt):
        self._timer -= 1
        if self._timer <= 0:
            self.player.fsm.change(PlayerState.IDLE)

    def on_exit(self):
        self.combat.end_parry()


class ParrySuccessState(_PlayerState):
    def on_enter(self):
        self.anim.play("parry_success", force=True)
        self._timer = 30

    def update(self, dt):
        if self.inp.wants_attack:
            self.player.fsm.change(PlayerState.ATTACK)
            return
        self._timer -= 1
        if self._timer <= 0:
            self.player.fsm.change(PlayerState.IDLE)


class HurtState(_PlayerState):
    def on_enter(self):
        self.anim.play("hurt", force=True)
        self._timer = 20

    def update(self, dt):
        self._timer -= 1
        if self._timer <= 0:
            if self.physics.on_ground:
                self.player.fsm.change(PlayerState.IDLE)
            else:
                self.player.fsm.change(PlayerState.FALL)


class DeadState(_PlayerState):
    def on_enter(self):
        self.anim.play("dead", force=True)
        self.inp.lock()
        self.physics.stop_x()

    def update(self, dt):
        pass


class CastState(_PlayerState):
    def on_enter(self):
        self.anim.play("cast", force=True)
        self._timer = 25

    def update(self, dt):
        self._timer -= 1
        if self._timer <= 0:
            self.player.fsm.change(PlayerState.IDLE)


# =============================================================================
#  PLAYER
# =============================================================================

class Player(Entity):
    """
    Le joueur de Mornia.

    Stats RPG : level, force, dexterity, intelligence, endurance
    Ressources : hp, mana, stamina
    Composants  : input, physics, health, animation, combat
    FSM interne : orchestre les états (idle, walk, jump, attack, dash...)
    """

    def __init__(self, x: float, y: float):
        W, H = 12, 22
        super().__init__(x, y, W, H)
        self.add_tag("player")

        # ------------------------------------------------------------------
        # Stats RPG
        # ------------------------------------------------------------------
        self.player_level  = 1
        self.strength      = 10
        self.dexterity     = 10
        self.intelligence  = 10
        self.endurance     = 10

        # Ressources
        self.mana          = PLAYER_BASE_MANA
        self.mana_max      = PLAYER_BASE_MANA
        self.stamina       = float(PLAYER_BASE_STAMINA)
        self.stamina_max   = float(PLAYER_BASE_STAMINA)
        self._stamina_regen_timer = 0

        self.weapon        = None

        # ------------------------------------------------------------------
        # Composants
        # ------------------------------------------------------------------
        self._setup_components()

        # ------------------------------------------------------------------
        # FSM interne
        # ------------------------------------------------------------------
        self.fsm = StateMachine(self)
        self._setup_fsm()
        self.fsm.change(PlayerState.IDLE)

    # ------------------------------------------------------------------
    # Raccourcis composants
    # ------------------------------------------------------------------
    @property
    def physics(self): return self.get_component(PhysicsComponent)
    @property
    def health(self):  return self.get_component(HealthComponent)
    @property
    def anim(self):    return self.get_component(AnimationComponent)
    @property
    def inp(self):     return self.get_component(InputComponent)
    @property
    def combat(self):  return self.get_component(CombatComponent)

    # ------------------------------------------------------------------
    # Setup composants
    # ------------------------------------------------------------------

    def _setup_components(self):
        self.add_component(PhysicsComponent(
            has_gravity   = True,
            can_jump      = True,
            can_dash      = True,
            jump_force    = PLAYER_JUMP_FORCE,
            max_jumps     = 1,
            dash_speed    = PLAYER_DASH_SPEED,
            dash_duration = PLAYER_DASH_DURATION,
            dash_cooldown = PLAYER_DASH_COOLDOWN,
        ))

        hp_comp = HealthComponent(
            hp_max           = PLAYER_BASE_HP,
            phys_resistance  = PLAYER_BASE_PHYS_RES,
            magic_resistance = PLAYER_BASE_MAGIC_RES,
            iframes          = PLAYER_IFRAMES,
        )
        hp_comp.on_damaged_cb = self._on_damaged
        hp_comp.on_death_cb   = self._on_death
        self.add_component(hp_comp)

        anim = AnimationComponent(default_anim="idle")
        self._setup_placeholder_animations(anim)
        self.add_component(anim)

        inp = InputComponent()
        self.add_component(inp)

        combat = CombatComponent(
            parry_window   = PLAYER_PARRY_WINDOW,
            parry_cooldown = PLAYER_PARRY_COOLDOWN,
        )
        combat.strength  = self.strength
        combat.dexterity = self.dexterity
        self._setup_attacks(combat)
        combat.on_hit_landed_cb    = self._on_hit_landed
        combat.on_parry_success_cb = self._on_parry_success
        self.add_component(combat)

    def _setup_placeholder_animations(self, anim: AnimationComponent):
        W, H = self.w, self.h

        def make(color, count=4, rate=8, loop=True):
            return Animation(_make_placeholder_frames(W, H, color, count), rate, loop)

        anim.add("idle",          make((80,  60, 120), 4, 10))
        anim.add("walk",          make((60,  80, 120), 6,  6))
        anim.add("run",           make((40, 100, 160), 8,  4))
        anim.add("jump",          make((80, 120,  80), 2,  8))
        anim.add("fall",          make((80,  80,  40), 2,  8))
        anim.add("dash",          make((40, 160, 200), 3,  3, loop=False))
        anim.add("attack",        make((200, 80,  40), 5,  4, loop=False))
        anim.add("parry",         make((200,180,  40), 3,  4, loop=False))
        anim.add("parry_success", make((255,220,   0), 4,  4, loop=False))
        anim.add("hurt",          make((200, 40,  40), 3,  5, loop=False))
        anim.add("dead",          make(( 60, 20,  20), 4,  8, loop=False))
        anim.add("cast",          make((100, 40, 200), 4,  5, loop=False))

    def _setup_attacks(self, combat: CombatComponent):
        combat.add_attack("light", AttackData(
            name="light", offset_x=14, offset_y=0,
            width=18, height=16,
            damage_min=8, damage_max=14,
            knockback_x=2.5, knockback_y=1.5,
            active_start=1, active_end=3,
            stat_scaling="dexterity",
        ))
        combat.add_attack("heavy", AttackData(
            name="heavy", offset_x=18, offset_y=2,
            width=24, height=20,
            damage_min=20, damage_max=35,
            knockback_x=5.0, knockback_y=3.0,
            active_start=3, active_end=5,
            stat_scaling="strength", stun_frames=20,
        ))

    def _setup_fsm(self):
        self.fsm.add_states({
            PlayerState.IDLE         : IdleState(self),
            PlayerState.WALK         : WalkState(self),
            PlayerState.RUN          : WalkState(self),
            PlayerState.JUMP         : JumpState(self),
            PlayerState.FALL         : FallState(self),
            PlayerState.DASH         : DashState(self),
            PlayerState.ATTACK       : AttackState(self),
            PlayerState.PARRY        : ParryState(self),
            PlayerState.PARRY_SUCCESS: ParrySuccessState(self),
            PlayerState.HURT         : HurtState(self),
            PlayerState.DEAD         : DeadState(self),
            PlayerState.CAST         : CastState(self),
        })

    # ------------------------------------------------------------------
    # Injection de dépendances (appelée par Level)
    # ------------------------------------------------------------------

    def setup(self, event_handler, tilemap, level):
        self.inp.set_event_handler(event_handler)
        self.physics.set_tilemap(tilemap)
        self.level = level

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float):
        if not self.active:
            return

        self.inp.update(dt)
        self._update_stamina(dt)
        self._update_components(dt)
        self.fsm.update(dt)
        self.anim.update_facing(self.facing)

        if self.inp.wants_pause and self.level:
            self.level.game.pause()

    # ------------------------------------------------------------------
    # Stamina
    # ------------------------------------------------------------------

    def _update_stamina(self, dt: float):
        if self._stamina_regen_timer > 0:
            self._stamina_regen_timer -= 1
        else:
            self.stamina = min(self.stamina_max,
                               self.stamina + STAMINA_REGEN_RATE)

    def has_stamina(self, cost: float) -> bool:
        return self.stamina >= cost

    def use_stamina(self, amount: float):
        self.stamina = max(0.0, self.stamina - amount)
        self._stamina_regen_timer = STAMINA_REGEN_DELAY

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        if not self.visible:
            return

        ox, oy = camera_offset
        frame  = self.anim.current_frame

        # Clignotement pendant les iframes
        health = self.health
        if health and health.is_invincible:
            if int(health._iframe_timer / 4) % 2 == 1:
                return

        surface.blit(frame, (self.rect.x - ox, self.rect.y - oy))

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_damaged(self, amount: int, damage_type: str, source):
        if not self.health.is_dead:
            self.fsm.change(PlayerState.HURT, force=True)

    def _on_death(self, source):
        self.fsm.change(PlayerState.DEAD, force=True)
        if self.level:
            self.level.game.game_over()

    def _on_hit_landed(self, target, damage: int, attack_data):
        pass   # TODO : effets visuels, son, freeze frame

    def _on_parry_success(self, attacker):
        self.fsm.change(PlayerState.PARRY_SUCCESS, force=True)

    # ------------------------------------------------------------------
    # Mort / résurrection
    # ------------------------------------------------------------------

    def on_death(self):
        pass   # Géré par _on_death

    def respawn(self, x: float, y: float):
        self.set_position(x, y)
        self.vel_x = 0.0
        self.vel_y = 0.0
        if self.health:
            self.health.full_heal()
        self.stamina = self.stamina_max
        self.mana    = self.mana_max
        self.inp.unlock()
        self.fsm.change(PlayerState.IDLE, force=True)

    # ------------------------------------------------------------------
    # Level up
    # ------------------------------------------------------------------

    def level_up(self, stat: str, points: int = 1):
        from settings import INT_MANA_SCALE
        if stat == "strength":
            self.strength    += points
            self.combat.strength = self.strength
        elif stat == "dexterity":
            self.dexterity   += points
            self.combat.dexterity = self.dexterity
        elif stat == "intelligence":
            self.intelligence += points
            self.mana_max     += INT_MANA_SCALE * points
            self.mana          = self.mana_max
        elif stat == "endurance":
            self.endurance    += points
        self.player_level += 1

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def draw_debug(self, surface: pygame.Surface, camera_offset: tuple):
        super().draw_debug(surface, camera_offset)
        if self.combat:
            self.combat.draw_debug(surface, camera_offset)

    def get_status(self) -> dict:
        h = self.health
        return {
            "level"  : self.player_level,
            "state"  : self.fsm.current_name,
            "hp"     : f"{h.hp:.0f}/{h.hp_max}" if h else "?",
            "stamina": f"{self.stamina:.0f}/{self.stamina_max}",
            "mana"   : f"{self.mana:.0f}/{self.mana_max}",
            "pos"    : f"({self.x:.1f}, {self.y:.1f})",
            "vel"    : f"({self.vel_x:.2f}, {self.vel_y:.2f})",
            "ground" : self.physics.on_ground if self.physics else "?",
        }