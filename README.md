# HackaHunt

Bot Discord qui automatise la découverte de hackathons et facilite la création d'équipes au sein d'une communauté Discord.

Surveille **13 plateformes** en continu, filtre les hackathons par qualité et notifie la communauté automatiquement.

> **Hébergement** — Le bot tourne sur une machine personnelle (macOS ou Windows). La base de données est hébergée sur [Neon](https://neon.tech) (PostgreSQL cloud, gratuit). Le bot est actif dès que **la machine est allumée**, sans avoir besoin d'être connecté à Discord.

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
│  (démarrage automatique)        │     │                      │
│                                 │     │                      │
│  scraper_cron.py ─────────────────────► PostgreSQL           │
│  (au login + toutes les 30min)  │     │                      │
└─────────────────────────────────┘     └──────────────────────┘
```

| Processus | Rôle |
| --- | --- |
| **bot.py** | Publication, matchmaking, archivage, logs Discord |
| **scraper_cron.py** | Scraping des 13 plateformes (au démarrage + toutes les 30min) |
| **Neon PostgreSQL** | Base de données cloud (always-on) |

```text
hackahunt/
├── bot.py                   # Bot Discord : publication, matchmaking, archivage, logs
├── scraper_cron.py          # Scraper autonome, lancé au démarrage puis toutes les 30min
├── database.py              # Accès PostgreSQL (Neon)
├── requirements.txt
├── .env                     # Variables d'environnement (non versionné)
│
├── launchagents/            # Configs macOS LaunchAgent
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

- Python 3.9+
- Un compte [Neon](https://neon.tech) (PostgreSQL cloud, gratuit)
- Bot Discord avec les intents **Server Members**, **Reactions** et **Presences** activés dans le [portail développeur Discord](https://discord.com/developers/applications)

## Installation

**1. Cloner le projet**

```bash
git clone https://github.com/AliouneKane/hackhahunt.git
cd hackahunt
```

**2. Créer et activer l'environnement virtuel**

macOS :
```bash
python3 -m venv venv && source venv/bin/activate
```

Windows :
```bat
python -m venv venv
venv\Scripts\activate
```

**3. Installer les dépendances**

```bash
pip install -r requirements.txt
```

**4. Créer le fichier `.env`**

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

## Démarrage automatique

### macOS — LaunchAgent

Copier les fichiers depuis `launchagents/`, adapter les chemins (`/CHEMIN/VERS/hackahunt` et `VOTRE_USER`), puis :

```bash
cp launchagents/*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.hackahunt.bot.plist
launchctl load ~/Library/LaunchAgents/com.hackahunt.scraper.plist
```

Le bot démarre automatiquement à chaque login et se relance en cas de crash.

### Windows — Planificateur de tâches

Le Planificateur de tâches Windows remplace les LaunchAgents macOS.

**Pour `bot.py` (démarrage au login, redémarrage si arrêt) :**

1. Ouvrir le **Planificateur de tâches** (`taskschd.msc`)
2. Créer une tâche de base → nommer la `HackahuntBot`
3. Déclencheur : **Lors de l'ouverture de session**
4. Action : **Démarrer un programme**
   - Programme : `C:\chemin\vers\hackahunt\venv\Scripts\python.exe`
   - Arguments : `C:\chemin\vers\hackahunt\bot.py`
   - Démarrer dans : `C:\chemin\vers\hackahunt`
5. Dans les paramètres : cocher **Redémarrer la tâche si elle s'arrête**

**Pour `scraper_cron.py` (au login + toutes les 30 minutes) :**

Répéter les étapes ci-dessus avec le nom `HackahuntScraper`, le script `scraper_cron.py`, et dans le déclencheur cocher **Répéter la tâche toutes les : 30 minutes**.

**Consulter les logs :**

Les logs sont écrits dans la console. Pour les rediriger vers un fichier, remplacer les arguments par :

```
-u C:\chemin\vers\hackahunt\bot.py >> C:\chemin\vers\hackahunt\logs\bot.log 2>&1
```

---

### Lancement manuel (macOS et Windows)

```bash
python bot.py
python scraper_cron.py
```

**Consulter les logs sur macOS :**

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
