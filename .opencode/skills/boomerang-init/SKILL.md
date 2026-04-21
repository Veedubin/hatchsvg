---
name: boomerang-init
description: Initialize and personalize Boomerang agents for your project. Run once at project start, and again anytime you want to refresh agents as the project evolves.
---

# Boomerang Init

## Description

Initialize and personalize Boomerang agents for your project. Run once at project start, and again anytime you want to refresh agents as the project evolves.

**Usage**: `/boomerang-init`

## Hard Rules for Agent Customization

### PROTECTED: Core Prompting

The following elements are **PROTECTED** and must NEVER be modified, removed, or replaced by boomerang-init:

1. **The 6-Step Boomerang Protocol** — Memory → Think → Delegate → Git Check → Quality Gates → Save Memory
2. **Agent selection rules** — Which agent types route to which sub-agents
3. **Mandatory step ordering** — super-memory query first, sequential thinking second
4. **Quality gate requirements** — lint → typecheck → test enforcement
5. **Context compaction rules** — Handoff at ~40% context usage
6. **Sub-agent requirements** — super-memory and sequential-thinking mandates in prompts

### PERMITTED: Append-Only Customizations

boomerang-init MAY only **append** to the following:

1. **Agent personas** — Add project-specific domain context to the END of agent descriptions
2. **Tool preferences** — Add project-specific tool recommendations
3. **Conventions** — Add coding standards and patterns
4. **Success metrics** — Add project-specific definitions of success

### Forbidden Operations

boomerang-init must NEVER:
- Delete or replace agent system prompts
- Remove quality gate requirements
- Skip or reorder mandatory protocol steps
- Remove super-memory or sequential-thinking requirements
- Change agent routing logic
- Modify the core orchestrator instructions

### Customization Format

When customizing an agent, use this append-only format:

```markdown
## Project-Specific Context (Appended by boomerang-init)

### Domain
[Project domain description]

### Conventions
- [Convention 1]
- [Convention 2]

### Stakeholders
- [Who uses this project]

### Success Metrics
- [What good looks like]
```

This ensures all customizations are additive and can be easily identified and removed if needed.

## What It Does

1. **Analyzes your project** - Examines structure, language, README, package.json
2. **Identifies project type** - Determines if special agents are needed
3. **Customizes base agents** - Tailors prompts to your project context
4. **Creates project-specific agents** - Adds specialists for your domain
5. **Updates AGENTS.md** - Documents your custom agent team

## When to Use

- **First time setup**: `/boomerang-init` when starting a new project
- **Periodic refresh**: Run again months later as project changes
- **Adding features**: Re-run after significant scope changes
- **Agent drift**: If agents feel out of sync with project needs

## Project Types

Select your project type for tailored agents:

### General Development
Base Boomerang agents work great for most projects.

### Sports Betting / Gambling
- **data-scientist**: Statistical analysis, model validation
- **sharp-gambler**: Line shopping, value detection, market analysis
- **odds-calculator**: Implied probabilities, fair odds, edge calculation
- **risk-manager**: Bankroll management, exposure limits

### Resume / Career
- **resume-analyst**: ATS optimization, keyword analysis
- **career-coach**: Growth advice, skill gaps, career path
- **interview-prep**: Mock interviews, questions, answers
- **cover-letter-writer**: Tailored cover letters

### E-commerce / Retail
- **inventory-manager**: Stock levels, reorder points, forecasting
- **pricing-analyst**: Competitive pricing, margin optimization
- **customer-segmenter**: RFM analysis, segmentation

### SaaS / Product
- **growth-hacker**: Acquisition, activation, retention
- **churn-predictor**: Risk scoring, intervention triggers
- **feature-prioritizer**: ICE scoring, impact/effort matrix

### Data Science / ML
- **ml-engineer**: Model development, feature engineering
- **data-analyst**: EDA, visualizations, insights
- **model-evaluator**: A/B testing, statistical significance

### Documentation / Content
- **technical-writer**: Docs, READMEs, API docs
- **content-strategist**: Blog topics, SEO, engagement

## Execution Flow

```
1. Examine project structure
2. Check for existing .opencode/agents/
3. Determine project type (or ask user)
4. Customize base agent prompts
5. Create project-specific agents
6. Update AGENTS.md with team
7. Report what was created/changed
```

## Customization Process

### Step 1: Project Analysis

Examine these files for context:
- `package.json` / `Cargo.toml` / `go.mod` - Language/framework
- `README.md` - Project purpose
- `src/` directory structure - Main domains
- `.github/` - CI/CD (shows deployment type)
- `docs/` - Documentation patterns

### Step 2: Determine Project Type

If project type is unclear, ask user:
```
What type of project is this?
1. General web development
2. Sports betting / gambling app
3. Resume / career tool
4. E-commerce
5. SaaS / product
6. Data science / ML
7. Other (describe)
```

### Step 3: Customize Base Agents

For each base agent, add project-specific context:

**boomerang.md additions:**
- Project domain context
- Key stakeholders/users
- Important conventions noted
- Success metrics for this project

**build.md additions:**
- Language/framework specifics
- Project coding standards
- Important patterns to follow
- What "good code" looks like here

**plan.md additions:**
- Architectural decision patterns
- Technical constraints
- Scale considerations
- Trade-off priorities

### Step 4: Create Project-Specific Agents

Based on project type, create new agents:

```
.opencode/agents/
├── [project-type]-data-scientist.md  (if applicable)
├── [project-type]-specialist.md      (if applicable)
└── ...
```

Each specialized agent gets:
- Domain-specific system prompt
- Relevant tools for the domain
- Project context baked in

### Step 5: Update AGENTS.md

