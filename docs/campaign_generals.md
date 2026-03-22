Script: Campaign Generals
Path: campaign/generals.py
Purpose: General management for loyalty, betrayal, prisoner mechanics, and cross-system progression.

Key Classes/Structures
- GeneralStatus
- Prisoner
- PlayerCaptureState
- GeneralManager

Public API Surface
- GeneralManager.register_general(general_name, faction_team, personality=None, level=1)
- GeneralManager.get_loyalty(general_name)
- GeneralManager.set_loyalty(general_name, value)
- GeneralManager.modify_loyalty(general_name, delta)
- GeneralManager.get_status(general_name)
- GeneralManager.get_faction(general_name)
- GeneralManager.get_personality(general_name)
- GeneralManager.check_betrayals(armies, ai_controllers, diplomacy, add_notification)
- GeneralManager.process_betrayal(army, action, armies, ai_controllers, factions, diplomacy)
- GeneralManager.attempt_bribe(...), attempt_convince(...), attempt_threaten(...)
- Prisoner serialization/deserialization

Core Data Structures
- self.generals dict: general_name -> {loyalty, status, faction_team, personality, level}
- self.player_prisoners, self.player_capture, self.intimidation_bonus, self.dead_generals

Notable Algorithms or Patterns
- Betrayal risk calculation based on loyalty and personality; action can be independent or defect
- Persuasion and bribery success chances influenced by personality and reputation
- Prisoner capture, ransom, recruitment, execution impact on relations

Interaction Surface
- Interacts with battle outcomes and diplomacy layer; general state tracked across campaign and battle

Design Notes and Tradeoffs
- Centralizes general lifecycle management; risk of tight coupling with diplomacy and battle logic; plan to further modularize via a GeneralEngine layer

Testing Notes
- Tests for loyalty updates, betrayal triggers, and prisoner lifecycle (capture, ransom, recruit, execute)

Performance Considerations
- Low-cost dictionary lookups; main cost is diplomacy interactions in large campaigns

Migration / Extension Notes
- Add unit tests for end-to-end flows across battle and diplomacy state changes

References
- battle/general.py, campaign/ai_controller.py, diplomacy subsystem (external)
