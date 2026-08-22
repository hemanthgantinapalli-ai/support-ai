# Policy-Driven Approval Agent

This project is a lightweight approval workflow app built for Supervity Problem 4: Policy-Driven Approval Agent.

## What it does

- Accepts plain-English business rules as configuration
- Applies a rule set to a batch of sample expense claims
- Produces an approve, reject, or escalate outcome per claim
- Shows a clear rationale tied to the matching rule and claim values
- Lets a non-technical reviewer change policy directly in the UI

## Why this approach

The solution keeps the policy layer transparent and configurable instead of hardcoded. It uses a deterministic rule parser for common business-language patterns, which makes the decision trail easy to audit and explains the tradeoff in a client-facing demo.

## Run locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the application:
   ```bash
   streamlit run app.py
   ```
3. Open the local URL shown in the terminal.

## Default rules

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
- The traceability panel explains which rule and condition led to the decision.
- The configuration is editable in the Streamlit sidebar without changing source code.
