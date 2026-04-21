---
name: boomerang-handoff
description: Wrap-up function for ending a session cleanly. Updates all documentation files and saves context for the next session.
---

# Boomerang Handoff

## Description

Wrap-up function for ending a session cleanly. Updates AGENTS.md, TASKS.md, HANDOFF.md, and README.md with current state, then saves context to super-memory. Run this when you want to "wrap it up" and start fresh in a new session.

**Usage**: `/handoff`

## What It Does

1. **Updates AGENTS.md** — Documents all current agents, their roles, and their models
2. **Updates TASKS.md** — Captures current task state, what's done, what's pending
3. **Updates HANDOFF.md** — Summarizes session accomplishments, decisions made, and where to resume
4. **Updates README.md** — Ensures project documentation stays current (if changes were made)
5. **Saves to super-memory** — Persists all critical context for the next session
6. **Optional: Compaction** — Calls context compaction agent if available

## When to Use

- **End of session**: User says "wrap it up", "done for now", "let's stop"
- **Context limit approaching**: When context usage reaches ~40%, run handoff before compaction
- **Major milestone**: After completing a significant feature or phase
- **Switching topics**: Before moving to a completely different area of work

## Handoff Process

```
1. Gather current state from all active agents
2. Update AGENTS.md with current agent roster
3. Update TASKS.md with task status
4. Write HANDOFF.md with session summary
5. Update README.md if project changed
6. Save all context to super-memory
7. (Optional) Trigger context compaction
8. Report handoff complete
```

## File Update Details

### AGENTS.md

Documents:
- All active agents and their roles
- Models assigned to each agent
- Any customizations or special instructions
- New agents created during the session

### TASKS.md

Captures:
- Completed tasks (with checkmarks)
- In-progress tasks (with current status)
- Pending tasks (backlog)
- Blocked tasks (with blockers noted)

### HANDOFF.md

Summarizes:
- Session date and duration
- What was accomplished
- Key decisions made
- Code changes summary
- Where to resume next session
- Any warnings or important notes
- Reference to super-memory for detailed context

### README.md

Updates (only if project structure changed):
- Architecture changes
- New features added
- Installation steps modified
- Configuration changes

## Output Format

After running, report:

```
## Handoff Complete ✓

### Files Updated:
- AGENTS.md (X agents documented)
- TASKS.md (X tasks tracked)
- HANDOFF.md (session summary written)
- README.md (updated if needed)

### Super-Memory:
- Saved session context
- Key decisions persisted
- Ready for next session

### Next Session:
1. Read HANDOFF.md for resume point
2. Read TASKS.md for current priorities
3. Query super-memory for full context
```

## Fallback Behavior

If any file update fails:
- Log the failure
- Save as much as possible to super-memory
- Report what succeeded and what failed
- Suggest manual fixes if needed
