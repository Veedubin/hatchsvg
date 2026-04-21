# Boomerang Agent Roster

## Core Agents

| Agent | Skill | Model | Role |
|-------|-------|-------|------|
| **boomerang** | boomerang-orchestrator | Kimi K2.5 | 🎯 **Orchestrator** — Plans, coordinates, enforces protocol |
| **boomerang-coder** | boomerang-coder | MiniMax M2.7 | 💻 **Fast code generation** — Write and modify code efficiently |
| **boomerang-architect** | boomerang-architect | Kimi K2.5 | 🏗️ **Design decisions** — Trade-off analysis and architecture |
| **boomerang-explorer** | boomerang-explorer | MiniMax M2.7 | 🔍 **Codebase exploration** — Find files, search patterns, understand structure |
| **boomerang-tester** | boomerang-tester | MiniMax M2.7 | 🧪 **Testing specialist** — Unit/integration tests, verification |
| **boomerang-linter** | boomerang-linter | MiniMax M2.7 | ✅ **Quality enforcement** — Lint, format, style consistency |
| **boomerang-git** | boomerang-git | MiniMax M2.7 | 📦 **Version control** — Commits, branches, history discipline |
| **boomerang-writer** | boomerang-writer | Kimi K2.5 | 📝 **Documentation** — Markdown writing and documentation |
| **boomerang-scraper** | boomerang-scraper | MiniMax M2.7 | 🌐 **Web scraping** — Research and information gathering |
| **boomerang-compactor** | boomerang-compactor | MiniMax M2.7 | 🔄 **Context compaction** — Summarizes threads, preserves critical context |
| **researcher** | researcher | MiniMax M2.7 | 🌐 **Web research** — Search, fetch, and synthesize online information |

## Special Skills

| Skill | Purpose | Model |
|-------|---------|-------|
| **boomerang-init** | Initialize and personalize agents for a project | Kimi K2.5 |
| **boomerang-handoff** | Wrap-up session. Updates docs, saves context | Kimi K2.5 |

## Agent Selection Guide

- **Orchestration / coordination** → `boomerang`
- **Code implementation / bug fixes** → `boomerang-coder`
- **Planning / design / architecture** → `boomerang-architect`
- **Code exploration / finding files** → `boomerang-explorer`
- **Writing tests** → `boomerang-tester`
- **Linting / formatting** → `boomerang-linter`
- **Git operations** → `boomerang-git`
- **Documentation / markdown** → `boomerang-writer`
- **Web research** → `researcher` or `boomerang-scraper`
- **Session initialization** → `boomerang-init`
- **Session wrap-up** → `boomerang-handoff`
- **Context compaction** → `boomerang-compactor`

## Super-Memory Requirements

All agents MUST:
1. Query super-memory before starting work
2. Save results to super-memory when complete
3. Use sequential-thinking for complex tasks

## Project-Specific Context

**Project**: png2svg - A Python CLI tool that converts PNG images to hatched SVG files for Cricut pen plotting.

### Tech Stack
- Python 3 with argparse CLI
- NumPy for image array processing
- Pillow (PIL) for image I/O
- dataclasses for data structures (RenderParams, LayerResult, StrokeStyle)
- JSON for session and palette serialization

### Project Structure
- Single-file script: `png2svg.py` (~870 lines)
- Color palettes in `color_palettes/` directory (JSON format)
- Sample images for testing: `Bluey.png`, `Bluey-orig.png`

### Success Criteria
- Clean SVG output for Inkscape/Cricut Design Space
- Accurate marker color matching
- Session save/load reproducibility
- Clear CLI help text

This is the Boomerang multi-agent orchestration system for OpenCode.