# Boomerang Tasks

> **Strategic Context**: See [ROADMAP.md](./ROADMAP.md) for long-term vision and phase-based goals. This file is for tactical, immediate work.

## In Progress

### Context Compaction & Documentation

- [ ] Implement context compaction agent/skill
- [ ] Document super-memory best practices

### Testing & Integration

- [ ] Add web scraping integration tests
- [ ] Create example project initialization flow

## Next Up

### Skill Enhancements

- [ ] Review deepagents SKILL.md pattern for inspiration

### Publishing & Distribution

- [ ] Add NPM publishing documentation

### Community & Learning

- [ ] Create video/tutorial for setup

## Backlog

### Performance & Optimization

- [ ] Agent performance metrics
- [ ] Automatic agent routing optimization
- [ ] Middleware hooks production implementation

### Scalability & Extensibility

- [ ] Support for additional LLM providers
- [ ] Multi-project workspace support
- [ ] Plugin marketplace integration

## Recently Completed ✓

- [x] Update boomerang-orchestrator skill (markdown reads, sequential thinking, session start protocol, context compaction)
- [x] Update boomerang-init skill (hard rules, protect core prompting, append-only customizations)
- [x] Create boomerang-handoff skill for session wrap-up
- [x] Create boomerang-writer skill for documentation
- [x] Create boomerang-scraper skill for web research
- [x] Update all agent skills with super-memory protocol requirements
- [x] Create missing agent skills (explorer, linter, git)
- [x] Research LangChain deepagents for competitive insights
- [x] Implement context isolation for subagents
- [x] Add tool result eviction / large output offloading
- [x] Implement middleware hooks concept (wrap_model_call, wrap_tool_call)
- [x] Create/update AGENTS.md with full agent roster
- [x] Create HANDOFF.md template
- [x] Update README.md with new skills and agents
- [x] Test Boomerang on sports-bet project
- [x] Package and publish v0.2.0
- [x] Rebuilt TypeScript plugin runtime from compiled JS
- [x] Added test infrastructure with 29 passing tests

## Guidelines

- All agents must query super-memory at start and save at end
- Sequential thinking is mandatory for complex tasks
- boomerang-init must only append to default personas, never replace core prompts
- Context compaction triggers at ~40% context usage
- Handoff skill should be called before compaction to preserve state