# Mornia

## Description du Projet

Mornia est un jeu vidéo développé en Python utilisant la bibliothèque Pygame. Il s'agit d'un jeu d'aventure/action en 2D avec des éléments de plateforme, de combat et d'exploration. Le jeu utilise une architecture modulaire basée sur des composants et des systèmes pour une meilleure maintenabilité et extensibilité.

*[À compléter : description détaillée du gameplay, objectifs, mécaniques, etc.]*

## Architecture Générale

Le projet suit une architecture orientée objet modulaire, inspirée des principes de l'ECS (Entity-Component-System) et du pattern State Machine. L'architecture est organisée autour des concepts suivants :

- **Entités** : Objets du jeu (joueur, ennemis, etc.) composés de composants.
- **Composants** : Fonctionnalités réutilisables (physique, santé, animation, etc.).
- **Systèmes** : Logique globale (rendu, collisions, HUD, etc.).
- **États** : Gestion des différents modes du jeu via des machines à états finis.
- **Monde** : Gestion des niveaux, cartes et caméra.

Le rendu utilise une résolution interne basse (320x180) upscalée à 1280x720 pour un effet pixel art.

## Structure du Code

### Fichiers Racine

- **`main.py`** : Point d'entrée du jeu. Initialise le jeu, charge les assets et lance la boucle principale.
- **`settings.py`** : Contient toutes les constantes globales (dimensions fenêtre, couleurs, paramètres physiques, stats joueur).

### Dossier `assets/`

Contient toutes les ressources du jeu :
- **`maps/`** : Fichiers de cartes/niveaux.
- **`sounds/`** : Effets sonores et musique.
- **`sprites/`** : Images des personnages, ennemis et objets.
- **`tilesets/`** : Tuiles pour construire les niveaux.

### Dossier `components/`

Composants réutilisables qui donnent des comportements aux entités :
- **`__init__.py`** : Module d'initialisation.
- **`animation.py`** : Gestion des animations de sprites.
- **`combat.py`** : Système de combat (attaques, dégâts, parades).
- **`health.py`** : Gestion de la santé, mana et stamina.
- **`input.py`** : Traitement des entrées utilisateur.
- **`physics.py`** : Physique du jeu (gravité, vélocité, collisions).

### Dossier `core/`

Noyau du jeu, logique principale :
- **`__init__.py`** : Module d'initialisation.
- **`event_handler.py`** : Gestion des événements Pygame.
- **`game.py`** : Classe principale Game, gère la fenêtre, boucle et FSM globale.
- **`playing_state.py`** : États de jeu (menu principal, gameplay, pause).
- **`state_machine.py`** : Implémentation générique de machine à états finis.

### Dossier `data/`

Gestion des données et ressources :
- **`__init__.py`** : Module d'initialisation.
- **`asset_loader.py`** : Chargement et gestion des assets (singleton).
- **`save_manager.py`** : Sauvegarde et chargement de la progression.
- **`sound_manager.py`** : Gestion audio.

### Dossier `entities/`

Entités du jeu :
- **`__init__.py`** : Module d'initialisation.
- **`base_entity.py`** : Classe abstraite Entity, base de toutes les entités.
- **`enemy.py`** : Classe de base pour les ennemis.
- **`player.py`** : Classe Player, entité contrôlée par le joueur.
- **`enemies/`** : Sous-dossier pour les types spécifiques d'ennemis :
  - **`__init__.py`** : Module d'initialisation.
  - **`melee_enemy.py`** : Ennemis au corps à corps.
  - **`ranged_enemy.py`** : Ennemis à distance.

### Dossier `systems/`

Systèmes globaux du jeu :
- **`__init__.py`** : Module d'initialisation.
- **`collision_system.py`** : Détection et résolution des collisions.
- **`hud.py`** : Interface utilisateur (barres de vie, mana, etc.).
- **`render_system.py`** : Système de rendu (vide pour le moment).

### Dossier `ui/`

Interface utilisateur :
- **`__init__.py`** : Module d'initialisation.
- **`menu.py`** : Menus principaux.
- **`pause_menu.py`** : Menu de pause.
- **`ui_element.py`** : Éléments d'interface réutilisables.

### Dossier `world/`

Gestion du monde de jeu :
- **`__init__.py`** : Module d'initialisation.
- **`camera.py`** : Caméra pour le suivi du joueur.
- **`level.py`** : Classe Level, orchestre tilemap, caméra et entités.
- **`room.py`** : Gestion des salles/pièces.
- **`tilemap.py`** : Carte en tuiles (tiles).

## Dépendances

- **Pygame** : Bibliothèque principale pour le développement du jeu.

*[À compléter : versions spécifiques, autres dépendances si nécessaire]*

## Installation et Lancement

1. Installer Python 3.x
2. Installer Pygame : `pip install pygame`
3. Cloner le repository
4. Lancer le jeu : `python main.py`

*[À compléter : instructions détaillées, configuration, etc.]*

## Contrôles

*[À compléter : mapping des touches, commandes]*

## Fonctionnalités Implémentées

- Architecture ECS modulaire
- Système de physique avec gravité et collisions
- Gestion des états du joueur (idle, walk, attack, dash)
- Système de santé et combat de base
- Caméra et niveaux en tuiles
- Interface utilisateur de base

*[À compléter : liste détaillée des features]*

## Développement

Le projet utilise une approche modulaire pour faciliter l'ajout de nouvelles fonctionnalités. Chaque composant est indépendant et peut être réutilisé. La machine à états finis permet une gestion claire des différents modes du jeu.

*[À compléter : conventions de code, workflow de développement, etc.]*

## Licence

*[À compléter]*

## Auteur

Moi le goat. 
