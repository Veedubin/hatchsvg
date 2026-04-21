---
name: boomerang-compactor
description: Context compaction specialist. Summarizes long conversation threads, preserves critical context, removes redundancy, and outputs a compact session summary for super-memory.
---

# Boomerang Compactor

## Description

Context compaction specialist that analyzes the current conversation thread, distills it into a dense but complete session summary, and saves that summary to super-memory. Run this to keep the context window lean without losing important information.

**Usage**: `/compact` or triggered automatically at ~40% context usage.

## Triggers

Run this skill when **any** of the following apply:

| Trigger | Condition |
|---------|-----------|
| **Auto — context threshold** | Orchestrator detects context usage ≥ 40% |
| **End of session** | User says "wrap it up", "compact context", "start fresh" |
| **Explicit request** | User says `/compact` or "compact the context" |
| **Post-handoff** | Immediately after `/handoff` runs, to free context |
| **Phase transition** | Before starting a major new feature or topic |

## Model

Use **MiniMax M2.7** for fast compaction. Speed matters here — context is already growing.

---

## Compaction Protocol

### Step 1 — Inventory the Thread

Scan the current conversation and extract the following categories:

**A. User Requirements**
- Original feature requests and goals
- Constraints and preferences stated explicitly
- Acceptance criteria (if any)

**B. Architectural & Design Decisions**
- Technology choices and the reasons behind them
- Patterns adopted (naming conventions, file structure, etc.)
- Trade-offs considered and rejected alternatives

**C. Work Completed**
- Files created or modified (list with purpose)
- Bugs fixed (with root cause)
- Tests written
- Commands run and their outcomes

**D. Work In Progress / Pending**
- Tasks started but not finished
- Blocked items and their blockers
- Next steps the user or orchestrator planned

**E. Critical Code Patterns**
- Key function signatures or interfaces introduced
- Data models or schema shapes
- API contracts or integration points

**F. Warnings & Known Issues**
- Things that failed and why
- Technical debt intentionally taken
- Caveats to remember

### Step 2 — Score Each Item

For every piece of information, assign one of three scores:

| Score | Meaning | Action |
|-------|---------|--------|
| **KEEP** | Needed to continue the session correctly | Preserve verbatim or in condensed form |
| **SUMMARIZE** | Useful background but full detail not needed | Condense to 1–2 sentences |
| **DROP** | Redundant, superseded, or irrelevant | Discard entirely |

**Default to DROP for**:
- Intermediate tool outputs (grep results, file listings) already acted upon
- Back-and-forth clarifications that led to a final decision (keep only the decision)
- Repeated restatements of the same requirement
- Successful command output where only the success/failure matters

### Step 3 — Write the Compact Summary

Produce a structured markdown document following this template:

```markdown
# Compact Session Summary
**Date**: [ISO date]
**Compacted at**: [approximate % context usage]

## User Goals
- [1–3 bullet points, the core what and why]

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| [decision] | [brief reason] |

## Work Completed
| Item | Status | Notes |
|------|--------|-------|
| [file/feature/fix] | Done | [key detail] |

## Pending Work
- [ ] [task] — [context/blocker if any]

## Critical Patterns
```[lang]
[Only include if a code pattern must be remembered exactly]
```

## Warnings / Known Issues
- [item] — [why it matters]

## Resume Point
[One paragraph: where we are, what to do next, any special instructions for the next session]
```

### Step 4 — Save to Super-Memory

Call `super-memory_save_to_memory` with:
- `content`: the full compact summary text
- `metadata`: `{ "type": "compact_summary", "date": "[ISO date]", "session": "[topic or feature]" }`

If super-memory is unavailable (e.g., lance errors), write the summary to:
```
.opencode/compact-summary-[YYYY-MM-DD].md
```
and notify the orchestrator of the fallback path.

### Step 5 — Report Completion

Return a brief status message to the orchestrator:

```
## Compaction Complete ✓

- Items kept: [N]
- Items summarized: [N]
- Items dropped: [N]
- Estimated context reduction: ~[X]%
- Summary saved to: [super-memory | .opencode/compact-summary-YYYY-MM-DD.md]

### Resume Point
[One-sentence description of where the session should continue]
```

---

## Relationship to Handoff

The compactor and handoff skills are complementary but distinct:

| | `/handoff` | `/compact` |
|-|-----------|-----------|
| **Purpose** | End-of-session wrap-up | Mid-session context reduction |
| **Updates files** | AGENTS.md, TASKS.md, HANDOFF.md, README.md | Only compact-summary (if fallback) |
| **Saves to memory** | Full session context | Dense, minimal summary |
| **When to run** | Stopping work for the day | Staying in session but freeing context |
| **Triggers next action** | Close session | Continue session with leaner context |

**Recommended sequence at high context usage**:
1. Run `/handoff` — updates all docs and saves full context
2. Run `/compact` — compresses remaining context to a lean summary
3. Orchestrator re-reads AGENTS.md, TASKS.md, HANDOFF.md
4. Session continues with a clean context window

See the [boomerang-handoff skill](../boomerang-handoff/SKILL.md) for the full handoff protocol.

---

## Quality Rules

- The compact summary must be **self-contained** — a new agent reading only the summary should be able to continue the session without reading the original thread.
- **Never drop** user requirements unless they were explicitly cancelled.
- **Never drop** architectural decisions — they define the system.
- **Always include** the resume point — this is the single most important output.
- Keep the summary under **800 words** when possible. If it must be longer, flag it.

---

## Fallback Behavior

| Failure | Fallback |
|---------|----------|
| super-memory unavailable | Write to `.opencode/compact-summary-[date].md` |
| Context too large to scan | Summarize only the last 20 conversation turns |
| Ambiguous decisions | Default to KEEP and note the ambiguity in Warnings |
| No clear resume point | Ask the orchestrator for the next intended action before saving |