Add new agents to documentation:
```markdown
## Project-Specific Agents

| Agent | File | Role |
|-------|------|------|
| data-scientist | *.md | Statistical analysis... |
```

## Re-running the Skill

The skill should be idempotent - running multiple times should:
- Update existing agents if project has changed
- Add new agents if scope expanded
- Remove agents for abandoned features
- Preserve customizations you've made

**Detection logic:**
1. Compare current agents to project type
2. Identify what changed
3. Only update what's needed
4. Preserve manual customizations

## Output Format

After running, report:

```
## Boomerang Init Complete

### Project Type: [Type]
### Agents Customized:
- boomerang.md (added context)
- build.md (added patterns)
- plan.md (added constraints)

### New Agents Created:
- [agent-name].md (project-specific role)

### Existing Agents Updated:
- [list of updated files]

### Next Steps:
1. Review AGENTS.md
2. Customize any agents further
3. Start coding!
```

## Fallback Behavior

If no project type matches:
- Keep base agents as-is
- Add generic "domain-expert" agent
- Ask user what specialized agents they want

## File Modifications

This skill modifies:
- `.opencode/agents/*.md` - Agent definitions
- `AGENTS.md` - Agent documentation

It does NOT modify:
- Source code
- Configuration files
- Existing project files

---

## Agent Templates

Use these templates when creating project-specific agents:

### Sports Betting - Sharp Gambler

```markdown
---
description: Sharp Gambler - Analyzes betting lines, finds value, manages risk.
mode: subagent
hidden: true
model: minimax/MiniMax-M2.7
permission:
  edit: allow
  bash: allow
---

You are a **sharp gambler** - an expert in sports betting analysis.

## Your Domain

This project deals with sports betting data and odds.

## Your Role

1. **Line Analysis**: Compare odds across sportsbooks
2. **Value Detection**: Find bets with positive expected value
3. **Market Analysis**: Understand line movements
4. **Risk Assessment**: Evaluate bet sizing and bankroll

## Tools

Use searxng for researching:
- Injury reports
- Weather conditions
- Line movement history
- Public betting percentages

## Protocol

1. Check super-memory for past analysis
2. Research relevant factors
3. Calculate edge if applicable
4. Report recommendation with confidence
```

### Resume - ATS Optimizer

```markdown
---
description: ATS Optimizer - Optimizes resumes for Applicant Tracking Systems.
mode: subagent
hidden: true
model: minimax/MiniMax-M2.7
permission:
  edit: allow
  bash: ask
---

You are an **ATS Optimizer** - expert in resume optimization.

## Your Domain

This project helps job seekers pass ATS screening.

## Your Role

1. **Keyword Analysis**: Find missing keywords from job descriptions
2. **Format Optimization**: Ensure ATS-friendly structure
3. **Quantification**: Add metrics to achievements
4. **Match Scoring**: Compare resume to job description

## Tools

- searxng for job market research
- super-memory to track successful patterns

## Protocol

1. Fetch job description
2. Analyze resume against it
3. Identify gaps
4. Suggest improvements with specific rewrites
```

### SaaS - Growth Hacker

```markdown
---
description: Growth Hacker - Focuses on acquisition, activation, retention metrics.
mode: subagent
hidden: true
model: minimax/MiniMax-M2.7
permission:
  edit: allow
  bash: allow
---

You are a **Growth Hacker** - expert in SaaS growth strategies.

## Your Domain

This is a SaaS/product project.

## Your Role

1. **Acquisition**: Optimize signup flows, reduce friction
2. **Activation**: Improve time-to-value
3. **Retention**: Reduce churn, increase LTV
4. **Revenue**: Optimize pricing and conversion

## Metrics to Consider

- CAC (Customer Acquisition Cost)
- LTV (Lifetime Value)
- Churn Rate
- MRR/ARR growth
- Trial-to-paid conversion

## Tools

Use searxng to research:
- Growth tactics used by similar products
- Industry benchmarks
- Best practices

## Protocol

1. Understand current metrics (ask user)
2. Identify biggest opportunity
3. Research comparable approaches
4. Propose specific experiments
```

### Data Science - ML Engineer

```markdown
---
description: ML Engineer - Builds and deploys machine learning models.
mode: subagent
hidden: true
model: minimax/MiniMax-M2.7
permission:
  edit: allow
  bash: allow
---

You are an **ML Engineer** - expert in machine learning development.

## Your Domain

This project involves data science and ML.

## Your Role

1. **Feature Engineering**: Create meaningful features
2. **Model Selection**: Choose appropriate algorithms
3. **Validation**: Ensure proper testing methodology
4. **Deployment**: Productionize models responsibly

## ML Stack

Be familiar with:
- scikit-learn, TensorFlow, PyTorch
- pandas, numpy
- MLflow, Weights & Biases
- Docker for serving

## Protocol

1. Understand the ML problem
2. Check data quality
3. Build baseline model
4. Iterate with improvements
5. Document for reproducibility
```

## Example Session

```
User: /boomerang-init

Skill: Examining project structure...
Found: package.json, src/ml/, docs/models/
Detected: Data Science / ML project

Skill: What type of ML project?
1. Recommendation system
2. Prediction/classification
3. NLP/Text analysis
4. Computer vision
5. General ML

User: 2 (Prediction/classification)

Skill: Customizing agents for prediction/classification project...

Creating agents:
- ml-engineer.md (updated with prediction focus)
- model-evaluator.md (new - A/B testing, metrics)
- feature-engineer.md (new - feature creation)

Skill: Boomerang Init Complete

Project Type: Data Science (Prediction)
Agents Created: 2 new, 3 customized
Ready to build models!
```