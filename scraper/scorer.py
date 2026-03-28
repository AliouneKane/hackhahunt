"""
scorer.py — Système de scoring des hackathons pour Hackahunt
Calcule un score sur 10 et détecte le niveau de difficulté.
Profil cible : ingénieurs statisticiens économistes (ENSAE Dakar)
"""

# ── Mots-clés par priorité thématique ────────────────────────────────────────

THEMES_HIGH = [
    "data science", "machine learning", "artificial intelligence", "intelligence artificielle",
    "deep learning", "neural network", "nlp", "natural language", "computer vision",
    "predictive", "prédictif", "modélisation", "forecasting", "classification",
    "regression", "régression", "clustering", "anomaly detection",
    "statistics", "statistique", "econometrics", "économétrie", "panel data",
    "time series", "séries temporelles", "causal inference", "inference causale",
    "survey", "enquête", "indicateurs", "indices",
    "fintech", "finance", "financial", "banking", "banque", "microfinance",
    "economic", "économique", "economy", "économie", "poverty", "pauvreté",
    "inequality", "inégalité", "gdp", "pib", "fiscal", "monetary",
    "health", "santé", "epidemiology", "épidémiologie", "public health",
    "disease", "maladie", "mortality", "mortalité", "healthcare",
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

GEO_AFRICA = [
    "africa", "afrique", "african", "africain",
    "senegal", "sénégal", "dakar",
    "nigeria", "kenya", "ghana", "côte d'ivoire", "ivory coast",
    "rwanda", "ethiopia", "tanzania", "morocco", "maroc",
    "west africa", "afrique de l'ouest", "sub-saharan", "subsaharienne",
]


def score_hackathon(hack: dict) -> dict:
    text = " ".join([
        hack.get("title", ""),
        hack.get("theme", ""),
        hack.get("location", ""),
        hack.get("format", ""),
    ]).lower()

    score = 0
    skip = False
    reasons = []

    # ── 1. Filtre prix désactivé — tous les hackathons gratuits sont acceptés ─
    prize_min = hack.get("prize_min_fcfa", 0)

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
        score += 1

    # ── 3. Score géographique (0–3 pts) ──────────────────────────────────────
    is_africa = any(kw in text for kw in GEO_AFRICA)
    fmt = hack.get("format", "online")

    if is_africa and fmt in ["hybrid", "in-person"]:
        score += 3
    elif fmt == "online":
        score += 2
    elif not is_africa and fmt == "hybrid":
        score += 2
    else:
        score += 1

    # ── 4. Score prix neutralisé — bonus fixe pour tous ──────────────────────
    score += 1

    # ── 5. Score accessibilité (0–2 pts) ─────────────────────────────────────
    lang = hack.get("language", "en")
    if lang == "fr":
        score += 2
    elif lang == "fr/en":
        score += 1

    # ── 6. Bonus source africaine ─────────────────────────────────────────────
    if hack.get("source") in ["zindi", "a2sv", "geekulcha"]:
        score = min(score + 1, 10)

    score = min(score, 10)
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
    return "Intermédiaire"


def filter_and_score(hackathons: list) -> list:
    results = []
    skipped = 0
    low_score = 0
    for hack in hackathons:
        scored = score_hackathon(hack)
        if scored["skip"]:
            skipped += 1
            continue
        if scored["score"] >= 3:  # Seuil basé de 5 à 3 pour capturer plus de hackathons
            results.append(scored)
        else:
            low_score += 1
    results.sort(key=lambda h: h["score"], reverse=True)
    print(f"  [Scorer] {len(results)} hackathons retenus, {skipped} exclus (thème hors profil), {low_score} score trop bas")
    return results