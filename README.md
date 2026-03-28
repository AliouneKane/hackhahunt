# HackaHunt

HackaHunt is a comprehensive Discord bot designed to automate the discovery of hackathons and facilitate team creation (matchmaking) within your Discord community. It continuously monitors 12 major competition platforms and centralizes their announcements directly into your Discord server without overwhelming the users.

## Main Features

- **Multi-Platform Scraping**: Automated data collection using official APIs and resilient HTML parsers. Supported platforms include:
  - Devpost (via JSON API)
  - Major League Hacking / MLH (Custom Tailwind CSS parser)
  - Zindi Africa (via JSON API)
  - DrivenData
  - Kaggle
  - Additional sources (Eventbrite, ChallengeData, Challengerocket, etc.)
- **Intelligent Filtering and Scoring**: Automatically filters out irrelevant themes and ranks hackathons based on predefined quality criteria. Only events meeting a strict scoring threshold are retained.
- **Smart Paced Announcements**: To prevent notification spam, the bot implements a queued posting system. It saves all discovered hackathons silently and broadcasts a maximum of 10 new announcements per hour to the selected channel.
- **Discord Rich Embeds**: Detailed presentation of crucial information, including prize pools (1st, 2nd, 3rd places, or overall prize values), participation formats (100% online, in-person, hybrid), location, and expected team sizes (typically 1 to 4 members).
- **Automated Deadline Management**: The bot uses `dateparser` to actively monitor registration deadlines. It automatically screens out hackathons that have already expired during the scraping process to prevent database clutter. For hackathons already posted, expired events are strictly moved to an archive channel to maintain the clarity of the main announcements channel.
- **Matchmaking and Team Management**:
  - Users can react with a specific emoji on an announcement to enter a matchmaking queue.
  - The bot dynamically provisions private Discord text channels for newly matched teams to coordinate.
  - Automatic private message notifications are sent to team members.

## Prerequisites

- Python 3.9 or higher
- A Discord Developer account with a valid Bot Token.
- Privileged Gateway Intents (specifically the Message Content Intent and Server Members Intent) must be enabled in the Discord Developer Portal.

## Installation and Deployment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AliouneKane/hackhahunt.git
   cd hackhahunt
   ```

2. **Create and activate a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(If a separate `scraper/requirements.txt` exists for the scraping logic, install it as well: `pip install -r scraper/requirements.txt`)*

4. **Environment Configuration**:
   Create a `.env` file at the root of the project using the following template:
   ```env
   DISCORD_BOT_TOKEN=your_secret_token_here
   GUILD_ID=123456789012345678              # The ID of your main Discord Server
   HACKATHON_CHANNEL_ID=123456789012345678  # Channel where announcements will be posted
   ARCHIVES_CHANNEL_ID=123456789012345678   # Channel where expired hackathons will be archived
   ```

5. **Database Initialization**:
   The local SQLite database will automatically initialize upon the first launch and create all necessary tables (`hackahunt.db`).

6. **Run the bot locally**:
   ```bash
   python3 bot.py
   ```
   *Once started, the bot will begin its background tasks, schedule its periodic scrapers, and configure the Discord event loops.*

## Project Structure

- `bot.py`: The main entry point for the Discord bot. It handles the connection, registers slash commands, and starts the asynchronous background loops.
- `database.py`: Handles all SQLite database queries (saving hackathons, logging Discord message IDs, and managing team formations).
- `/cogs/`: Contains modular Discord plugins separated by domain (`hackathons.py`, `matchmaking.py`, `teams.py`).
- `/scraper/`: Houses the core data gathering logic and the orchestrator.
  - `runner.py`: Executes the scraping tasks, saves records to the database, and slowly trickles posts into Discord via the batching system.
  - `scorer.py`: Enforces localized quality control by attributing scores and filtering out irrelevant events.
  - `devpost.py`, `mlh.py`, `zindi.py`, `drivendata.py`, etc.: Dedicated scrapers tailored to the formatting of each external platform.

## Contributing

Contributions are highly encouraged. Whether it is a minor typo fix or a major architectural improvement, please consider opening an issue on this repository and submitting a Pull Request describing your changes.

## License

This project is open-source. Feel free to use it to build robust communities and great software.
