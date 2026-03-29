# HackaHunt

HackaHunt est un bot Discord complet conçu pour automatiser la découverte de hackathons et faciliter la création d'équipes (matchmaking) au sein de votre communauté Discord. Il surveille en permanence de nombreuses plateformes de compétition majeures et centralise leurs annonces directement sur votre serveur Discord sans submerger les utilisateurs.

## Contexte du Projet

Avec la multiplication des plateformes de compétitions informatiques et d'innovation (hackathons, datathons, concours de code), il est devenu difficile de rester à jour et de trouver des coéquipiers. HackaHunt est né de la volonté de centraliser ces opportunités pour une communauté de développeurs sur Discord, tout en automatisant la fastidieuse étape de recherche d'informations et de constitution d'équipes.

## Objectif

L'objectif de HackaHunt est de :
1. **Centraliser l'information** : Récupérer automatiquement les hackathons pertinents depuis de multiples sources pour les afficher dans un seul canal.
2. **Filtrer le bruit** : Ne garder que les hackathons de qualité, en excluant les événements passés ou ne correspondant pas aux thématiques du serveur.
3. **Faciliter la collaboration** : Permettre aux membres du serveur Discord de trouver rapidement des coéquipiers en réagissant simplement aux annonces.

## Stack Technologique

- **Langage** : Python 3.9+
- **Bot/API Discord** : `discord.py` (gestion du bot, des commandes slash et des événements)
- **Base de données** : SQLite (gestion légère et autonome via `sqlite3` et requêtes SQL en Python)
- **Scraping & Requêtes** : `requests` (Appels API JSON), `BeautifulSoup` (`bs4`), outils de parsing HTML personnalisés
- **Gestion du Temps et des Dates** : `dateparser` (gestion intelligente et flexible des dates d'échéance)
- **Environnement** : `python-dotenv` (pour la gestion sécurisée des variables d'environnement)

## Fonctionnalités Principales

- **Scraping Multi-Plateformes** : Collecte automatisée de données utilisant des APIs officielles et des analyseurs HTML résilients. Les plateformes prises en charge incluent :
  - Devpost (via API JSON)
  - Major League Hacking / MLH (Analyseur CSS Tailwind personnalisé)
  - Zindi Africa (via API JSON)
  - DrivenData
  - Kaggle
  - D'autres sources diverses (Eventbrite, ChallengeData, Challengerocket, etc.)
- **Filtrage et Notation Intelligents** : Filtre automatiquement les thèmes non pertinents et classe les hackathons selon des critères de qualité prédéfinis. Seuls les événements atteignant un score minimum sont conservés.
- **Annonces Périodiques Intelligentes** : Pour éviter le spam de notifications, le bot utilise une file d'attente. Il enregistre silencieusement tous les hackathons découverts et diffuse un maximum de 10 nouvelles annonces par heure dans le canal sélectionné.
- **Embeds Discord Enrichis** : Présentation détaillée des informations cruciales, y compris les prix globaux, les formats de participation (100% en ligne, en présentiel, hybride), le lieu et la taille des équipes attendues (généralement 1 à 4 membres).
- **Gestion Automatisée des Deadlines** : Le bot utilise `dateparser` pour surveiller activement les dates limites d'inscription. Il filtre et ignore les hackathons déjà expirés pendant le scraping. Pour les hackathons déjà postés dont la deadline passe, le bot **supprime le message du canal principal** et le **reposte automatiquement dans le canal d'archives** pour maintenir la clarté des annonces actives.
- **Matchmaking et Gestion d'Équipes** :
  - Les utilisateurs peuvent réagir avec un émoji spécifique sur une annonce pour entrer dans une file d'attente de matchmaking.
  - Le bot crée dynamiquement des salons textuels privés pour les équipes nouvellement formées afin de faciliter la coordination.
  - Des notifications par messages privés sont envoyées automatiquement aux membres de l'équipe.

## Commandes Slash disponibles

| Commande | Accès | Description |
| --- | --- | --- |
| `/ping` | Tous | Vérifie la latence du bot |
| `/aide` | Tous | Liste toutes les commandes disponibles |
| `/stats` | Tous | Nombre de hackathons en attente, postés et archivés en base |
| `/bilan` | Tous | Résumé des actions du bot depuis le début de la journée (scrapés, postés, archivés) |
| `/scrape` | Admin | Lance un scraping manuel immédiat sur toutes les plateformes |
| `/post_now [limite]` | Admin | Pousse immédiatement N hackathons non postés vers le canal (défaut : 10) |
| `/archive_now` | Admin | Force l'archivage des hackathons dont la deadline est dépassée |
| `/test_archive [minutes]` | Admin | Crée un hackathon fictif, le poste, puis l'archive automatiquement après N minutes (défaut : 5) |
| `/diagnose` | Tous | Vérifie la configuration des canaux dans le `.env` |

## Prérequis

- Python 3.9 ou supérieur
- Un compte Discord Developer avec un Token de Bot valide.
- Les Privileged Gateway Intents (spécifiquement "Message Content Intent" et "Server Members Intent") doivent être activés sur le portail Discord Developer.

## Installation et Déploiement

1. **Cloner le répertoire** :
   ```bash
   git clone https://github.com/AliouneKane/hackhahunt.git
   cd hackhahunt
   ```

2. **Créer et activer un environnement virtuel** (recommandé) :
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Sous Windows : venv\Scripts\activate
   ```

3. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```
   *(S'il y a un fichier `scraper/requirements.txt` séparé pour la logique de scraping, installez-le également : `pip install -r scraper/requirements.txt`)*

4. **Configuration de l'environnement** :
   Créez un fichier `.env` à la racine du projet en utilisant le modèle suivant :
   ```env
   DISCORD_BOT_TOKEN=votre_token_secret_ici
   GUILD_ID=123456789012345678              # L'ID de votre serveur Discord principal
   HACKATHON_CHANNEL_ID=123456789012345678  # Le canal où les annonces seront postées
   ARCHIVES_CHANNEL_ID=123456789012345678   # Le canal où les hackathons expirés seront archivés
   ```

5. **Initialisation de la base de données** :
   La base de données locale SQLite initialisera automatiquement et créera toutes les tables nécessaires (`hackahunt.db`) lors du premier lancement.

6. **Lancer le bot localement** :
   ```bash
   python3 bot.py
   ```
   *Une fois démarré, le bot commencera ses tâches en arrière-plan, programmera ses scrapers périodiques et configurera les événements Discord.*

## Structure du Projet

- `bot.py` : Le point d'entrée principal du bot Discord. Il gère la connexion, enregistre les commandes slash et lance les boucles asynchrones en arrière-plan.
- `database.py` : Gère toutes les requêtes de la base de données SQLite (sauvegarde des hackathons, logs des ID de messages Discord et gestion des formations d'équipes).
- `/cogs/` : Contient les plugins Discord modulaires séparés par domaine d'action (`hackathons.py`, `matchmaking.py`, `teams.py`).
- `/scraper/` : Héberge la logique centrale de collecte de données et l'orchestrateur.
  - `runner.py` : Exécute les tâches de scraping, sauvegarde les enregistrements dans la base de données, et publie progressivement les posts sur Discord via un système de lots.
  - `scorer.py` : Applique un contrôle de qualité local en attribuant des scores et en filtrant les événements douteux ou non pertinents.
  - `devpost.py`, `mlh.py`, `zindi.py`, `drivendata.py`, etc. : Des scrapers dédiés et adaptés au formatage spécifique de chaque plateforme externe.

## Contribuer

Les contributions sont vivement encouragées ! Qu'il s'agisse d'une petite correction typographique ou d'une amélioration majeure de l'architecture, n'hésitez pas à ouvrir une *issue* sur ce dépôt ou à soumettre une *Pull Request* décrivant vos modifications.

## Licence

Ce projet est open-source. N'hésitez pas à l'utiliser pour construire des communautés solides et des applications innovantes.
