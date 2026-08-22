import json

from app import evaluate_claims


def test_default_rules_approve_sales_under_500():
    claims = [{"claim_id": "EXP-1", "employee": "A", "department": "Sales", "amount": 420.0}]
    rules = "If department is Sales and amount under $500 then approve"
    results = evaluate_claims(rules, claims)
    assert results[0]["decision"] == "approve"
    assert "Sales" in results[0]["rationale"]


def test_default_rules_escalate_large_sale():
    claims = [{"claim_id": "EXP-2", "employee": "B", "department": "Sales", "amount": 2200.0}]
    rules = "If department is Sales and amount between $500 and $2000 then escalate\nIf amount above $2000 then escalate"
    results = evaluate_claims(rules, claims)
    assert results[0]["decision"] == "escalate"


def test_default_rules_reject_when_no_match():
    claims = [{"claim_id": "EXP-3", "employee": "C", "department": "Support", "amount": 650.0}]
    rules = "If department is Sales and amount under $500 then approve"
    results = evaluate_claims(rules, claims)
    assert results[0]["decision"] == "reject"


def test_multiple_claims_are_processed():
    claims = json.loads(
        '[{"claim_id":"EXP-101","employee":"Priya","department":"Sales","amount":420.0},{"claim_id":"EXP-102","employee":"Daniel","department":"Engineering","amount":780.0}]'
    )
    rules = "If department is Sales and amount under $500 then approve\nIf department is Engineering and amount under $1000 then approve"
    results = evaluate_claims(rules, claims)
    decisions = [item["decision"] for item in results]
    assert decisions == ["approve", "approve"]
