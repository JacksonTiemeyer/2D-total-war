# Documentation Index for Claude Code Context

This directory contains machine-friendly Markdown docs that describe the key scripts in the codebase. Claude Code uses these docs to quickly understand data structures, APIs, and interactions when planning and executing changes.

- Patch A: Combat Engine scaffolding (done)
- Patch B: Core engine implementation (done)
- Patch C: AI Engine scaffolding (done)
- Patch D: Siege Engine scaffolding (done)
- Patch E: Veterancy/XP scaffolding (done)
- Battle
- Campaign
- Misc

Docs available:
- battle_battle_scene.md
- battle_squad.md
- battle_soldier.md
- battle_general.md
- battle_abilities.md
- battle_siege_scene.md
- battle_skirmish_setup.md
- docs/CLAUDE_MIGRATION_NOTES.md (notes from migration plan)
- campaign_army.md
- campaign_generals.md
- campaign_ai_controller.md

Usage hints for Claude Code:
- Read the script section to understand the purpose and API surface.
- Use the Public API Surface to infer function signatures and call patterns.
- Look at Interaction Surface to see how modules communicate.

Index generated for Patch A: CombatEngine scaffolding and BattleScene bridge.

## Combat Subsystem Refactor — Patch Index

| Patch | Name | Engine File | Context Doc | Status Doc |
|-------|------|-------------|-------------|------------|
| B | CombatEngine Core | `battle/engine.py` | [CLAUDE_PATCHB.md](CLAUDE_PATCHB.md) | [claude_patchB_status.md](claude_patchB_status.md) |
| C | AIEngine Scaffolding | `battle/ai_engine.py` | [CLAUDE_PATCHC.md](CLAUDE_PATCHC.md) | [claude_patchC_status.md](claude_patchC_status.md) |
| D | SiegeEngine Scaffolding | `battle/siege_engine.py` | [CLAUDE_PATCHD.md](CLAUDE_PATCHD.md) | [claude_patchD_status.md](claude_patchD_status.md) |
| E | VeterancyEngine Scaffolding | `battle/veterancy_engine.py` | [CLAUDE_PATCHE.md](CLAUDE_PATCHE.md) | [claude_patchE_status.md](claude_patchE_status.md) |
