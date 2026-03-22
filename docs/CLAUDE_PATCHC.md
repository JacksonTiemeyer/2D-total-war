Patch C Context: AI Engine scaffolding

What Patch C will implement
- Introduce battle/ai_engine.py with a pluggable AIEngine interface
- Basic update() hook and a simple default strategy scaffold
- Wire-in and preserve existing ArmyAI behavior for Patch C compatibility

Rationale
- Prepare for a cleanAI engine replacement without breaking existing battle logic

What Claude should implement next (high-level)
- Build a plan to migrate ArmyAI into a dedicated AIEngine with pluggable strategies
- Update Patch D to integrate SiegeEngine and hook AIEngine outputs into move/attack commands
- Update Patch E to align with post-battle XP/veterancy flows
