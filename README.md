# Policy-Driven Approval Agent

This project is a lightweight approval workflow app built for Supervity Problem 4: Policy-Driven Approval Agent.

## What it does

- Accepts plain-English business rules as configuration
- Applies those rules against a batch of sample expense claims
- Produces an approve, reject, or escalate decision per claim
- Shows a clear rationale tied to the matched rule and the claim values
- Lets a non-technical user edit rules in the UI without changing code

## Assumption

The assessment asks for a solution that can handle ambiguous business policy. In this version, the rules are intentionally plain-English and are parsed using a small rule interpreter, rather than a full LLM-powered policy engine. That keeps the logic deterministic, transparent, and easy to audit.

## Run locally

1. Create a virtual environment if desired.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   streamlit run app.py
   ```
4. Open the local URL shown in the terminal.

## Default rule examples

```text
If department is Sales and amount under $500 then approve
If department is Sales and amount between $500 and $2000 then escalate
If amount above $2000 then escalate
If department is Engineering and amount under $1000 then approve
If department is Marketing and amount over $1500 then reject
```

## Notes

- Rules are evaluated in order.
- If no rule matches, the app defaults to reject for safety.
- The rationale on the right side explains which rule applied and why.
