# CLAUDE.md

## Project Context

This repository documents an 8-week intensive self-development program aimed at building practical experience in AI/ML data management and engineering.
The focus is on hands-on implementation of data-centric AI projects using modern tooling and best practices.

## Repository Structure

```
self-boost-8week-project/
├── projects/           # Individual project implementations
│   └── [project-name]/ # Each project as a separate module
├── til/                # Daily learning logs (Today I Learned)
│   └── tpl.md         # Template for daily entries
├── CLAUDE.md          # This file - context for AI assistants
└── README.md          # Human-readable project overview (Korean)
```

## Technology Stack
- **Language**: Python 3.14
- **Package Manager**: `uv` (fast Python package installer and resolver)
- **Project Organization**: Modular structure under `projects/` directory
- **Documentation**: Daily TIL entries tracking progress and learnings

## Working with This Repository

### For AI Assistants (Claude)

When assisting with this project:

1. **Understand the Goal**: Each task should contribute to building AI Data Manager competencies
2. **Follow the Structure**: Use `projects/` for implementations, `til/` for daily logs
3. **Use Modern Tools**: Leverage Python 3.14 features and `uv` for dependency management
4. **Maintain Quality**: Write production-quality code with proper error handling and documentation
5. **Track Progress**: Help update TIL entries with accomplishments and learnings
6. **Stay Focused**: Avoid over-engineering; build practical, demonstrable skills

### Project Setup Pattern

Each new project should follow this initialization:

```bash
cd projects
mkdir project-name
cd project-name
uv init
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Commit Convention

Use conventional commit messages:
- `feat: add table extraction module`
- `fix: resolve PDF parsing encoding issue`
- `docs: update TIL for day 15`
- `refactor: optimize image preprocessing pipeline`
