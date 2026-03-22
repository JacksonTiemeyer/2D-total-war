Patch E Context: Veterancy and XP propagation scaffolding

What Patch E will implement
- Introduce a VeterancyEngine to centralize post-battle XP and veterancy progression
- Provide hooks for distributing XP to campaign generals and squads
- Wire XP hooks into the engine so future patches can trigger XP distribution from battle outcomes

Rationale
- Centralizes growth mechanics; keeps combat logic focused on on-battle state while enabling cross-system progression

What Claude should implement next (high-level)
- Implement concrete veterancy progression rules and per-squad stat bumps
- Integrate with campaign data models to persist veterancy and level-ups
- Add tests for XP distribution and veterancy thresholds
