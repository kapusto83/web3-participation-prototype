import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# --------------------------------------------------
# Setup
# --------------------------------------------------

st.set_page_config(
    page_title="Participation Dashboard",
    page_icon="📊",
    layout="wide",
)

DB_PATH = Path(__file__).parent.parent / "data" / "prototype.db"


# --------------------------------------------------
# Database
# --------------------------------------------------

def get_connection():
    return sqlite3.connect(DB_PATH)


def query_df(sql, params=()):
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def conversion(numerator, denominator):
    if denominator == 0:
        return 0.0
    return numerator / denominator * 100


# --------------------------------------------------
# Load data
# --------------------------------------------------

participants = query_df("""
    SELECT participant_id
    FROM participants
""")

events = query_df("""
    SELECT
        event_id,
        participant_id,
        session_id,
        review_id,
        event_type,
        timestamp,
        metadata
    FROM events
    ORDER BY timestamp
""")

reviews = query_df("""
    SELECT
        review_id,
        participant_id,
        session_id,
        qualified,
        created_at
    FROM reviews
""")

acknowledgements = query_df("""
    SELECT
        participant_id,
        review_id,
        acknowledged_at
    FROM acknowledgements
""")


# --------------------------------------------------
# Page
# --------------------------------------------------

st.title("Web3 Participation Measurement")

st.caption(
    "Synthetic participation dataset and funnel measurement"
)


# --------------------------------------------------
# Event counts
# --------------------------------------------------

def unique_participants(event_type):
    return len(
        events[
            events["event_type"] == event_type
        ]["participant_id"].unique()
    )


invited = unique_participants("invited")
started = unique_participants("started")
disclosure_viewed = unique_participants("disclosure_viewed")
review_started = unique_participants("review_started")
review_submitted = unique_participants("review_submitted")
qualified = unique_participants("review_qualified")
completed = unique_participants("completed")

wallet_connected = unique_participants("wallet_connected")
ack_requested = unique_participants("acknowledgement_requested")
ack_signed = unique_participants("acknowledgement_signed")
ack_failed = unique_participants("acknowledgement_failed")
duplicates = unique_participants("duplicate_detected")


# --------------------------------------------------
# KPI row
# --------------------------------------------------

st.subheader("Key participation metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Invited", invited)

with col2:
    st.metric("Qualified reviews", qualified)

with col3:
    st.metric(
        "Qualified conversion",
        f"{conversion(qualified, invited):.0f}%",
    )

with col4:
    st.metric("Completed", completed)


# --------------------------------------------------
# Participation funnel
# --------------------------------------------------

st.divider()

st.subheader("Participation funnel")

funnel_rows = [
    ("Invited", invited, None),
    ("Started", started, invited),
    ("Disclosure viewed", disclosure_viewed, started),
    ("Review started", review_started, disclosure_viewed),
    ("Review submitted", review_submitted, review_started),
    ("Review qualified", qualified, review_submitted),
    ("Completed", completed, qualified),
]

funnel = pd.DataFrame(
    [
        {
            "Stage": stage,
            "Participants": count,
            "From previous stage": (
                "—"
                if previous is None
                else f"{conversion(count, previous):.0f}%"
            ),
            "From invited": f"{conversion(count, invited):.0f}%",
        }
        for stage, count, previous in funnel_rows
    ]
)

st.dataframe(
    funnel,
    width="stretch",
    hide_index=True,
)


# --------------------------------------------------
# Primary business metric
# --------------------------------------------------

st.subheader("Primary business metric")

primary_metric = pd.DataFrame(
    [
        {
            "Metric": "Qualified reviews / invited participants",
            "Numerator": qualified,
            "Denominator": invited,
            "Conversion": f"{conversion(qualified, invited):.0f}%",
        }
    ]
)

st.dataframe(
    primary_metric,
    width="stretch",
    hide_index=True,
)


# --------------------------------------------------
# Wallet activity
# --------------------------------------------------

st.divider()

st.subheader("Optional wallet activity")

wallet_rows = [
    ("Wallet connected", wallet_connected),
    ("Acknowledgement requested", ack_requested),
    ("Acknowledgement signed", ack_signed),
    ("Acknowledgement failed", ack_failed),
]

wallet_metrics = pd.DataFrame(
    [
        {
            "Metric": metric,
            "Participants": count,
            "% of invited": f"{conversion(count, invited):.0f}%",
        }
        for metric, count in wallet_rows
    ]
)

st.dataframe(
    wallet_metrics,
    width="stretch",
    hide_index=True,
)


# --------------------------------------------------
# Wallet acknowledgement success
# --------------------------------------------------

