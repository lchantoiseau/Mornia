# =============================================================================
#  MORNIA — entities/base_entity.py
#  Classe abstraite dont héritent toutes les entités du jeu.
#  (Joueur, ennemis, PNJ, projectiles, objets interactifs...)
#
#  Principe : une entité EST une coquille vide.
#  Ce sont ses COMPOSANTS qui lui donnent des comportements.
#  → Entity.add_component(PhysicsComponent(self))
#  → Entity.add_component(HealthComponent(self, hp=100))
# =============================================================================

import pygame
from abc import ABC, abstractmethod


class Entity(ABC):
    """
    Classe de base abstraite pour toutes les entités du jeu.

    Chaque entité possède :
      - Une position (rect pygame)
      - Un dictionnaire de composants
      - Un état courant (géré par sa propre StateMachine ou une string simple)
      - Des flags de cycle de vie (active, visible, pending_destroy)

    Méthodes à implémenter obligatoirement dans les sous-classes :
      - update(dt)
      - draw(surface, camera_offset)
    """

    # Compteur global pour donner un ID unique à chaque entité
    _id_counter = 0

    def __init__(self, x: float, y: float, w: int, h: int):
        """
        x, y : position initiale (coin haut-gauche, en pixels internes)
        w, h : dimensions du rect de collision (hitbox)
        """
        # ID unique
        Entity._id_counter += 1
        self.id = Entity._id_counter

        # Position et dimensions
        # On sépare position flottante (précision physique)
        # et rect entier (collisions pygame)
        self.x      = float(x)
        self.y      = float(y)
        self.w      = w
        self.h      = h
        self.rect   = pygame.Rect(int(x), int(y), w, h)

        # Vélocité (gérée par PhysicsComponent mais accessible partout)
        self.vel_x  = 0.0
        self.vel_y  = 0.0

        # Direction regardée : +1 = droite, -1 = gauche
        self.facing = 1

        # --- Composants ---
        # { nom_str : instance_composant }
        self._components = {}

        # --- Flags de cycle de vie ---
        self.active          = True    # Update et draw actifs
        self.visible         = True    # Draw actif (même si pas update)
        self.pending_destroy = False   # Marqué pour suppression en fin de frame

        # --- Tags ---
        # Ensemble de strings libres pour identifier le type d'entité
        # ex: {"enemy", "melee"} ou {"player"} ou {"projectile", "fire"}
        self.tags = set()

        # --- Groupe d'appartenance (référence au Level courant) ---
        self.level = None   # Assigné par Level.add_entity()

    # ------------------------------------------------------------------
    # Composants
    # ------------------------------------------------------------------

    def add_component(self, component):
        """
        Ajoute un composant à l'entité.
        Le composant est indexé par le nom de sa classe.
        Un seul composant par type autorisé (remplace l'ancien si existant).

        Usage :
            entity.add_component(PhysicsComponent(entity))
            entity.add_component(HealthComponent(entity, hp=80))
        """
        name = type(component).__name__
        component.owner = self
        self._components[name] = component
        component.on_attach()
        return self   # Chaînable : entity.add_component(A).add_component(B)

    def get_component(self, component_class):
        """
        Retourne le composant du type demandé, ou None s'il n'existe pas.

        Usage :
            physics = entity.get_component(PhysicsComponent)
            if physics:
                physics.apply_force(0, -5)
        """
        return self._components.get(component_class.__name__)

    def has_component(self, component_class) -> bool:
        """Retourne True si l'entité possède ce type de composant."""
        return component_class.__name__ in self._components

    def get_component_by_name(self, name: str):
        """
        Retourne un composant par son nom de classe (string).
        Utile quand on veut éviter les imports circulaires.
        ex: entity.get_component_by_name("PhysicsComponent")
        """
        return self._components.get(name)

    def remove_component(self, component_class):
        """Retire un composant de l'entité et appelle on_detach()."""
        name = component_class.__name__
        if name in self._components:
            self._components[name].on_detach()
            del self._components[name]

    def _update_components(self, dt):
        """Appelle update(dt) sur tous les composants actifs."""
        for component in self._components.values():
            if component.enabled:
                component.update(dt)

    # ------------------------------------------------------------------
    # Méthodes abstraites — à implémenter dans chaque entité concrète
    # ------------------------------------------------------------------

    @abstractmethod
    def update(self, dt: float):
        """
        Logique de mise à jour spécifique à l'entité.
        Doit appeler self._update_components(dt) pour mettre à jour
        les composants automatiquement.
        """
        pass

    @abstractmethod
    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        """
        Rendu de l'entité.
        camera_offset : (offset_x, offset_y) fourni par Camera.
        """
        pass

    # ------------------------------------------------------------------
    # Synchronisation position ↔ rect
    # ------------------------------------------------------------------

    def sync_rect(self):
        """
        Synchronise le rect pygame avec les coordonnées flottantes x/y.
        À appeler après chaque déplacement physique.
        """
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def set_position(self, x: float, y: float):
        """Téléporte l'entité à une position donnée."""
        self.x = x
        self.y = y
        self.sync_rect()

    def get_center(self) -> tuple:
        """Retourne le centre de l'entité (float)."""
        return (self.x + self.w / 2, self.y + self.h / 2)

    def get_feet(self) -> tuple:
        """Retourne le point bas-centre de l'entité (utile pour la physique sol)."""
        return (self.x + self.w / 2, self.y + self.h)

    # ------------------------------------------------------------------
    # Gestion des tags
    # ------------------------------------------------------------------

    def add_tag(self, *tags: str):
        """Ajoute un ou plusieurs tags. ex: entity.add_tag("enemy", "boss")"""
        for tag in tags:
            self.tags.add(tag)
        return self

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def is_player(self)    -> bool: return "player"     in self.tags
    def is_enemy(self)     -> bool: return "enemy"      in self.tags
    def is_projectile(self)-> bool: return "projectile" in self.tags
    def is_npc(self)       -> bool: return "npc"        in self.tags

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def destroy(self):
        """Marque l'entité pour suppression à la fin de la frame."""
        self.pending_destroy = True

    def on_death(self):
        """
        Appelé quand HealthComponent atteint 0.
        Override dans les sous-classes pour déclencher animations, drops...
        """
        self.destroy()

    def on_hit(self, damage: int, source):
        """
        Appelé quand l'entité reçoit un coup.
        source : l'entité qui inflige les dégâts.
        Override pour des réactions spécifiques (knockback, sons...).
        """
        pass

    def on_level_enter(self):
        """Appelé quand l'entité est ajoutée à un Level."""
        pass

    def on_level_exit(self):
        """Appelé quand l'entité est retirée d'un Level."""
        pass

    # ------------------------------------------------------------------
    # Distances et overlaps utilitaires
    # ------------------------------------------------------------------

    def distance_to(self, other) -> float:
        """Distance euclidienne entre les centres de deux entités."""
        cx1, cy1 = self.get_center()
        cx2, cy2 = other.get_center()
        return ((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2) ** 0.5

    def is_overlapping(self, other) -> bool:
        """True si les rects des deux entités se chevauchent."""
        return self.rect.colliderect(other.rect)

    def direction_to(self, other) -> int:
        """Retourne +1 si other est à droite, -1 s'il est à gauche."""
        return 1 if other.x >= self.x else -1

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def draw_debug(self, surface: pygame.Surface, camera_offset: tuple):
        """
        Dessine la hitbox et les infos de debug.
        Appelé depuis RenderSystem quand le mode debug est actif.
        """
        ox, oy = camera_offset
        debug_rect = pygame.Rect(
            self.rect.x - ox, self.rect.y - oy,
            self.rect.w,      self.rect.h
        )
        pygame.draw.rect(surface, (0, 255, 0), debug_rect, 1)

        # Centre
        cx = debug_rect.centerx
        cy = debug_rect.centery
        pygame.draw.circle(surface, (255, 0, 0), (cx, cy), 1)

    def __repr__(self):
        return (f"<{self.__class__.__name__} id={self.id} "
                f"pos=({self.x:.1f},{self.y:.1f}) "
                f"tags={self.tags}>")


# =============================================================================
#  COMPONENT — classe de base pour tous les composants
# =============================================================================

class Component:
    """
    Classe de base pour tous les composants attachables à une Entity.

    Chaque composant concret hérite de Component et implémente
    les méthodes dont il a besoin.
    """

    def __init__(self):
        self.owner   = None    # Assigné par Entity.add_component()
        self.enabled = True    # Si False, update() n'est pas appelé

    def on_attach(self):
        """Appelé une fois quand le composant est attaché à l'entité."""
        pass

    def on_detach(self):
        """Appelé quand le composant est retiré de l'entité."""
        pass

    def update(self, dt: float):
        """Logique de mise à jour, appelée chaque frame si enabled."""
        pass

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def __repr__(self):
        owner_name = self.owner.__class__.__name__ if self.owner else "None"
        return f"<{self.__class__.__name__} owner={owner_name} enabled={self.enabled}>"