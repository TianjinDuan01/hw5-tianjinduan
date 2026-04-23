---
name: business-hours-sla
description: calculate the exact sla breach time for a single ticket using business-hour-aware datetime math in a specified time zone. use when the user asks for a business-hours-based deadline, breach timestamp, remaining sla time, or weekend-aware sla calculation from a created timestamp, sla duration, working hours, and working days. do not use for batch audits, holiday calendars, or vague policy interpretation.
---

# Business Hours SLA

Use this skill to calculate the exact SLA breach time for a single ticket using deterministic business-time rules.

This skill is for cases where normal clock time is not enough. It only counts time that falls within defined business hours and working days.

## Expected inputs

This skill expects structured inputs for one ticket:

- `ticket_id`: an optional identifier for the ticket
- `created_at`: the ticket creation timestamp
- `sla_hours`: the SLA duration in hours
- `timezone`: the IANA time zone for the calculation
- `business_start`: the start of the business day in `HH:MM`
- `business_end`: the end of the business day in `HH:MM`
- `working_days`: a list of allowed working days where Monday = `0` and Sunday = `6`
- `evaluated_at`: an optional timestamp used to determine whether the ticket is currently still within SLA or already breached

Example input:

```json
{
  "ticket_id": "INC-4821",
  "created_at": "2026-10-16T16:30:00",
  "sla_hours": 4,
  "timezone": "America/Los_Angeles",
  "business_start": "09:00",
  "business_end": "17:00",
  "working_days": [0, 1, 2, 3, 4],
  "evaluated_at": "2026-10-19T10:00:00"
}
```

Example scenario:

A support ticket `INC-4821` is created at 4:30 PM on a Friday in Los Angeles. The SLA is 4 business hours. Since only business hours count, the final 3.5 hours must roll over to the next working day instead of being counted over the weekend.

## When not to use this skill

Do not use this skill for:

- general ticket prioritization
- incident severity analysis
- calendar scheduling
- batch CSV auditing
- vague policy interpretation from free-form prose
- holiday calendar lookup
- cases where the user wants you to guess a missing timezone

If the user provides incomplete or ambiguous time information, do not guess. Explain what is missing and what must be provided before the calculation can continue.

## Workflow

1. Read the structured input for one ticket.
2. Validate the timestamp, SLA hours, timezone, business hours, and working days.
3. If required input is missing or ambiguous, stop and explain what must be provided.
4. Run the script in `scripts/` to calculate the business-hours-based SLA deadline.
5. Treat the script output as the source of truth.
6. Summarize the result with:
   - the exact breach timestamp
   - the SLA status
   - a short calculation trace
7. Keep the explanation concise and deterministic. Do not invent policy rules that were not provided.

## Required checks

Before calculating, verify the following:

- `created_at` is a valid timestamp
- `sla_hours` is a positive number
- `timezone` is a valid IANA time zone string
- `business_start` and `business_end` are valid `HH:MM` times
- `business_start` is earlier than `business_end`
- `working_days` contains only integers from `0` to `6`
- if `evaluated_at` is provided, it must be a valid timestamp

If any of these checks fail, stop and explain the problem instead of guessing.

## Deterministic calculation rules

The script must do the following:

1. Parse the input timestamp.
2. Normalize the timestamp into the specified time zone.
3. Determine whether the ticket was created:
   - before business hours
   - during business hours
   - after business hours
4. Start counting SLA time only during allowed business hours.
5. Skip all time outside business hours.
6. Skip all non-working days.
7. Continue until the full SLA duration has been counted.
8. Return the exact local breach timestamp.
9. If `evaluated_at` is provided, compare it against the breach timestamp and return whether the ticket is still within SLA or already breached.

## Expected output format

Present the result as a short operational response, not as raw JSON.

Use this structure:

### SLA calculation summary

State the ticket id if available, the created time in the specified timezone, the SLA duration, and the business-hours rule used for the calculation.

### SLA result

State:

- the exact breach timestamp
- whether the ticket is still within SLA or already breached

### Calculation trace

Show a compact step-by-step trace of how business time was counted.

Example response:

**SLA calculation summary**  
Ticket `INC-4821` was created on Friday, October 16, 2026 at 4:30 PM in `America/Los_Angeles`. The SLA target is 4 business hours, and business time is counted from 09:00 to 17:00 on working days `[0, 1, 2, 3, 4]`.

**SLA result**  
The SLA breach time is Monday, October 19, 2026 at 12:30 PM local time.  
Current status: `within_sla` because `evaluated_at` is earlier than the breach timestamp.

**Calculation trace**

- Fri 16:30-17:00 counted: 0.5h
- Sat skipped: non-working day
- Sun skipped: non-working day
- Mon 09:00-12:30 counted: 3.5h
- final breach time: Mon 12:30

Keep the final response clear, short, and operational. The user should be able to read it like a support or incident update.

## Limitations

This version of the skill is intentionally narrow.

It currently:

- handles one ticket at a time
- does not support holidays
- does not support batch file input
- does not parse natural-language SLA policies
- does not infer missing timezone information

If the input is missing a timezone or uses an ambiguous timestamp, explain what the user needs to provide before the calculation can continue.

## Script usage

Use the script in `scripts/` for the actual calculation. Do not perform the business-time math manually in prose when the script is available.

The script is load-bearing because this task requires deterministic datetime arithmetic across business-hour boundaries, off-hours, weekends, and time zones.
