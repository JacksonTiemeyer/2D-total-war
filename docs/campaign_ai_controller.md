Script: AI Controller
Path: campaign/ai_controller.py
Purpose: Priority-based task system for AI armies; determines movement and actions based on personality traits and battlefield context.

Key Classes/Structures
- GeneralPersonality
- ArmyAI

Public API Surface
- ArmyAI.__init__(self, army, personality=None)
- ArmyAI.update(self, armies, settlements, diplomacy)
- ArmyAI._task_status_label(self, task)
- ArmyAI._evaluate_priorities(self, armies, settlements, diplomacy)
- ArmyAI._check_defend_home(self, armies, settlements, diplomacy)
- ArmyAI._check_war_orders(self, armies, settlements, diplomacy)
- ArmyAI._check_patrol(self, settlements)
- ArmyAI._check_hunt_bandits(self, armies)
- ArmyAI._check_pillage(self, settlements, diplomacy)
- ArmyAI._check_reinforce(self, armies, diplomacy)
- ArmyAI._check_idle_garrison(self, settlements)
- ArmyAI.serialize(self), ArmyAI.deserialize(self, data)

Core Data Structures
- self.army, self.personality, self.current_task, self.task_target, self.task_cooldown
- self.loyalty

Notable Algorithms or Patterns
- Priority-based task selection; personality biases affect timing and target choice
- Distance-based target evaluation for nearest enemy or nearest own- settlements
- Fallback wandering to preserve some activity when no clear target exists

Interaction Surface
- Consumes: armies data, settlements info, diplomacy state
- Produces: move orders and task assignments on the connected Army instance

Design Notes and Tradeoffs
- Simple heuristic-driven AI; opportunities to plug a behavior-tree/decision-engine later

Testing Notes
- Tests for priority resolution under controlled scenarios; seed random to ensure deterministic tests

Performance Considerations
- Lightweight per-tick evaluation; scale concerns with large numbers of AI agents in a campaign

Migration / Extension Notes
- Abstract to a separate AIEngine with pluggable strategies

References
- battle and campaign game loop integration points
