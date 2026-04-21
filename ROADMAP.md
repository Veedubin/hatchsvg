# Boomerang Roadmap

## Vision/Mission

Boomerang is a multi-agent orchestration system for OpenCode that enables intelligent, context-aware task delegation across specialized AI agents. The system provides a scalable framework for building complex AI-driven development workflows with built-in memory persistence, context management, and seamless agent collaboration.

**Mission**: Empower developers to create sophisticated AI orchestration workflows through a modular, extensible agent system that maintains context across sessions and scales from simple tasks to complex multi-agent collaborations.

---

## Phase 1: Core Multi-Agent System (Completed)

### Goals
- Establish fundamental agent roles and communication patterns
- Create base skill infrastructure
- Implement super-memory integration for context persistence

### Deliverables
- [x] Initial skill creation (orchestrator, coder, tester, architect, init)
- [x] README.md with installation and configuration
- [x] Super-memory integration documentation
- [x] Basic agent roster definition
- [x] AGENTS.md with full agent roster
- [x] HANDOFF.md template for session transitions

### Agents Created
- boomerang-orchestrator (Kimi K2.5)
- boomerang-coder (MiniMax M2.7)
- boomerang-tester (Gemini 3 Pro)
- boomerang-architect (Kimi K2.5)
- boomerang-init (Kimi K2.5)

---

## Phase 2: TypeScript Runtime & Deep Agents Features (Completed)

### Goals
- Rebuild plugin runtime in TypeScript for better type safety
- Add advanced orchestration capabilities
- Enable context isolation and result offloading

### Deliverables
- [x] Rebuilt TypeScript plugin runtime from compiled JS
- [x] Added test infrastructure with 29 passing tests
- [x] Context isolation for subagents
- [x] Tool result eviction / large output offloading
- [x] Updated sports-bet project with latest Boomerang setup

### Advanced Features
- [x] Middleware hooks concept (wrap_model_call, wrap_tool_call)
- [x] Sequential thinking enforcement for complex tasks
- [x] Session start protocol (auto-read context files)
- [x] Deep research on LangChain deepagents for competitive insights

---

## Phase 3: Context Compaction, Documentation & Testing (Current)

### Goals
- Implement context compaction to handle long-running sessions
- Complete documentation for all skills and agents
- Add integration tests for web research workflows

### Deliverables
- [ ] Implement context compaction agent/skill
- [ ] Add web scraping integration tests
- [ ] Create example project initialization flow
- [ ] Document super-memory best practices

### Context Compaction Strategy
- Trigger at ~40% context usage
- Preserve critical decisions and current state
- Summarize completed work for future recall
- Handoff skill called before compaction to preserve state

### Documentation Updates
- [x] boomerang-orchestrator skill updated with markdown reads and sequential thinking
- [x] boomerang-init skill with hard rules (protect core prompting, append-only)
- [x] boomerang-handoff skill for session wrap-up
- [x] boomerang-writer skill for documentation
- [x] boomerang-scraper skill for web research
- [x] All agent skills with super-memory protocol requirements
- [x] Create/update AGENTS.md with full agent roster
- [x] Update README.md with new skills and agents

---

## Phase 4: Middleware, Performance Metrics & Routing (Planned)

### Goals
- Implement production-ready middleware hooks
- Add agent performance metrics collection
- Enable automatic agent routing optimization

### Deliverables
- [ ] Production middleware hooks implementation
- [ ] Agent performance metrics
- [ ] Automatic agent routing optimization

### Technical Considerations
- wrap_model_call and wrap_tool_call hooks ready for implementation
- Metrics collection during agent execution
- Routing optimization based on task complexity and agent performance history

---

## Phase 5: Multi-Project Workspaces, Plugin Marketplace & LLM Providers (Future)

### Goals
- Support multi-project workspace workflows
- Create plugin marketplace for community contributions
- Add additional LLM provider support

### Deliverables
- [ ] Multi-project workspace support
- [ ] Plugin marketplace integration
- [ ] Support for additional LLM providers

### LLM Provider Considerations
- OpenAI integration
- Anthropic Claude integration
- Google Gemini integration
- Local model support (Ollama, LM Studio)

---

## Strategic Principles

1. **Context Preservation**: All agents must query super-memory at start and save at end
2. **Append-Only Customization**: boomerang-init must only append to default personas, never replace core prompts
3. **Sequential Thinking**: Mandatory for complex tasks to ensure thorough reasoning
4. **Session Handoff**: Critical state must be preserved before context compaction triggers

---

## Appendix: Completed Milestones

- Initial skill creation (orchestrator, coder, tester, architect, init)
- README.md with installation and configuration
- Super-memory integration documentation
- Basic agent roster definition
- Rebuilt TypeScript plugin runtime
- Added test infrastructure (29 passing tests)
- Updated sports-bet project with latest Boomerang setup
- Package and publish v0.2.0