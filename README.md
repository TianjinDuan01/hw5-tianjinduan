# Week 5: Build a Reusable AI Skill

## Skill overview

I built a reusable skill called **business-hours-sla**.

This skill calculates the exact SLA breach time for a single ticket using **business-hour-aware datetime math** in a specified time zone. It counts only time that falls within defined business hours and working days, and skips off-hours and weekends.

This is not a generic chatbot or a one-off prompt. It is a narrow, reusable capability for a specific workflow: calculating SLA deadlines that depend on business time rather than simple clock time.

---

## Why I chose this skill

I chose this idea because it fits the assignment requirements well:

- it is **narrowly scoped**
- it solves a **realistic, reusable problem**
- it requires **deterministic code**
- it cannot be done as reliably with prose alone

Many teams track response or resolution SLAs for tickets, incidents, or support requests. In real workflows, SLA time often counts only during business hours. That means the calculation must correctly handle:

- business-hour boundaries
- after-hours ticket creation
- weekends
- time-zone-aware timestamps

A language model can describe the policy, but it cannot reliably perform the exact calculation across all of those rules without code. That is why the Python script is genuinely load-bearing in this skill.

---

## What the skill does

The skill takes structured input for one ticket and calculates the exact SLA breach timestamp.

### Inputs

- `ticket_id` (optional)
- `created_at`
- `sla_hours`
- `timezone`
- `business_start`
- `business_end`
- `working_days`
- `evaluated_at` (optional)

### Outputs

- exact local SLA breach timestamp
- SLA status (`within_sla` or `breached`) when `evaluated_at` is provided
- a short calculation trace showing how business time was counted

---

## Why the script is load-bearing

The Python script performs the deterministic part of the workflow. It is responsible for:

- parsing structured timestamps
- validating the IANA timezone
- validating business-hour inputs
- aligning ticket creation time to the correct business window
- skipping off-hours
- skipping non-working days
- accumulating SLA hours until the exact breach timestamp is reached
- optionally comparing `evaluated_at` against the breach time

This is the core of the skill. Without the script, the skill would not be reliable.

---

## Repository structure

```text
hw5-tianjinduan/
├─ .agents/
│  └─ skills/
│     └─ business-hours-sla/
│        ├─ SKILL.md
│        └─ scripts/
│           └─ calculate_breach.py
└─ README.md
```

---

## How to use the skill

The skill is triggered when the user asks for a business-hours-based SLA deadline, breach timestamp, remaining SLA time, or a weekend-aware SLA calculation.

The Python script can be run like this:

```bash
python3 .agents/skills/business-hours-sla/scripts/calculate_breach.py \
  --created-at "2026-10-16T16:30:00" \
  --sla-hours 4 \
  --timezone "America/Los_Angeles" \
  --business-start "09:00" \
  --business-end "17:00" \
  --working-days 0 1 2 3 4 \
  --pretty
```

---

## Script details

The skill uses one Python script:

- `calculate_breach.py`

This script is intentionally the only script in the skill because the workflow is a single deterministic computation pipeline. Splitting it into multiple scripts would add unnecessary complexity to a narrowly scoped skill.

The script includes logic for:

- input parsing with `argparse`
- timestamp normalization
- timezone validation
- business-time alignment
- business-hour accumulation
- weekend skipping
- structured JSON output

---

## Test prompts and results

I tested the skill on three prompts, as required.

### 1. Normal case

```bash
python3 .agents/skills/business-hours-sla/scripts/calculate_breach.py \
  --created-at "2026-10-16T16:30:00" \
  --sla-hours 4 \
  --timezone "America/Los_Angeles" \
  --business-start "09:00" \
  --business-end "17:00" \
  --working-days 0 1 2 3 4 \
  --pretty
```

**Expected behavior:**  
The ticket is created on Friday at 4:30 PM. Only 0.5 business hours remain that day. The weekend is skipped, and the remaining 3.5 hours are counted on Monday morning.

**Expected result:**  
SLA breach time = **Monday, October 19, 2026 at 12:30 PM**

---

### 2. Edge case

```bash
python3 .agents/skills/business-hours-sla/scripts/calculate_breach.py \
  --created-at "2026-10-16T17:00:00" \
  --sla-hours 1 \
  --timezone "America/Los_Angeles" \
  --business-start "09:00" \
  --business-end "17:00" \
  --working-days 0 1 2 3 4 \
  --pretty
```

