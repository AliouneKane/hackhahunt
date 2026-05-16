# HackaHunt

Bot Discord qui automatise la découverte de hackathons et facilite la création d'équipes au sein d'une communauté Discord.

Surveille **13 plateformes** en continu, filtre les hackathons par qualité et notifie la communauté automatiquement.

> **Hébergement local** — Le bot tourne sur ma machine personnelle (macOS), pas sur un serveur cloud.
> Il est actif uniquement quand **ma machine est allumée et que je suis connecté à Discord**.
> Faute de pouvoir financer un hébergement cloud (Railway, Fly.io, etc.), c'est la solution retenue pour l'instant.

## Fonctionnalités

- **Scraping multi-plateformes** — Devpost, MLH, Kaggle, Zindi, DrivenData, Eventbrite, ChallengeData, Challengerocket, Hackmakers, A2SV, Geekulcha, OpportunitiesAfrica, GoogleSenegal
- **Scoring automatique** — chaque hackathon est noté 0/10 selon la pertinence du thème, la géographie, la langue et la source
- **Publication cadencée** — 1 hackathon posté toutes les 5 minutes dans #hackathons
- **Archivage automatique** — les hackathons expirés sont déplacés dans #archives toutes les 12h
- **Rappels deadline** — notifications J-7, J-3, J-1 dans les salons d'équipe
- **Matchmaking par réaction** — clique 👍 sur un hackathon, choisis un coéquipier en MP, salon privé créé automatiquement
- **Onboarding** — message de bienvenue en MP (règles + guide) envoyé à chaque nouveau membre

## Architecture

Le projet tourne entièrement en local sur macOS. Trois processus indépendants :

| Processus | Démarrage | Rôle |
| --- | --- | --- |
| **PostgreSQL** | Docker (always-on) | Base de données |
| **bot.py** | LaunchAgent (au login) | Publication, matchmaking, archivage |
| **scraper_cron.py** | LaunchAgent (toutes les 6h) | Scraping des 13 plateformes |

```text
hackahunt/
├── bot.py                   # Bot Discord : matchmaking, publication, archivage
├── scraper_cron.py          # Scraper autonome, lancé toutes les 6h
├── database.py              # Accès PostgreSQL
├── requirements.txt
├── docker-compose.yml       # Lance uniquement la base PostgreSQL
├── Dockerfile
├── .env                     # Variables d'environnement (non versionné)
│
├── launchagents/            # Configs macOS LaunchAgent (à adapter et copier dans ~/Library/LaunchAgents/)
│   ├── com.hackahunt.bot.plist
│   └── com.hackahunt.scraper.plist
│
├── cogs/
│   ├── matchmaking.py       # Réactions 👍, votes, matchs mutuels
│   └── teams.py             # Salons d'équipe, rappels, archivage
│
└── scraper/
    ├── runner.py            # Orchestrateur async (posting Discord, archivage)
    ├── scorer.py            # Scoring qualité 0-10
    ├── devpost.py
    ├── mlh.py
    ├── kaggle.py
    ├── zindi.py
    ├── drivendata.py
    ├── eventbrite.py
    ├── hackmakers.py
    ├── french_platforms.py  # ChallengeData, Challengerocket
    ├── africa_platforms.py  # A2SV, Geekulcha, OpportunitiesAfrica
    └── senegal_platforms.py
```

## Prérequis

- macOS
- [Docker Desktop](https://www.docker.com/)
- Python 3.9+ avec venv
- Bot Discord avec les intents **Server Members** et **Reactions** activés

## Installation

```bash
git clone https://github.com/AliouneKane/hackhahunt.git
cd hackahunt
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Créer le fichier `.env` :

```env
DISCORD_TOKEN=votre_token
GUILD_ID=id_du_serveur
HACKATHON_CHANNEL_ID=id_canal_hackathons
ARCHIVES_CHANNEL_ID=id_canal_archives
MATCHMAKING_CHANNEL_ID=id_canal_matchmaking
DATABASE_URL=postgresql://hackahunt:hackahunt_local_pw@localhost:5435/hackahunt
```

## Démarrage

**1. Lancer la base de données :**

```bash
docker compose up -d
```

**2. Installer les LaunchAgents (démarrage automatique au login) :**

Copier les fichiers depuis `launchagents/`, adapter les chemins (`/CHEMIN/VERS/hackahunt` et `VOTRE_USER`), puis :

```bash
cp launchagents/*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.hackahunt.bot.plist
launchctl load ~/Library/LaunchAgents/com.hackahunt.scraper.plist
```

Le bot démarre automatiquement à chaque login et se relance en cas de crash.
Le scraper tourne toutes les 6h.

**Lancer manuellement (sans LaunchAgent) :**

```bash
python3 bot.py
python3 scraper_cron.py
```

**Consulter les logs :**

```bash
tail -f ~/Library/Logs/hackahunt-bot.log
tail -f ~/Library/Logs/hackahunt-scraper.log
```

## Flux utilisateur

```text
Hackathon posté dans #hackathons (toutes les 5 min)
        │
        ▼
Membre clique 👍
        │
        ▼
Bot envoie un MP avec la liste des membres intéressés
        │
        ▼
Membre choisit un coéquipier
        │
        ▼
Match mutuel → salon privé créé automatiquement
        │
        ▼
Rappels automatiques J-7 / J-3 / J-1 avant la deadline
```

## Licence

Open-source.
