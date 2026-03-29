# HackaHunt

Bot Discord qui automatise la découverte de hackathons et facilite la création d'équipes au sein d'une communauté Discord.

Surveille **12 plateformes** en continu, filtre les hackathons par qualité et permet aux membres de former des équipes en un clic.

## Fonctionnalités

- **Scraping multi-plateformes** — Devpost, MLH, Kaggle, Zindi, DrivenData, Eventbrite, ChallengeData, Challengerocket, Hackmakers, A2SV, Geekulcha, OpportunitiesAfrica
- **Scoring automatique** — chaque hackathon est noté 0/10 selon la pertinence du thème, la géographie, la langue et la source
- **Anti-spam** — file d'attente diffusant max 10 annonces/heure
- **Archivage automatique** — les hackathons expirés sont déplacés dans #archives
- **Rappels deadline** — notifications J-7, J-3, J-1 dans les salons d'équipe
- **Matchmaking** — réagis avec 👍, choisis un coéquipier en MP, salon privé créé automatiquement
- **Onboarding** — message de bienvenue en MP avec règles et guide du serveur

## Commandes

| Commande | Accès | Description |
|---|---|---|
| `/aide` | Tous | Liste des commandes |
| `/ping` | Tous | Latence du bot |
| `/stats` | Tous | Hackathons en base |
| `/bilan` | Tous | Résumé des actions du jour |
| `/diagnose` | Tous | Vérifier la config des canaux |
| `/monequipe` | Tous | Voir son équipe en cours |
| `/team @pseudo` | Tous | Proposer une équipe |
| `/welcome_all` | Admin | Envoyer le welcome aux membres existants |
| `/scrape` | Admin | Lancer un scraping manuel |
| `/post_now [n]` | Admin | Poster N hackathons immédiatement |
| `/archive_now` | Admin | Forcer l'archivage |
| `/test_archive [min]` | Admin | Tester le cycle complet |

## Prérequis

- Python 3.9+
- Compte [Discord Developer](https://discord.com/developers) avec un token de bot
- Gateway Intents activés : **Message Content**, **Server Members**

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
```

```bash
python3 bot.py
```

La base de données (`hackahunt.db`) se crée automatiquement au premier lancement.

## Déploiement (Heroku)

```bash
heroku create
heroku config:set DISCORD_TOKEN=... GUILD_ID=... HACKATHON_CHANNEL_ID=... ARCHIVES_CHANNEL_ID=... MATCHMAKING_CHANNEL_ID=...
git push heroku main
heroku ps:scale worker=1
```

## Architecture

```
hackahunt/
├── bot.py                  # Point d'entrée, commandes slash, tâches planifiées
├── database.py             # SQLite (hackathons, équipes, matchmaking, welcomed)
├── requirements.txt
├── .env                    # Variables d'environnement (non versionné)
├── Procfile                # Heroku worker
├── runtime.txt
│
├── cogs/
│   ├── matchmaking.py      # Réactions 👍, votes, matchs mutuels
│   └── teams.py            # Création salons privés, rappels, archivage
│
└── scraper/
    ├── runner.py            # Orchestrateur (scraping, posting, archiving)
    ├── scorer.py            # Scoring qualité 0-10
    ├── devpost.py           # Devpost (API JSON)
    ├── mlh.py               # Major League Hacking
    ├── kaggle.py            # Kaggle
    ├── zindi.py             # Zindi Africa
    ├── drivendata.py        # DrivenData
    ├── eventbrite.py        # Eventbrite
    ├── hackmakers.py        # Hackmakers
    ├── french_platforms.py  # ChallengeData, Challengerocket
    └── africa_platforms.py  # A2SV, Geekulcha, OpportunitiesAfrica
```

## Flux utilisateur

```
Hackathon posté dans #hackathons
        │
        ▼
Membre clique 👍
        │
        ▼
Bot envoie MP avec liste des intéressés
        │
        ▼
Membre choisit un coéquipier
        │
        ▼
Match mutuel → salon privé créé
        │
        ▼
Rappels automatiques J-7 / J-3 / J-1
```

## Licence

Open-source.