**Expected behavior:**  
The ticket is created exactly at the end of business hours. The script should not count any time on Friday and should align the calculation to the next business window.

**Expected result:**  
SLA breach time = **Monday, October 19, 2026 at 10:00 AM**

---

### 3. Cautious / limited case

```bash
python3 .agents/skills/business-hours-sla/scripts/calculate_breach.py \
  --created-at "2026-10-16T09:00:00" \
  --sla-hours 4 \
  --timezone "LosAngeles" \
  --business-start "09:00" \
  --business-end "17:00" \
  --working-days 0 1 2 3 4 \
  --pretty
```

**Expected behavior:**  
The script should not guess the intended timezone.

**Expected result:**  
It returns an input validation error:

```json
{
  "error": "Invalid IANA timezone: LosAngeles"
}
```

This demonstrates that the skill behaves cautiously and avoids unreliable calculations when the input is invalid or ambiguous.

---

## What worked well

Several parts of this skill worked well:

- The task stayed narrow and specific.
- The script clearly handled the deterministic core of the workflow.
- The skill was easy to explain in terms of input, output, and limitations.
- The three test cases showed normal behavior, edge behavior, and cautious failure behavior.
- The idea was realistic and reusable rather than just being a generic prompt.

---

## Limitations

This version of the skill is intentionally limited in scope.

It currently:

- handles one ticket at a time
- does not support batch CSV input
- does not support holiday calendars
- does not parse free-form SLA policy text
- does not infer missing or invalid timezone information

These limitations are intentional because the goal of the assignment was to build a narrow, reliable skill rather than a broad system.

---

## What I would improve next

If I continued this project, I would consider adding:

- optional holiday support
- batch ticket input
- remaining business-time calculations
- richer status reporting
- a second mode for calculating time remaining before breach

I did not add these in this version because they would have made the skill broader than necessary for the assignment.

---

## Final reflection

This project changed how I think about the boundary between a prompt, a skill, and a tool.

At first, my instinct was to build something broader, more like a smart assistant for support workflows. But the more I worked through the assignment requirements, the more I realized that a strong skill is not just “an AI that can help with a topic.” A strong skill is a narrowly defined capability with a clear trigger, a clear handoff between language and code, and a scope that is intentionally limited. That design constraint turned out to be useful rather than restrictive.

The most important idea I learned was that a script should not be included just to satisfy the assignment. It should carry the part of the workflow that the model cannot reliably perform on its own. In this project, that deterministic part was business-time calculation. The model can explain what an SLA policy means, but it is not dependable for exact datetime arithmetic across after-hours boundaries, weekends, and time zones. Once I recognized that, the project became much easier to design: the model should orchestrate and explain, while the script should calculate.

I also learned that narrowness is a strength. Early on, it was tempting to add more features, such as holiday support, batch processing, or natural-language policy parsing. Those additions sounded impressive, but they would have weakened the skill by making it less focused and harder to explain. By keeping the scope to one ticket, one set of business-hour rules, and one deterministic script, the final skill became more coherent. It now feels like something that could realistically be reused, rather than a half-finished system trying to do too much.

Another thing that stood out to me was the importance of failure behavior. A useful skill is not only defined by what it can do, but also by what it refuses to do. The invalid-timezone test case ended up being important because it showed that the skill does not guess when the input is ambiguous or incorrect. That made the skill feel more trustworthy. In other words, reliability came not only from correct calculations, but also from clearly enforced limits.

Overall, this project helped me understand that good AI workflow design is really about deciding where natural language should end and deterministic computation should begin. That distinction is easy to blur in casual prompting, but building a reusable skill forced me to make it explicit. I think that is the main lesson I will carry forward: reusable AI systems become stronger when the model is used for interpretation and explanation, while code is used for exact, repeatable operations that should not be left to guesswork.

---

## Video walkthrough

Video link:
[YouTube Video](https://youtu.be/ZoqseBG2HpY)

This short demo shows:

- the skill folder structure
- the `SKILL.md` file
- the Python script in `scripts/`
- the skill being used through test prompts
- why the script is necessary and not decorative