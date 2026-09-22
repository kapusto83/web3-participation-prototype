import argparse
import random
from datetime import datetime, timezone, timedelta

from database import (
    create_participant,
    create_session,
    create_review,
    log_event,
    complete_session,
    save_acknowledgement,
)
from incentives import points_for_review


DEFAULT_COUNT = 100

# Experiment assumptions:
# - 30% of participants are "good": primarily task-driven.
# - 70% are "adversarial": more reward-seeking and more likely to optimize/farm.
PERSONA_WEIGHTS = {
    "good": 0.30,
    "adversarial": 0.70,
}

PERSONA_BEHAVIOR = {
    "good": {
        "qualified": 0.90,
        "duplicate": 0.03,
        "wallet": 0.25,
        "wallet_failure": 0.05,
        "effort_min": 2.0,
        "effort_max": 5.0,
    },
    "adversarial": {
        "qualified": 0.65,
        "duplicate": 0.25,
        "wallet": 0.20,
        "wallet_failure": 0.10,
        "effort_min": 0.5,
        "effort_max": 2.0,
    },
}


def timestamp(offset_minutes=0):
    return (
        datetime.now(timezone.utc)
        + timedelta(minutes=offset_minutes)
    ).isoformat()


def weighted_choice(rng, weights):
    values = list(weights.keys())
    probabilities = list(weights.values())
    return rng.choices(values, weights=probabilities, k=1)[0]


def run_scenario(name, persona, rng, forced=None):
    behavior = PERSONA_BEHAVIOR[persona]

    forced = forced or {}

    qualified = forced.get("qualified", rng.random() < behavior["qualified"])
    duplicate = forced.get("duplicate", rng.random() < behavior["duplicate"])

    # A duplicate is still allowed to have a qualified-looking submission;
    # uniqueness is what determines the final +50 point layer.
    wallet = forced.get("wallet", rng.random() < behavior["wallet"])
    wallet_failed = forced.get(
        "wallet_failed",
        wallet and rng.random() < behavior["wallet_failure"],
    )

    effort_minutes = forced.get(
        "effort_minutes",
        round(
            rng.uniform(
                behavior["effort_min"],
                behavior["effort_max"],
            ),
            2,
        ),
    )

    created_at = timestamp()
    participant_id = create_participant(created_at)

    session_id = create_session(
        participant_id=participant_id,
        started_at=created_at,
    )

    metadata_base = {
        "persona": persona,
        "effort_minutes": effort_minutes,
    }

    if forced and forced.get("scenario"):
        metadata_base["scenario"] = forced["scenario"]

    # Funnel
    log_event(
        participant_id,
        "invited",
        timestamp(),
        session_id=session_id,
        metadata=metadata_base,
    )

    log_event(
        participant_id,
        "started",
        timestamp(),
        session_id=session_id,
    )

    log_event(
        participant_id,
        "disclosure_viewed",
        timestamp(),
        session_id=session_id,
    )

    log_event(
        participant_id,
        "review_started",
        timestamp(),
        session_id=session_id,
    )

    review_text = (
        f"Synthetic review for {name}. "
        "The disclosure should provide more detail about "
        "the assumptions behind projected annual generation "
        "and the expected operating conditions."
    )

    review_id = create_review(
        session_id=session_id,
        participant_id=participant_id,
        content=review_text,
        qualified=qualified,
        created_at=timestamp(),
    )

    log_event(
        participant_id,
        "review_submitted",
        timestamp(),
        session_id=session_id,
        review_id=review_id,
        metadata=metadata_base,
    )

    if qualified:
        log_event(
            participant_id,
            "review_qualified",
            timestamp(),
            session_id=session_id,
            review_id=review_id,
            metadata={
                **metadata_base,
                "qualification_rule": "synthetic_probability",
            },
        )

    if duplicate:
        log_event(
            participant_id,
            "duplicate_detected",
            timestamp(),
            session_id=session_id,
            review_id=review_id,
            metadata={
                **metadata_base,
                "reason": "synthetic_duplicate_probability",
            },
        )

    non_duplicate = qualified and not duplicate
    points = points_for_review(
        submitted=True,
        qualified=qualified,
        non_duplicate=non_duplicate,
    )

    log_event(
        participant_id,
        "points_awarded",
        timestamp(),
        session_id=session_id,
        review_id=review_id,
        metadata={
            **metadata_base,
            "submission_points": 20,
            "qualification_points": 30 if qualified else 0,
            "unique_points": 50 if non_duplicate else 0,
            "points": points,
        },
    )

    # Optional wallet acknowledgement is deliberately independent of points
    # and qualification.
    if wallet:
        wallet_address = f"0xSYNTHETIC{name[-6:]}"

        log_event(
            participant_id,
            "wallet_connect_started",
            timestamp(),
            session_id=session_id,
            review_id=review_id,
        )

        log_event(
            participant_id,
            "wallet_connected",
            timestamp(),
            session_id=session_id,
            review_id=review_id,
            metadata={
                "wallet_address": wallet_address,
            },
        )

        log_event(
            participant_id,
            "acknowledgement_requested",
            timestamp(),
            session_id=session_id,
            review_id=review_id,
        )

        if wallet_failed:
            log_event(
                participant_id,
                "acknowledgement_failed",
                timestamp(),
                session_id=session_id,
                review_id=review_id,
                metadata={
                    "reason": "synthetic_signature_failure",
                },
            )
        else:
            message = f"Synthetic acknowledgement for {review_id}"
            signature = f"synthetic-signature-{participant_id}"

            save_acknowledgement(
                participant_id=participant_id,
                review_id=review_id,
                wallet_address=wallet_address,
                message=message,
                signature=signature,
                acknowledged_at=timestamp(),
            )

            log_event(
                participant_id,
                "acknowledgement_signed",
                timestamp(),
                session_id=session_id,
                review_id=review_id,
            )

    log_event(
        participant_id,
        "completed",
        timestamp(),
        session_id=session_id,
        review_id=review_id,
    )

    complete_session(
        session_id,
        timestamp(),
    )

    return {
        "name": name,
        "persona": persona,
        "qualified": qualified,
        "duplicate": duplicate,
        "wallet": wallet,
        "wallet_failed": wallet_failed,
        "effort_minutes": effort_minutes,
        "points": points,
    }


