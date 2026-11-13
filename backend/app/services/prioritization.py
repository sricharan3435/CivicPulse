from difflib import SequenceMatcher
import math
import re

URGENT_TERMS = {"danger", "dangerous", "accident", "injury", "flooding", "overflow", "blocked", "urgent", "hazard", "exposed"}
CATEGORY_WEIGHT = {
    "Water Leaks": 1.25,
    "Potholes": 1.15,
    "Streetlight Failures": 1.1,
    "Garbage": 1.0,
    "Other": 1.0,
}


def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def analyze_report(title: str, description: str, category: str, latitude: float, longitude: float, existing: list):
    text = f"{title} {description}".lower()
    words = set(re.findall(r"[a-z]+", text))
    weight = CATEGORY_WEIGHT.get(category, 1.0)
    severity = min(len(words & URGENT_TERMS), 3) * 0.12
    candidate_ids = []
    nearby = [
        issue for issue in existing
        if issue.category == category and _distance_meters(latitude, longitude, issue.latitude, issue.longitude) <= 300
    ]

    if nearby:
        try:
            import numpy as np
            import pandas as pd
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            frame = pd.DataFrame([{"id": issue.id, "text": f"{issue.title} {issue.description}"} for issue in nearby])
            matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(frame["text"].tolist() + [text])
            scores = np.asarray(cosine_similarity(matrix[-1], matrix[:-1])).ravel()
            best = int(scores.argmax())
            if scores[best] >= 0.55:
                candidate_ids = [nearby[best].id]
            similarity = float(scores.max())
        except (ImportError, ValueError):
            fallback_scores = [SequenceMatcher(None, text, f"{issue.title} {issue.description}".lower()).ratio() for issue in nearby]
            best = max(range(len(fallback_scores)), key=fallback_scores.__getitem__)
            similarity = fallback_scores[best]
            if similarity >= 0.55:
                candidate_ids = [nearby[best].id]
    else:
        similarity = 0.0

    # Higher reported urgency and nearby similar reports raise the review score.
    score = min(100.0, 35 * weight + 20 * severity + 25 * similarity + min(20, len(nearby) * 5))
    return round(score, 1), (candidate_ids[0] if candidate_ids else None)
