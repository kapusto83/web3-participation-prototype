import streamlit as st
from datetime import datetime, timezone

from wallet import wallet_component
from database import (
    init_db,
    create_participant,
    create_session,
    create_review,
    review_exists_for_session,
    log_event,
    complete_session,
    save_acknowledgement,
)


# --------------------------------------------------
# Setup
# --------------------------------------------------

st.set_page_config(
    page_title="Project Review",
    page_icon="🔎",
    layout="centered",
)

init_db()


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def now():
    return datetime.now(timezone.utc).isoformat()


def go_to(page):
    st.session_state.page = page


def log_once(event_type, **kwargs):
    """
    Prevent duplicate events when Streamlit reruns the script.
    """

    flag = f"event_logged_{event_type}"

    if not st.session_state.get(flag, False):

        log_event(
            participant_id=st.session_state.participant_id,
            event_type=event_type,
            timestamp=now(),
            session_id=st.session_state.get("session_id"),
            review_id=st.session_state.get("review_id"),
            **kwargs,
        )

        st.session_state[flag] = True


# --------------------------------------------------
# Session state
# --------------------------------------------------

if "page" not in st.session_state:

    st.session_state.page = "invite"

    # Create a new synthetic participant.
    participant_id = create_participant(now())

    st.session_state.participant_id = participant_id

    # The session begins when the participant enters the flow.
    session_id = create_session(
        participant_id=participant_id,
        started_at=now(),
    )

    st.session_state.session_id = session_id

    st.session_state.review = ""
    st.session_state.qualified = False
    st.session_state.review_id = None

    st.session_state.acknowledgement_saved = False
    st.session_state.wallet_failure_logged = False

    log_event(
        participant_id=participant_id,
        session_id=session_id,
        event_type="invited",
        timestamp=now(),
    )


# --------------------------------------------------
# Invitation
# --------------------------------------------------

if st.session_state.page == "invite":

    st.title("Project Review Invitation")

    st.write(
        "You have been invited to review a public project disclosure "
        "and submit a useful question or comment."
    )

    st.info(
        "Estimated time: 3 minutes\n\n"
        "Participation does not require a wallet."
    )

    st.subheader("Participation incentive")

    st.write(
        "Submit a qualified review and receive 100 participation points."
    )

    if st.button("Start review", type="primary"):

        log_once("started")

        go_to("disclosure")
        st.rerun()


# --------------------------------------------------
# Disclosure
# --------------------------------------------------

elif st.session_state.page == "disclosure":

    log_once("disclosure_viewed")

    st.title("Project Disclosure")

    st.subheader("Northstar Solar Project")

    st.write(
        """
        Northstar Solar is a fictional renewable-energy project seeking
        financing for a 25 MW solar installation.

        The project disclosure reports an estimated annual generation of
        34,000 MWh and states that construction is expected to begin in
        Q2 2027.

        The disclosure identifies the proposed site, expected capacity,
        projected operating period, and financing structure.
        """
    )

    st.divider()

    st.subheader("Your task")

    st.write(
        "Read the disclosure and submit one question or comment that "
        "would be useful for evaluating the project."
    )

    if st.button("Write a review", type="primary"):

        log_once("review_started")

        go_to("review")
        st.rerun()


# --------------------------------------------------
# Review
# --------------------------------------------------

elif st.session_state.page == "review":

    st.title("Submit your review")

    review = st.text_area(
        "What would you like the project team to clarify?",
        value=st.session_state.review,
        height=180,
        placeholder=(
            "Example: The disclosure gives projected annual generation, "
            "but does not explain what assumptions were used for the estimate."
        ),
    )

    if st.button("Submit review", type="primary"):

        st.session_state.review = review.strip()

        # --------------------------------------------------
        # Duplicate protection
        # --------------------------------------------------

        if review_exists_for_session(
            st.session_state.session_id
        ):

            log_once(
                "duplicate_detected",
                metadata={
                    "reason": "review_already_exists_for_session"
                },
            )

            st.warning(
                "A review has already been submitted for this "
                "participation session."
            )

        # --------------------------------------------------
        # Qualification
        # --------------------------------------------------

        elif len(st.session_state.review) >= 40:

            st.session_state.qualified = True

            review_id = create_review(
                session_id=st.session_state.session_id,
                participant_id=st.session_state.participant_id,
                content=st.session_state.review,
                qualified=True,
                created_at=now(),
            )

            st.session_state.review_id = review_id

            log_once("review_submitted")

            log_once(
                "review_qualified",
                metadata={
                    "qualification_rule": "minimum_40_characters"
                },
            )

            go_to("result")
            st.rerun()

        else:

            # We only record submission when it actually qualifies.
            # Short attempts remain inside the review step.
            st.warning(
                "This review is too short to qualify. "
                "Please provide a specific question or comment."
            )


