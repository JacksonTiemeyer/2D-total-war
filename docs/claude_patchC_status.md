Patch C Status: AI Engine scaffolding

- Added battle/ai_engine.py with AIEngine class and a no-op update signature
- Patch C lays groundwork for migrating ArmyAI into a pluggable engine
- Documentation skeleton CLAUDE_PATCHC.md and status file added

Next steps for Claude:
- Implement a functional AIEngine.update(...) strategy and tests
- Prepare patch D to wire AIEngine into CombatEngine
