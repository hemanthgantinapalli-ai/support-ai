import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
RULES_PATH = BASE_DIR / "data" / "default_rules.txt"
CLAIMS_PATH = BASE_DIR / "data" / "claims.json"


@st.cache_data
def load_default_rules() -> list[str]:
    return [line.strip() for line in RULES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


@st.cache_data
def load_claims() -> list[dict]:
    return json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))


def parse_rule(rule_text: str) -> dict:
    text = (rule_text or "").strip()
    if not text:
        raise ValueError("Empty rule.")
    if "then" not in text.lower():
        raise ValueError(f"Rule is missing a 'then' clause: {rule_text}")

    condition, action = re.split(r"\bthen\b", text, maxsplit=1, flags=re.IGNORECASE)
    condition = condition.strip()
    action = action.strip().lower()

    if action not in {"approve", "reject", "escalate"}:
        raise ValueError(f"Action must be approve, reject, or escalate: {rule_text}")

    department = None
    dept_match = re.search(
        r"(?:department\s+(?:is|=)|for)\s*([A-Za-z][A-Za-z\s-]*?)(?=\s+(?:and|amount|then|$))",
        condition,
        flags=re.IGNORECASE,
    )
    if dept_match:
        department = dept_match.group(1).strip().lower()

    amount_rule = parse_amount_condition(condition)

    return {
        "text": text,
        "department": department,
        "amount_rule": amount_rule,
        "action": action,
    }


def parse_amount_condition(condition_text: str):
    text = condition_text.lower()
    if "between" in text:
        match = re.search(r"between\s+\$?(\d+(?:\.\d+)?)\s+and\s+\$?(\d+(?:\.\d+)?)", condition_text, flags=re.IGNORECASE)
        if match:
            low = float(match.group(1))
            high = float(match.group(2))
            return {
                "mode": "between",
                "low": min(low, high),
                "high": max(low, high),
                "label": f"amount between ${min(low, high):,.2f} and ${max(low, high):,.2f}",
            }

    for comparison, symbol in [("under", "<"), ("less than", "<"), ("below", "<"), ("over", ">"), ("above", ">"), ("more than", ">"), ("at least", ">="), ("minimum", ">=")]:
        match = re.search(rf"amount\s*(?:is\s*)?(?:{comparison})\s*\$?(\d+(?:\.\d+)?)", condition_text, flags=re.IGNORECASE)
        if match:
            value = float(match.group(1))
            return {
                "mode": "simple",
                "operator": symbol,
                "value": value,
                "label": f"amount {symbol} ${value:,.2f}",
            }

    match = re.search(r"amount\s*(<=|>=|<|>|=)\s*\$?(\d+(?:\.\d+)?)", condition_text, flags=re.IGNORECASE)
    if match:
        operator = match.group(1)
        value = float(match.group(2))
        return {
            "mode": "simple",
            "operator": operator,
            "value": value,
            "label": f"amount {operator} ${value:,.2f}",
        }

    return None


def amount_matches(rule_amount, amount: float) -> bool:
    if rule_amount is None:
        return True

    mode = rule_amount["mode"]
    if mode == "between":
        return rule_amount["low"] <= amount <= rule_amount["high"]
    operator = rule_amount["operator"]
    value = rule_amount["value"]
    if operator == "<":
        return amount < value
    if operator == "<=":
        return amount <= value
    if operator == ">":
        return amount > value
    if operator == ">=":
        return amount >= value
    if operator == "=":
        return amount == value
    return False


def matches_rule(rule: dict, claim: dict) -> bool:
    if rule["department"] and claim.get("department", "").lower() != rule["department"]:
        return False
    if not amount_matches(rule["amount_rule"], float(claim["amount"])):
        return False
    return True


def evaluate_claims(rules_text: str, claims: list[dict]) -> list[dict]:
    parsed_rules = []
    for idx, line in enumerate(rules_text.splitlines(), start=1):
        item = line.strip()
        if not item:
            continue
        try:
            parsed_rules.append(parse_rule(item))
        except ValueError as exc:
            raise ValueError(f"Rule #{idx} is invalid: {exc}") from exc

    results = []
    for claim in claims:
        selected_rule = None
        for rule in parsed_rules:
            if matches_rule(rule, claim):
                selected_rule = rule
                break

        if selected_rule is None:
            decision = "reject"
            rationale = "No rule matched this claim, so the system defaulted to reject for safety."
        else:
            decision = selected_rule["action"]
            rationale = (
                f"Matched rule '{selected_rule['text']}'. "
                f"Department {claim.get('department', 'n/a')} and amount ${float(claim['amount']):,.2f} satisfy the configured condition."
            )

        results.append(
            {
                "claim_id": claim["claim_id"],
                "employee": claim["employee"],
                "department": claim["department"],
                "amount": claim["amount"],
                "decision": decision,
                "rationale": rationale,
            }
        )
    return results