def run_defined_scenario(name, scenario, rng):
    """Run one of the four scenarios defined in the prototype specification."""
    scenario_config = {
        "A — wallet declined": {
            "persona": "good",
            "qualified": True,
            "duplicate": False,
            "wallet": False,
            "wallet_failed": False,
        },
        "B — wallet signed": {
            "persona": "good",
            "qualified": True,
            "duplicate": False,
            "wallet": True,
            "wallet_failed": False,
        },
        "C — duplicate": {
            "persona": "adversarial",
            "qualified": True,
            "duplicate": True,
            "wallet": False,
            "wallet_failed": False,
        },
        "D — wallet failure": {
            "persona": "good",
            "qualified": True,
            "duplicate": False,
            "wallet": True,
            "wallet_failed": True,
        },
    }

    config = scenario_config[scenario]
    behavior = PERSONA_BEHAVIOR[config["persona"]]

    effort_minutes = round(
        rng.uniform(
            behavior["effort_min"],
            behavior["effort_max"],
        ),
        2,
    )

    return run_scenario(
        name=name,
        persona=config["persona"],
        rng=rng,
        forced={
            **config,
            "effort_minutes": effort_minutes,
            "scenario": scenario,
        },
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Append synthetic participation data. "
            "The first four records are the defined scenarios; "
            "the remaining records are probabilistic."
        )
    )
    parser.add_argument(
        "count",
        nargs="?",
        type=int,
        default=DEFAULT_COUNT,
        help=f"Number of participants to generate (default: {DEFAULT_COUNT})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible synthetic data.",
    )

    args = parser.parse_args()

    if args.count < 4:
        parser.error(
            "count must be at least 4 so all four defined scenarios are included"
        )

    rng = random.Random(args.seed)

    defined_scenarios = [
        "A — wallet declined",
        "B — wallet signed",
        "C — duplicate",
        "D — wallet failure",
    ]

    print(
        f"Generating {args.count} synthetic participants "
        f"({len(defined_scenarios)} defined + "
        f"{args.count - len(defined_scenarios)} probabilistic)..."
    )

    results = []

    for index, scenario in enumerate(defined_scenarios, start=1):
        results.append(
            run_defined_scenario(
                name=f"Scenario-{chr(64 + index)}",
                scenario=scenario,
                rng=rng,
            )
        )

    for i in range(len(defined_scenarios) + 1, args.count + 1):
        persona = weighted_choice(rng, PERSONA_WEIGHTS)
        results.append(
            run_scenario(
                name=f"Synthetic-{i:04d}",
                persona=persona,
                rng=rng,
            )
        )

    qualified = sum(r["qualified"] for r in results)
    duplicates = sum(r["duplicate"] for r in results)
    total_points = sum(r["points"] for r in results)
    total_effort = sum(r["effort_minutes"] for r in results)

    print("\nDone.")
    print(f"Participants added: {len(results)}")
    print(f"Defined scenarios: {len(defined_scenarios)}")
    print(f"Probabilistic participants: {len(results) - len(defined_scenarios)}")
    print(f"Good: {sum(r['persona'] == 'good' for r in results)}")
    print(f"Adversarial: {sum(r['persona'] == 'adversarial' for r in results)}")
    print(f"Qualified: {qualified}")
    print(f"Duplicates: {duplicates}")
    print(f"Points: {total_points}")
    print(
        f"Points/minute: {total_points / total_effort:.2f}"
        if total_effort
        else "Points/minute: 0.00"
    )


if __name__ == "__main__":
    main()
