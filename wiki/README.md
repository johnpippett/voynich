# Project Wiki

This repo keeps durable project documentation in decimal-numbered markdown files.
Use it as the canonical record of what changed, why, and how to verify it.

The numbering system is inspired by [Johnny.Decimal](https://johnnydecimal.com/)
— a simple, sortable way to organize information where the tens digit is a
**category** (10-19, 20-29, ...) and the decimal is an **ID** within that
category (11.01, 11.02, ...).

## Numbering

The full 00-99 number space is available. Predefined categories:

- `00-09 System & Meta/` — wiki index, project conventions, agent contract
  - `01 Project Conventions/`
  - `02 Wiki Index/`
- `10-19 Conversations & Decisions/`
  - `11 Key Decisions/`
  - `12 Session Logs/`
- `20-29 Implementation & Operations/`
  - `21 Implementation Notes/`
  - `22 Workflows/`
- `30-39 Integrations & Tooling/`
  - `31 Tool Configs/`
  - `32 Integration Notes/`
- `40-49` — available for project-specific use
- `50-59` — available for project-specific use
- `60-69` — available for project-specific use
- `70-79` — available for project-specific use
- `80-89` — available for project-specific use
- `90-99 Archive/`
  - `91 Historical Scripts/`
  - historical notes and retired content

Projects can add their own categories in the unused ranges (40-89). Create a
folder with a descriptive name and start numbering from `.01`.

File names use decimal numbers:

- `11.01 Project Documentation Policy.md`
- `12.01 Session Log Index.md`
- `21.01 Initial Architecture Decisions.md`
- `22.01 Local Development Workflow.md`
- `31.01 MCP Server Configuration.md`

Use the next available number in the most relevant folder. Prefer updating an
existing note when the topic already exists.

## Agent Rule

Any agent making meaningful project changes must create or update a wiki
note. Each note should cover:

- what changed
- why it changed
- how to verify it
- rollback notes, when relevant

If no wiki update is needed, the agent must say why in its final response.
