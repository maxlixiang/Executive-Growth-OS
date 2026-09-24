from datetime import date, timedelta

def next_review_date(concept_score: int, application_score: int, consecutive_successes: int, today: date | None = None) -> date:
    """Transparent V1 scheduler; kept independent so it can be upgraded later."""
    if not 0 <= concept_score <= 3 or not 0 <= application_score <= 3:
        raise ValueError("Scores must be between 0 and 3.")
    today = today or date.today()
    if concept_score <= 1: days = 1
    elif application_score <= 1: days = 3
    elif application_score == 2: days = 7
    else:
        days = (14, 30, 60, 90)[min(consecutive_successes, 3)]
    return today + timedelta(days=days)
