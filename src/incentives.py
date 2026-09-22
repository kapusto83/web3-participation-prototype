"""Layered participation incentive model."""

SUBMISSION_POINTS = 20
QUALIFICATION_POINTS = 30
UNIQUE_POINTS = 50
MAX_REVIEW_POINTS = 100


def points_for_review(
    submitted=True,
    qualified=False,
    non_duplicate=False,
):
    """Calculate participation points without mixing them with wallet activity."""
    points = SUBMISSION_POINTS if submitted else 0

    if qualified:
        points += QUALIFICATION_POINTS

    if qualified and non_duplicate:
        points += UNIQUE_POINTS

    return points


def reward_breakdown(
    submitted=True,
    qualified=False,
    non_duplicate=False,
):
    return {
        "submission": SUBMISSION_POINTS if submitted else 0,
        "qualification": QUALIFICATION_POINTS if qualified else 0,
        "unique": UNIQUE_POINTS if qualified and non_duplicate else 0,
        "total": points_for_review(
            submitted=submitted,
            qualified=qualified,
            non_duplicate=non_duplicate,
        ),
    }


def rate(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def abuse_metrics(
    points,
    submissions,
    qualified,
    duplicates,
    unique_contributions,
    effort_minutes,
):
    return {
        "points_per_minute": (
            points / effort_minutes if effort_minutes else 0.0
        ),
        "qualification_rate": rate(qualified, submissions),
        "duplicate_rate": rate(duplicates, submissions),
        "unique_contribution_rate": rate(
            unique_contributions,
            submissions,
        ),
    }
