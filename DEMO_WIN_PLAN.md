# FairnessOps Demo Win Plan (12-14 Hour Sprint)

## Goal

Win on credibility: a live, clinically grounded fairness operations demo that feels production-ready for hospital leadership.

## Strategic Call: Multi-tenant Now?

**Recommendation: do NOT implement multi-tenant before demo.**

Why:
- It is high engineering cost and low visible demo impact.
- Judges will score clinical relevance, reliability, clarity, and trust faster than tenancy architecture.
- You can describe multi-tenant as a near-term roadmap item without risking current polish.

Roadmap phrasing for judges:
- "Current deployment is single-org for safety and validation speed."
- "Tenant isolation (schema/RLS per org) is designed and next in line after pilot."

## Demo Narrative (What to Show in 5 Minutes)

1. **Live model monitoring**
   - Scheduler streams new predictions every cycle.
   - Fairness worker runs automatically and updates dashboard in realtime.
2. **Clinical risk framing**
   - Show "Immediate Review" vs "Monitor Closely" findings.
   - Explain patient impact in plain language, not metric jargon.
3. **Actionability**
   - Show one high-risk subgroup issue.
   - Show recommended care-ops next action.
4. **Model reliability drift**
   - Show PELT changepoints and explain operational meaning.
5. **Closed-loop alerting**
   - Show Slack alert and triage workflow.

## Priority Backlog (Order Matters)

## P0 - Must Ship (Demo Critical)

1. **Realtime reliability**
   - Confirm live feed never appears empty after refresh.
   - Keep latest run seeded in UI while waiting for next insert.
2. **Clinical language standardization**
   - Replace remaining technical labels with clinician-facing terms.
   - Keep numeric values as secondary context.
3. **Data volume stability**
   - Keep `PREDICT_BATCH_SIZE=250` (or `300`) for robust subgroup coverage.
4. **PELT visibility**
   - Keep changepoint markers and baseline/current/drop summary visible in drift tab.
5. **Demo script + fallback**
   - Have one primary model (`synthetic_monitor_v1`) and one backup URL.

## P1 - Strong Differentiators (If Time)

1. **Clinical metadata quality**
   - Ensure every run includes: use case, outcome, population, department, compliance note.
2. **Top 3 actions panel**
   - Add one compact "What to do now" card for current run.
3. **Small run quality guardrail**
   - Show "low sample caution" badge for underpowered subgroup findings.

## P2 - Post-Demo / Mention as Roadmap

1. Multi-tenant org isolation.
2. SSO/RBAC.
3. Audit export and PDF packet.
4. Model onboarding wizard.

## Clinical Accuracy Standardization Checklist

- Outcome wording uses clinical phrasing ("high deterioration risk", "missed-care gap").
- No fake percentages from raw counts.
- Representation issues framed as data sufficiency risk, not model failure.
- Distinguish fairness risk from performance drift in explanations.
- Compliance text is consistent across critical alerts.

## Accessibility and Production UX Checklist

- Color is not the only signal (labels/icons for severity).
- Contrast stays readable in dark mode panels.
- Tab order and keyboard focus are visible.
- Tooltips and chart labels are understandable without jargon.
- Empty/loading/error states are explicit and non-technical.
- Numbers use consistent formatting and units.

## Operational Runbook for Demo Day

1. Start API (`8000`), dashboard (`3000`), scheduler (synthetic mode).
2. Verify `/health` and model selector shows `synthetic_monitor_v1`.
3. Wait one worker cycle, confirm:
   - New `run_id`
   - Non-empty live updates
   - Drift panel updates with changepoints summary
4. Trigger backup talking path if data is sparse:
   - Emphasize low-sample caution handling and safe interpretation.
5. Keep one screenshot backup per section in case conference Wi-Fi is unstable.

## Judge-Facing One-Liner

"FairnessOps is a realtime clinical fairness command center: it continuously monitors subgroup safety signals, explains them in clinician language, and routes immediate actions before inequity reaches patient care."

