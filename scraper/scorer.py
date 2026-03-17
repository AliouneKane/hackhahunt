"""
scorer.py — Système de scoring des hackathons pour Hackahunt
Calcule un score sur 10 et détecte le niveau de difficulté.
Profil cible : ingénieurs statisticiens économistes (ENSAE Dakar)
"""

# ── Mots-clés par priorité thématique ────────────────────────────────────────

THEMES_HIGH = [
    # Data science / IA / ML
    "data science", "machine learning", "artificial intelligence", "intelligence artificielle",
    "deep learning", "neural network", "nlp", "natural language", "computer vision",
    "predictive", "prédictif", "modélisation", "forecasting", "classification",
    "regression", "régression", "clustering", "anomaly detection",
    # Statistiques / économétrie
    "statistics", "statistique", "econometrics", "économétrie", "panel data",
    "time series", "séries temporelles", "causal inference", "inference causale",
    "survey", "enquête", "indicateurs", "indices",
    # Finance / économie
    "fintech", "finance", "financial", "banking", "banque", "microfinance",
    "economic", "économique", "economy", "économie", "poverty", "pauvreté",
    "inequality", "inégalité", "gdp", "pib", "fiscal", "monetary",
    # Santé publique
    "health", "santé", "epidemiology", "épidémiologie", "public health",
    "disease", "maladie", "mortality", "mortalité", "healthcare",
    # Énergie / climat avec données
    "climate data", "climate change", "données climatiques", "energy",
    "renewable", "carbon", "emissions",
]

THEMES_MEDIUM = [
    "agriculture", "agritech", "farming", "food security", "sécurité alimentaire",
    "govtech", "government", "open data", "données publiques", "civic",
    "smart city", "urban", "mobility", "transport", "logistics",
    "education", "edtech", "learning",
    "supply chain", "e-commerce",
]

THEMES_LOW = [
    "web", "mobile", "app", "application", "platform", "cybersecurity",
    "security", "blockchain", "open innovation", "entrepreneurship",
    "startup", "social impact",
]

THEMES_EXCLUDED = [
    "game", "gaming", "gamedev", "game development",
    "graphic design", "illustration", "fashion",
    "hardware only", "robotics only",
]

# ── Mots-clés de niveau de difficulté ────────────────────────────────────────

LEVEL_BEGINNER = [
    "beginner", "débutant", "no coding", "no experience", "no technical",
    "no code", "everyone", "tout le monde", "open to all", "ouvert à tous",
    "ideathon", "idéation", "pitch", "no prior",
]

LEVEL_INTERMEDIATE = [
    "python", "r programming", "sql", "data analysis", "analyse de données",
    "machine learning basics", "api", "rest api", "basic ml",
    "undergraduate", "étudiant", "student",
]

LEVEL_ADVANCED = [
    "deep learning", "nlp", "large language model", "llm", "transformer",
    "computer vision", "reinforcement learning", "time series forecasting",
    "causal inference", "econometric model", "structural model",
    "optimization", "big data", "spark", "distributed",
    "advanced", "avancé", "expert",
]

LEVEL_RESEARCH = [
    "phd", "doctoral", "research paper", "publication", "peer review",
    "academic", "académique", "jury académique", "scientific committee",
    "workshop paper", "proceedings", "arxiv",
]

# ── Mots-clés géographiques ───────────────────────────────────────────────────

GEO_AFRICA = [
    "africa", "afrique", "african", "africain",
    "senegal", "sénégal", "dakar",
    "nigeria", "kenya", "ghana", "côte d'ivoire", "ivory coast",
    "rwanda", "ethiopia", "tanzania", "morocco", "maroc",
    "west africa", "afrique de l'ouest", "sub-saharan", "subsaharienne",
]

GEO_HYBRID_KEYWORDS = ["online", "virtual", "en ligne", "hybrid", "hybride", "final", "finale"]
GEO_INPERSON_KEYWORDS = ["in-person", "présentiel", "on-site", "on site"]