# --------------------------------------------------
# Review result
# --------------------------------------------------

elif st.session_state.page == "result":

    st.title("Review submitted")

    if st.session_state.qualified:

        st.success(
            "Your review qualifies for participation credit."
        )

        st.write("Your submission:")

        st.info(st.session_state.review)

        st.caption(
            f"Review ID: {st.session_state.review_id}"
        )

        st.divider()

        st.subheader("Optional acknowledgement")

        st.write(
            "You may optionally record a cryptographic acknowledgement "
            "with your wallet."
        )

        st.caption(
            "A wallet is not required to participate."
        )

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "Continue without wallet",
                type="primary",
                use_container_width=True,
            ):

                log_once("completed")

                complete_session(
                    st.session_state.session_id,
                    now(),
                )

                go_to("complete")
                st.rerun()

        with col2:

            if st.button(
                "Connect wallet",
                type="secondary",
                use_container_width=True,
            ):

                log_once("wallet_connect_started")

                go_to("wallet")
                st.rerun()

    else:

        st.error("Your review did not qualify.")

        if st.button("Try again", type="primary"):

            go_to("review")
            st.rerun()


# --------------------------------------------------
# Wallet acknowledgement
# --------------------------------------------------

elif st.session_state.page == "wallet":

    st.title("Optional wallet acknowledgement")

    review_id = st.session_state.review_id

    message = f"""Northstar Solar Project
Review acknowledgement

Review ID: {review_id}
Action: I acknowledge that I submitted this review.

This signature does not represent asset ownership,
investment, verified reserves, or a guaranteed reward.
"""

    st.write(
        "You may optionally sign an acknowledgement "
        "with your wallet."
    )

    st.caption(
        "Signing does not transfer funds."
    )

    result = wallet_component(message)

    wallet = result.get("wallet")
    signature = result.get("signature")
    wallet_error = result.get("error")

    # --------------------------------------------------
    # Wallet connected
    # --------------------------------------------------

    if wallet:

        log_once(
            "wallet_connected",
            metadata={
                "wallet_address": wallet["address"]
            },
        )

        st.success("Wallet connected")

        st.write("Wallet address:")

        st.code(wallet["address"])

    # --------------------------------------------------
    # Acknowledgement signed
    # --------------------------------------------------

    if signature:

        log_once("acknowledgement_requested")

        if not st.session_state.acknowledgement_saved:

            save_acknowledgement(
                participant_id=st.session_state.participant_id,
                review_id=review_id,
                wallet_address=signature["address"],
                message=signature["message"],
                signature=signature["signature"],
                acknowledged_at=now(),
            )

            st.session_state.acknowledgement_saved = True

            log_once("acknowledgement_signed")

        st.success("Acknowledgement signed.")

        st.write("Signature:")

        st.code(signature["signature"])

        if st.button("Continue", type="primary"):

            log_once("completed")

            complete_session(
                st.session_state.session_id,
                now(),
            )

            go_to("complete")
            st.rerun()

    # --------------------------------------------------
    # Wallet/signature failure
    # --------------------------------------------------

    elif wallet_error:

        if not st.session_state.wallet_failure_logged:

            log_event(
                participant_id=st.session_state.participant_id,
                session_id=st.session_state.session_id,
                review_id=st.session_state.review_id,
                event_type="acknowledgement_failed",
                timestamp=now(),
                metadata={
                    "error": str(wallet_error)
                },
            )

            st.session_state.wallet_failure_logged = True

        st.warning(
            "The wallet acknowledgement could not be completed. "
            "Your qualified review is still valid."
        )

        if st.button(
            "Continue without wallet",
            type="primary",
            use_container_width=True,
        ):

            log_once("completed")

            complete_session(
                st.session_state.session_id,
                now(),
            )

            go_to("complete")
            st.rerun()

    # --------------------------------------------------
    # No wallet / user chooses to continue
    # --------------------------------------------------

    elif st.button(
        "Continue without wallet",
        type="primary",
        use_container_width=True,
    ):

        log_once("completed")

        complete_session(
            st.session_state.session_id,
            now(),
        )

        go_to("complete")
        st.rerun()


# --------------------------------------------------
# Completion
# --------------------------------------------------

elif st.session_state.page == "complete":

    st.title("Participation complete")

    st.success(
        "Thank you. Your review has been recorded."
    )

    st.write(
        "Your participation is complete. Any optional wallet "
        "acknowledgement is separate from qualification."
    )

    st.caption(
        f"Participant: {st.session_state.participant_id}"
    )

    st.caption(
        f"Review: {st.session_state.review_id}"
    )

    if st.button("Start over"):

        st.session_state.clear()
        st.rerun()
