# 🎯 HackaHunt

**HackaHunt** est un bot Discord complet conçu pour automatiser la recherche de hackathons et faciliter la création d'équipes (matchmaking) au sein de votre communauté Discord. Il scrute en permanence 12 plateformes de compétitions majeures et centralise les annonces dans votre serveur Discord. 

## 🌟 Fonctionnalités Principales

- 📡 **Scraping Multi-Plateformes** via des APIs officielles et parsers HTML. Les plateformes incluent :
  - **Devpost** (via API JSON)
  - **Major League Hacking (MLH)** (Parsers Tailwind CSS - saisons futures)
  - **Zindi Africa** (via API JSON)
  - **DrivenData**
  - **Kaggle**
  - Et bien d'autres (Eventbrite, plateformes françaises, etc.)
- 🏆 **Filtrage Intelligent (Scorer)** : Trie automatiquement les hackathons et met en avant les plus pertinents pour votre communauté (exclut les thèmes non ciblés et retient les scores élevés).
- 💬 **Discord Rich Embeds** : Affichage complet des informations clés du hackathon : prix à gagner ($1^{\text{er}}$, $2^{\text{e}}$, $3^{\text{e}}$ ou prize pool global), format de participation (100% en ligne, présentiel, hybride), localisation et l'estimation de la taille d'équipe (généralement 1 à 4 personnes).
- 🤝 **Matchmaking et Gestion d'Équipes** : 
  - Réagissez avec 👍 à une annonce pour rejoindre une file d'attente/trouver une équipe.
  - Création dynamique de salons Discord privés pour la coordination de votre nouvelle équipe.
  - Notification en message privé.
- ⏰ **Rappels Automatiques de Deadlines** : Le bot prévient les membres à J-7, J-3, et J-1 avant la fermeture des inscriptions et archive automatiquement les hackathons terminés.

## ⚙️ Prérequis

- [Python 3.9+](https://www.python.org/downloads/)
- Un compte [Discord Developer](https://discord.com/developers/applications) avec un [Token de Bot Discord](https://discordpy.readthedocs.io/en/stable/discord.html) valide. Les "Privileged Gateway Intents" (notamment `Message Content Intent` et `Server Members Intent`) doivent être activés.

## 🚀 Installation & Déploiement

1. **Cloner le projet** :
   ```bash
   git clone https://github.com/AliouneKane/hackhahunt.git
   cd hackhahunt
   ```

2. **Créer et activer un environnement virtuel** (recommandé) :
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Sur Windows: venv\Scripts\activate
   ```

3. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```
   *(Si un `scraper/requirements.txt` existe séparément pour la logique de récupération, installez-le également : `pip install -r scraper/requirements.txt`)*

4. **Configuration de l'environnement (`.env`)** :
   Créez un fichier `.env` à la racine du projet en vous basant sur cet exemple :
   ```env
   DISCORD_BOT_TOKEN=votre_token_secret_ici
   GUILD_ID=123456789012345678              # L'ID de votre Serveur Discord principal
   HACKATHON_CHANNEL_ID=123456789012345678  # Salon où les annonces seront postées
   ARCHIVES_CHANNEL_ID=123456789012345678   # Salon où archiver les hackathons expirés
   ```

5. **Initialisation de la base de données** :
   La base de données SQLite régionale ou locale s'activera au premier lancement et créera les tables nécessaires (`hackahunt.db`).

6. **Lancer le bot localement** :
   ```bash
   python3 bot.py
   ```
   *Une fois démarré, le bot va commencer à scraper les différentes sources et configurer la boucle événementielle et les cogs Discord.*

## 🛠 Structure du projet

- `bot.py` : Point d'entrée du bot Discord. Il gère la connexion, les commandes `/` (slash) et lance l'orchestrateur.
- `database.py` : Gestion des requêtes de la base de données SQLite (sauvegarde des hackathons, logs des messages Discord, gestion des équipes (`t_teams`, `team_members`)).
- `/cogs/` : Regroupe les différents modules Discord par thèmes (`hackathons.py`, `matchmaking.py`, `teams.py`).
- `/scraper/` : Contient l'intelligence de récupération des données et le fameux ordonnanceur.
  - `runner.py` : Scrape et envoie les posts Discord.
  - `scorer.py` : Filtre et attribue une note ou un niveau aux événements trouvés garantissant un certain niveau de qualité localisé.
  - `devpost.py`, `mlh.py`, `zindi.py`, `drivendata.py`, etc : Fichiers dédiés au formatage pour chaque plateforme externe.

## 🤝 Contribution
Toute contribution est la bienvenue. Pour toute idée mineure ou majeure, merci d'ouvrir une *issue* sur ce dépôt puis de soumettre une *Pull Request* décrivant vos modifications !

## 📜 Licence
Ce projet est open-source. Servez-vous et codez de belles choses 💻✨!
