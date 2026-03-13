# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Game

```bash
pip install -r requirements.txt
python main.py
```

Only dependency is `pygame>=2.5.0`. No build step needed — pure Python.

## Architecture

**State Machine** in `main.py` drives everything. The `Game` class manages transitions between states:

```
MAIN_MENU → CAMPAIGN ↔ PRE_BATTLE → BATTLE → POST_BATTLE → CAMPAIGN
           ↓
        SKIRMISH_SETUP → BATTLE → POST_BATTLE → MAIN_MENU
```

### Module Layout

- **`main.py`** — Entry point, `Game` class, state machine, post-battle XP/casualty resolution
- **`campaign/`** — Campaign map systems (real-time, Mount & Blade style)
  - `campaign_scene.py` — Main campaign loop, player army, settlements, enemy armies, diplomacy, recruitment
  - `army.py` — `CampaignSquad` and `Army` classes with veterancy persistence across battles
  - `settlement.py` — Towns/Villages/Castles with ownership and vision radius
  - `faction.py` — Faction definitions (Iron Empire, Forest Alliance, Desert Raiders, etc.)
  - `diplomacy.py` — Faction relationships, war/alliance/neutral states
- **`battle/`** — Real-time tactical combat at 60 FPS
  - `battle_scene.py` (~1600 lines) — Battle orchestrator: squads, terrain, weather, fog of war, AI, targeting. This is the largest and most complex file
  - `squad.py` (~1000 lines) — Squad and `Soldier` management, formations, movement modes, morale, exhaustion, stances
  - `soldier.py` — Individual soldier model (health, position, facing, attacks)
  - `general.py` — Hero/general system with Three Kingdoms-style dueling, abilities, XP/leveling
  - `abilities.py` — Special abilities by general type (Commander, Champion, Strategist)
  - `siege_scene.py` — Siege battle variant with walls/gates/towers
  - `skirmish_setup.py` — Budget-based army builder for skirmish mode
- **`core/`** — Engine systems
  - `settings.py` — **All game constants and balance parameters live here** (screen size, map dimensions, combat values, morale thresholds, exhaustion rates, terrain/weather modifiers)
  - `camera.py` — Pan and zoom
  - `audio.py` — Procedurally generated placeholder sounds
  - `save_system.py` — JSON save/load to `~/.2d-total-war/save.json`
  - `utils.py` — Distance, angle, normalize helpers
- **`data/unit_types.py`** — All unit definitions (`UnitStats` class with 20+ attributes per unit type)

## Key Game Systems

**Combat**: Melee/ranged with armor penetration, charge bonuses, flanking (30% bonus) and rear attacks (60% bonus) based on facing angles. Spatial grid optimization (30-unit cells) for collision.

**Formations**: Line, Column, Square, Loose, Wedge — each with stat modifiers. Defined in `squad.py`, constants in `settings.py`.

**Morale**: 100-point scale. Breaks at 25, routs at 10. Affected by casualties, flanking, general aura, abilities.

**Exhaustion**: 100-point scale. Three movement modes (Walk 0x, March 0.25x, Run 1.0x exhaustion rate). Penalizes speed, damage, attack cooldown.

**Stances**: Defensive (hold position, auto-brace spearmen) and Skirmish (ranged kiting).

**Terrain**: Hills give ranged/vision bonuses, forests block LOS and slow cavalry. Weather (rain, fog, mud, wind) applies global modifiers.

**Veterancy**: Squads persist across battles. Ranks: Raw → Trained → Veteran → Elite → Legendary based on battles survived.

**General Abilities**: Commander (Rally, Second Wind), Champion (Challenge, Bloodlust), Strategist (Precision Volley, Scout Report, Weaken Resolve). Cooldown-based.

## Development Status

- **PLAN.md** — Phase 1 feature roadmap (13 features, most implemented)
- **PHASE2_PLAN.md** — Phase 2 detailed specs (battle overhaul, campaign sandbox, UI, advanced systems). Status: PLANNING. Implementation order is in Part E of that doc.

Phase 1 completed features include: post-battle summary, terrain effects, skirmish mode, unit persistence, battle AI, formations, fog of war, save/load, sound, veterancy, siege battles, weather, diplomacy.

Phase 2 is organized into batches: Battle Core Fixes → Battle Tactics → Campaign Foundation → Campaign Interaction → Campaign Depth → Advanced Systems.

## Conventions

- Game runs at 60 FPS, screen 1280x720, battle map 3000x2000, campaign map 4000x3000
- All balance tuning goes in `core/settings.py` as named constants
- Unit types defined in `data/unit_types.py` with `UnitStats` dataclass
- Campaign squads (`CampaignSquad` in `army.py`) bridge campaign persistence with battle instances
- Post-battle resolution (XP, casualties, veterancy) happens in `main.py._resolve_battle()`
- No external assets — all graphics are pygame primitives, all sounds are procedurally generated
