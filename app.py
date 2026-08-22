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
        r"(?:department\s+(?:is|=)|for)\s+([A-Za-z][A-Za-z\s-]*)",
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

st.title("Policy-Driven Approval Agent")
st.caption("A configurable approval workflow that translates plain-English rules into traceable decisions.")

with st.sidebar:
    st.header("Rules configuration")
    rules_text = st.text_area(
        "Edit plain-English business rules",
        value="\n".join(load_default_rules()),
        height=220,
    )
    apply_rules = st.button("Evaluate claims")

    st.markdown("---")
    render_guide()

claims = load_claims()

if apply_rules:
    try:
        results = evaluate_claims(rules_text, claims)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
else:
    results = evaluate_claims("\n".join(load_default_rules()), claims)

col1, col2 = st.columns([1.4, 1])
with col1:
    st.subheader("Claim decisions")
    df = pd.DataFrame(results)
    df["amount"] = df["amount"].map(lambda value: f"${float(value):,.2f}")
    st.dataframe(df, use_container_width=True, hide_index=True)

with col2:
    st.subheader("Rule traceability")
    for item in results:
        st.markdown(f"**{item['claim_id']}**: {item['decision'].upper()}\n\n{item['rationale']}")
        st.markdown("---")

st.subheader("Sample claim data")
claim_df = pd.DataFrame(claims)
claim_df["amount"] = claim_df["amount"].map(lambda value: f"${float(value):,.2f}")
st.dataframe(claim_df, use_container_width=True, hide_index=True)

st.markdown("### Why this works")
st.markdown(
    "The app keeps the decision logic transparent: every claim is evaluated against the configured rules in order, and the explanation cites the specific department and amount condition that triggered the outcome. This makes it easy for a non-technical reviewer to understand, audit, and edit business policy without touching code."
)
