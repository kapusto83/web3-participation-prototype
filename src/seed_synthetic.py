from datetime import datetime, timezone, timedelta

from database import (
    create_participant,
    create_session,
    create_review,
    log_event,
    complete_session,
    save_acknowledgement,
)


def timestamp(offset_minutes=0):
    return (
        datetime.now(timezone.utc)
        + timedelta(minutes=offset_minutes)
    ).isoformat()


def run_scenario(name, wallet=False, wallet_failed=False, duplicate=False):
    created_at = timestamp()

    participant_id = create_participant(created_at)

    session_id = create_session(
        participant_id=participant_id,
        started_at=created_at,
    )

    # Funnel events
    log_event(
        participant_id,
        "invited",
        timestamp(),
        session_id=session_id,
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
        qualified=True,
        created_at=timestamp(),
    )

    log_event(
        participant_id,
        "review_submitted",
        timestamp(),
        session_id=session_id,
        review_id=review_id,
    )

    log_event(
        participant_id,
        "review_qualified",
        timestamp(),
        session_id=session_id,
        review_id=review_id,
        metadata={
            "qualification_rule": "synthetic_test"
        },
    )

    # --------------------------------------------------
    # Duplicate scenario
    # --------------------------------------------------

    if duplicate:

        log_event(
            participant_id,
            "duplicate_detected",
            timestamp(),
            session_id=session_id,
            review_id=review_id,
            metadata={
                "reason": "second_review_for_same_session"
            },
        )

        complete_session(
            session_id,
            timestamp(),
        )

        print(
            f"{name}: duplicate detected "
            f"({participant_id}, {review_id})"
        )

        return

    # --------------------------------------------------
    # Wallet branch
    # --------------------------------------------------

    if wallet:

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
                "wallet_address": f"0xSYNTHETIC{name[-2:]}"
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
                    "reason": "synthetic_signature_failure"
                },
            )

        else:

            wallet_address = (
                f"0xSYNTHETIC{name[-2:]}"
            )

            message = (
                "Synthetic acknowledgement for "
                f"{review_id}"
            )

            signature = (
                f"synthetic-signature-{participant_id}"
            )

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

    # --------------------------------------------------
    # Completion
    # --------------------------------------------------

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

    print(
        f"{name}: completed "
        f"({participant_id}, {review_id})"
    )


def main():

    scenarios = [
        # Required scenario A
        {
            "name": "User-A",
        },

        # Required scenario B
        {
            "name": "User-B",
            "wallet": True,
        },

        # Required scenario C
        {
            "name": "User-C",
            "duplicate": True,
        },

        # Required scenario D
        {
            "name": "User-D",
            "wallet": True,
            "wallet_failed": True,
        },

        # Additional normal participants
        {
            "name": "User-E",
        },
        {
            "name": "User-F",
            "wallet": True,
        },
        {
            "name": "User-G",
        },
        {
            "name": "User-H",
            "wallet": True,
        },
        {
            "name": "User-I",
        },
        {
            "name": "User-J",
            "wallet": True,
        },
    ]

    print("Generating synthetic participants...\n")

    for scenario in scenarios:
        run_scenario(**scenario)

    print("\nDone.")


if __name__ == "__main__":
    main()