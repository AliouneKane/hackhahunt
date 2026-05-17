# HackaHunt

Bot Discord qui automatise la découverte de hackathons et facilite la création d'équipes au sein d'une communauté Discord.

Surveille **13 plateformes** en continu, filtre les hackathons par qualité et notifie la communauté automatiquement.

> **Hébergement** — Le bot tourne sur ma machine personnelle (macOS). La base de données est hébergée sur [Neon](https://neon.tech) (PostgreSQL cloud). Le bot est actif dès que **ma machine est allumée**, sans avoir besoin d'être connecté à Discord.

## Fonctionnalités

- **Scraping multi-plateformes** — Devpost, MLH, Kaggle, Zindi, DrivenData, Eventbrite, ChallengeData, Challengerocket, Hackmakers, A2SV, Geekulcha, OpportunitiesAfrica, GoogleSenegal
- **Scoring automatique** — chaque hackathon est noté 0/10 selon la pertinence du thème, la géographie, la langue et la source
- **Publication cadencée** — 1 hackathon posté toutes les 5 minutes dans #hackathons
- **Rattrapage au démarrage** — tous les hackathons en attente sont publiés d'un coup dès l'allumage de la machine
- **Archivage automatique** — les hackathons expirés sont déplacés dans #archives toutes les 12h
- **Rappels deadline** — notifications J-7, J-3, J-1 dans les salons d'équipe
- **Matchmaking par réaction** — clique 👍 sur un hackathon, choisis un coéquipier en MP, salon privé créé automatiquement
- **Onboarding** — message de bienvenue en MP (règles + guide) envoyé à chaque nouveau membre
- **Canal de logs** — le bot poste en temps réel dans #log-bots ce qu'il est en train de faire
- **DM de résumé** — à chaque reconnexion Discord, le propriétaire reçoit un MP résumant l'activité depuis sa dernière connexion

## Architecture

```text
┌─────────────────────────────────┐     ┌──────────────────────┐
│         Machine locale          │     │      Neon (cloud)    │
│                                 │     │                      │
│  bot.py ──────────────────────────────► PostgreSQL           │
│  (LaunchAgent, au login)        │     │                      │
│                                 │     │                      │
│  scraper_cron.py ─────────────────────► PostgreSQL           │
│  (LaunchAgent, toutes les 30min)│     │                      │
└─────────────────────────────────┘     └──────────────────────┘
```

| Processus | Démarrage | Rôle |
| --- | --- | --- |
| **bot.py** | LaunchAgent (au login) | Publication, matchmaking, archivage, logs |
| **scraper_cron.py** | LaunchAgent (au login + toutes les 30min) | Scraping des 13 plateformes |
| **Neon PostgreSQL** | Cloud (always-on) | Base de données |

```text
hackahunt/
├── bot.py                   # Bot Discord : publication, matchmaking, archivage, logs
├── scraper_cron.py          # Scraper autonome, lancé au démarrage puis toutes les 30min
├── database.py              # Accès PostgreSQL (Neon)
├── requirements.txt
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
- Python 3.9+
- Un compte [Neon](https://neon.tech) (PostgreSQL cloud, gratuit)
- Bot Discord avec les intents **Server Members**, **Reactions** et **Presences** activés

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
BOT_LOGS_CHANNEL_ID=id_canal_log_bots
OWNER_ID=votre_id_discord
DATABASE_URL=postgresql://...votre_url_neon...
```

## Démarrage

**Installer les LaunchAgents (démarrage automatique au login) :**

Copier les fichiers depuis `launchagents/`, adapter les chemins (`/CHEMIN/VERS/hackahunt` et `VOTRE_USER`), puis :

```bash
cp launchagents/*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.hackahunt.bot.plist
launchctl load ~/Library/LaunchAgents/com.hackahunt.scraper.plist
```

Dès le login, le bot démarre, vide la file d'attente et publie dans #hackathons. Le scraper cherche de nouveaux hackathons au démarrage puis toutes les 30 minutes.

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