if ack_requested:

    st.caption(
        "Acknowledgement success rate is calculated only among "
        "participants who reached the acknowledgement request."
    )

    st.metric(
        "Acknowledgement success rate",
        f"{conversion(ack_signed, ack_requested):.0f}%",
    )


# --------------------------------------------------
# Business vs wallet
# --------------------------------------------------

st.divider()

st.subheader("Business participation vs wallet activity")

comparison = pd.DataFrame(
    [
        {
            "Metric": "Qualified reviews",
            "Participants": qualified,
            "% of invited": f"{conversion(qualified, invited):.0f}%",
        },
        {
            "Metric": "Completed participation",
            "Participants": completed,
            "% of invited": f"{conversion(completed, invited):.0f}%",
        },
        {
            "Metric": "Wallet connected",
            "Participants": wallet_connected,
            "% of invited": f"{conversion(wallet_connected, invited):.0f}%",
        },
        {
            "Metric": "Acknowledgement signed",
            "Participants": ack_signed,
            "% of invited": f"{conversion(ack_signed, invited):.0f}%",
        },
    ]
)

st.dataframe(
    comparison,
    width="stretch",
    hide_index=True,
)


# --------------------------------------------------
# Exception signals
# --------------------------------------------------

st.divider()

st.subheader("Exception signals")

exceptions = pd.DataFrame(
    [
        {
            "Signal": "Duplicate detected",
            "Participants": duplicates,
        },
        {
            "Signal": "Acknowledgement failed",
            "Participants": ack_failed,
        },
    ]
)

st.dataframe(
    exceptions,
    width="stretch",
    hide_index=True,
)


# --------------------------------------------------
# Required scenario validation
# --------------------------------------------------

st.divider()

st.subheader("Required synthetic scenarios")

participant_rows = []

for participant_id in participants["participant_id"]:

    participant_events = events[
        events["participant_id"] == participant_id
    ]

    event_types = set(
        participant_events["event_type"]
    )

    participant_rows.append(
        {
            "Participant": participant_id,
            "Invited": "invited" in event_types,
            "Qualified": "review_qualified" in event_types,
            "Wallet connected": "wallet_connected" in event_types,
            "Signed": "acknowledgement_signed" in event_types,
            "Wallet failed": "acknowledgement_failed" in event_types,
            "Duplicate": "duplicate_detected" in event_types,
            "Completed": "completed" in event_types,
        }
    )

participant_table = pd.DataFrame(participant_rows)


def find_scenario(condition):
    matches = participant_table[
        condition(participant_table)
    ]

    if matches.empty:
        return None

    return matches.iloc[0]["Participant"]


scenario_a = find_scenario(
    lambda df:
        df["Qualified"]
        & ~df["Wallet connected"]
        & df["Completed"]
        & ~df["Duplicate"]
)


scenario_b = find_scenario(
    lambda df:
        df["Qualified"]
        & df["Wallet connected"]
        & df["Signed"]
        & df["Completed"]
)


scenario_c = find_scenario(
    lambda df:
        df["Qualified"]
        & df["Duplicate"]
)


scenario_d = find_scenario(
    lambda df:
        df["Qualified"]
        & df["Wallet connected"]
        & df["Wallet failed"]
        & df["Completed"]
)


scenario_table = pd.DataFrame(
    [
        {
            "Scenario": "A — wallet declined",
            "Participant": scenario_a or "Not found",
            "Expected": "Qualified + completed",
            "Status": "PASS" if scenario_a else "FAIL",
        },
        {
            "Scenario": "B — wallet signed",
            "Participant": scenario_b or "Not found",
            "Expected": "Qualified + signed + completed",
            "Status": "PASS" if scenario_b else "FAIL",
        },
        {
            "Scenario": "C — duplicate",
            "Participant": scenario_c or "Not found",
            "Expected": "Duplicate detected",
            "Status": "PASS" if scenario_c else "FAIL",
        },
        {
            "Scenario": "D — wallet failure",
            "Participant": scenario_d or "Not found",
            "Expected": "Qualified + wallet failure + completed",
            "Status": "PASS" if scenario_d else "FAIL",
        },
    ]
)

st.dataframe(
    scenario_table,
    width="stretch",
    hide_index=True,
)


# --------------------------------------------------
# Participant-level view
# --------------------------------------------------

st.divider()

st.subheader("Participant-level event summary")

st.dataframe(
    participant_table,
    width="stretch",
    hide_index=True,
)


# --------------------------------------------------
# Raw event stream
# --------------------------------------------------

with st.expander("Raw event stream"):

    st.dataframe(
        events,
        width="stretch",
        hide_index=True,
    )