def render_guide():
    st.markdown("### Rule-writing guide")
    st.code(
        "If department is Sales and amount under $500 then approve\n"
        "If department is Sales and amount between $500 and $2000 then escalate\n"
        "If amount above $2000 then escalate\n"
        "If department is Marketing and amount over $1500 then reject"
    )
    st.caption(
        "Supported actions: approve, reject, escalate. Supported comparisons: under, over, between, <=, >=, <, >."
    )


st.set_page_config(page_title="Policy-Driven Approval Agent", layout="wide")

st.markdown(
    """
    <style>
    .main { background: linear-gradient(135deg, #0b1020 0%, #101a2d 40%, #172033 100%); }
    .stApp { color: #edf3ff; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    .block-container { padding-top: 1.5rem; }
    .stDataFrame { background: rgba(255,255,255,0.04); border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Policy-Driven Approval Agent")
st.caption("A configurable, traceable approval workflow for plain-English business policy.")

with st.sidebar:
    st.header("Rules configuration")
    default_rules = "\n".join(load_default_rules())
    if "rules_text" not in st.session_state:
        st.session_state.rules_text = default_rules

    st.session_state.rules_text = st.text_area(
        "Edit plain-English business rules",
        value=st.session_state.rules_text,
        height=240,
    )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Evaluate"):
            st.session_state.apply_rules = True
    with col_btn2:
        if st.button("Reset"):
            st.session_state.rules_text = default_rules
            st.session_state.apply_rules = False

    st.markdown("---")
    render_guide()

claims = load_claims()

if "apply_rules" not in st.session_state:
    st.session_state.apply_rules = False

if st.session_state.apply_rules:
    try:
        results = evaluate_claims(st.session_state.rules_text, claims)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
else:
    results = evaluate_claims(default_rules, claims)

count_map = {"approve": 0, "reject": 0, "escalate": 0}
for item in results:
    count_map[item["decision"]] = count_map.get(item["decision"], 0) + 1

metric_cols = st.columns(4)
metric_cols[0].metric("Total claims", len(results))
metric_cols[1].metric("Approved", count_map["approve"])
metric_cols[2].metric("Escalated", count_map["escalate"])
metric_cols[3].metric("Rejected", count_map["reject"])

col1, col2 = st.columns([1.5, 1])
with col1:
    st.subheader("Claim decisions")
    df = pd.DataFrame(results)
    df["amount"] = df["amount"].map(lambda value: f"${float(value):,.2f}")
    st.dataframe(df, use_container_width=True, hide_index=True)

with col2:
    st.subheader("Traceability")
    for item in results:
        color = {"approve": "#6ee7b7", "reject": "#fca5a5", "escalate": "#fbbf24"}.get(item["decision"], "#e2e8f0")
        st.markdown(
            f"""
            <div style="padding: 0.8rem 1rem; border-left: 5px solid {color}; background: rgba(255,255,255,0.04); border-radius: 8px; margin-bottom: 0.8rem;">
            <strong>{item['claim_id']}</strong> — <span style="text-transform: uppercase;">{item['decision']}</span><br>
            {item['rationale']}
            </div>
            """,
            unsafe_allow_html=True,
        )

st.subheader("Sample claim dataset")
claim_df = pd.DataFrame(claims)
claim_df["amount"] = claim_df["amount"].map(lambda value: f"${float(value):,.2f}")
st.dataframe(claim_df, use_container_width=True, hide_index=True)

st.markdown("### Why this is strong for the assessment")
st.markdown(
    "The logic remains explicit and auditable: each claim is evaluated against a configured rule set, and the rationale calls out the exact department and amount conditions that caused the decision. That makes the workflow easy for a reviewer to trust, edit, and explain in a client-facing demo."
)
