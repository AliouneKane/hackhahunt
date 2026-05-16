# HackaHunt

Bot Discord qui automatise la découverte de hackathons et facilite la création d'équipes au sein d'une communauté Discord.

Surveille **13 plateformes** en continu, filtre les hackathons par qualité et notifie la communauté automatiquement.

## Fonctionnalités

- **Scraping multi-plateformes** — Devpost, MLH, Kaggle, Zindi, DrivenData, Eventbrite, ChallengeData, Challengerocket, Hackmakers, A2SV, Geekulcha, OpportunitiesAfrica, GoogleSenegal
- **Scoring automatique** — chaque hackathon est noté 0/10 selon la pertinence du thème, la géographie, la langue et la source
- **Publication cadencée** — 1 hackathon posté toutes les 5 minutes dans #hackathons
- **Archivage automatique** — les hackathons expirés sont déplacés dans #archives toutes les 12h
- **Rappels deadline** — notifications J-7, J-3, J-1 dans les salons d'équipe
- **Matchmaking par réaction** — clique 👍 sur un hackathon, choisis un coéquipier en MP, salon privé créé automatiquement
- **Onboarding** — message de bienvenue en MP (règles + guide) envoyé à chaque nouveau membre

## Architecture

Le bot et le scraper tournent en **deux processus séparés** pour éviter de bloquer l'event loop Discord.

```text
hackahunt/
├── bot.py                   # Bot Discord : événements, matchmaking, tâches planifiées
├── scraper_cron.py          # Scraper autonome (lancé toutes les 6h, indépendant du bot)
├── database.py              # Accès PostgreSQL (hackathons, équipes, matchmaking, welcomed)
├── requirements.txt
├── Dockerfile               # Image Python pour bot et scraper
├── docker-compose.yml       # Orchestration : db + bot + scraper
├── .env                     # Variables d'environnement (non versionné)
│
├── cogs/
│   ├── matchmaking.py       # Réactions 👍, votes, matchs mutuels, salons d'équipe
│   └── teams.py             # Création salons privés, rappels deadline, archivage équipes
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

- [Docker](https://www.docker.com/) et Docker Compose
- Bot Discord avec les intents **Server Members** et **Reactions** activés

## Installation

```bash
git clone https://github.com/AliouneKane/hackhahunt.git
cd hackahunt
```

Créer le fichier `.env` :

```env
DISCORD_TOKEN=votre_token
GUILD_ID=id_du_serveur
HACKATHON_CHANNEL_ID=id_canal_hackathons
ARCHIVES_CHANNEL_ID=id_canal_archives
MATCHMAKING_CHANNEL_ID=id_canal_matchmaking
```

## Lancement

Tout démarrer (base de données + bot + scraper) :

```bash
docker compose up -d
```

La base de données est initialisée automatiquement au premier démarrage.

Lancer uniquement la base de données (pour du développement local) :

```bash
docker compose up -d db
python3 bot.py
```

Lancer un scraping manuel hors Docker :

```bash
python3 scraper_cron.py
```

## Services Docker

| Service | Description | Fréquence |
| --- | --- | --- |
| `db` | PostgreSQL 17 (port 5435) | Toujours actif |
| `bot` | Bot Discord principal | Toujours actif |
| `scraper` | Scraping des 13 plateformes | Toutes les 6h |

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