def score_hackathon(hack: dict) -> dict:
    """
    Calcule le score et le niveau d'un hackathon.
    Retourne le hack enrichi avec 'score', 'level', 'skip'.
    """
    text = " ".join([
        hack.get("title", ""),
        hack.get("theme", ""),
        hack.get("location", ""),
        hack.get("format", ""),
    ]).lower()

    score = 0
    skip = False
    reasons = []

    # ── 1. Filtre disqualifiant : prix minimum ────────────────────────────────
    prize_min = hack.get("prize_min_fcfa", 0)
    if prize_min > 0 and prize_min < 200_000:
        skip = True
        reasons.append("Prix 3e < 200 000 FCFA")

    # ── 2. Score thématique (0–3 pts) ────────────────────────────────────────
    if any(kw in text for kw in THEMES_EXCLUDED):
        skip = True
        reasons.append("Thème hors profil")
    elif any(kw in text for kw in THEMES_HIGH):
        score += 3
    elif any(kw in text for kw in THEMES_MEDIUM):
        score += 2
    elif any(kw in text for kw in THEMES_LOW):
        score += 1
    else:
        score += 1  # thème inconnu → score minimal, pas exclu

    # ── 3. Score géographique (0–3 pts) ──────────────────────────────────────
    is_africa = any(kw in text for kw in GEO_AFRICA)
    is_online = any(kw in text for kw in GEO_HYBRID_KEYWORDS)
    fmt = hack.get("format", "online")

    if is_africa and fmt in ["hybrid", "in-person"]:
        score += 3  # Afrique hybride/présentiel → top
    elif fmt == "online":
        score += 2  # En ligne → accessible
    elif not is_africa and fmt == "hybrid":
        score += 2  # International hybride
    else:
        score += 1  # Présentiel hors Afrique

    # ── 4. Score prix attractif (0–2 pts) ────────────────────────────────────
    if prize_min >= 1_000_000:
        score += 2
    elif prize_min >= 300_000:
        score += 1
    elif prize_min == 0:
        score += 1  # Prix non précisé : on ne pénalise pas trop

    # ── 5. Score accessibilité (0–2 pts) ─────────────────────────────────────
    lang = hack.get("language", "en")
    if lang == "fr":
        score += 2
    elif lang == "fr/en":
        score += 1
    else:
        score += 0  # Anglais uniquement

    # ── 6. Bonus source africaine ─────────────────────────────────────────────
    if hack.get("source") in ["zindi", "a2sv", "geekulcha"]:
        score = min(score + 1, 10)

    score = min(score, 10)

    # ── Détection du niveau ───────────────────────────────────────────────────
    level = _detect_level(text)

    return {
        **hack,
        "score": score,
        "level": level,
        "skip": skip,
        "skip_reasons": reasons,
    }


def _detect_level(text: str) -> str:
    text_lower = text.lower()

    if any(kw in text_lower for kw in LEVEL_RESEARCH):
        return "Recherche"
    if any(kw in text_lower for kw in LEVEL_ADVANCED):
        return "Avancé"
    if any(kw in text_lower for kw in LEVEL_INTERMEDIATE):
        return "Intermédiaire"
    if any(kw in text_lower for kw in LEVEL_BEGINNER):
        return "Débutant"
    return "Intermédiaire"  # défaut pour profil ENSAE


def filter_and_score(hackathons: list) -> list:
    """
    Applique le scoring à une liste de hackathons bruts.
    Retourne uniquement ceux qui passent les filtres, triés par score.
    """
    results = []
    skipped = 0

    for hack in hackathons:
        scored = score_hackathon(hack)
        if scored["skip"]:
            skipped += 1
            continue
        if scored["score"] >= 5:  # Seuil minimum pour être posté
            results.append(scored)

    results.sort(key=lambda h: h["score"], reverse=True)
    print(f"  [Scorer] {len(results)} hackathons retenus, {skipped} exclus")
    return results