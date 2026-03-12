# 2D Total War Prototype - Feature Implementation Plan

Ordered easiest → hardest. Each feature lists files touched, estimated scope,
and dependencies on prior features.

---

## 1. Post-Battle Summary Screen
**Scope: Small | Files: main.py**
**Dependencies: None**

Add a POST_BATTLE game state between battle end and campaign return.
- Track stats during battle: kills per squad, casualties, XP gained, generals leveled
- Display: army losses (before/after), MVP squad, general XP/level changes, loot earned
- "Press ENTER to continue" → return to campaign
- Wire into `_resolve_battle()` which already handles the transition

**Implementation:**
- Add `POST_BATTLE` to GameState enum
- Add `self.battle_stats` dict populated from battle scene data
- New `_draw_post_battle()` method with two-column layout (your army | enemy army)
- Modify `_resolve_battle()` to go to POST_BATTLE first, then CAMPAIGN on ENTER

---

## 2. Terrain Combat Effects
**Scope: Small | Files: battle/squad.py, battle/battle_scene.py, core/settings.py**
**Dependencies: None**

Make existing terrain rectangles affect gameplay:
- **Hills**: +15% ranged damage when firing from hill, +20% charge bonus downhill,
  -10% speed moving uphill
- **Forests**: -50% cavalry speed, -30% ranged accuracy into/out of forest,
  +15% melee defense (cover)

**Implementation:**
- Add terrain constants to settings.py
- Add `get_terrain_at(x, y)` helper to BattleScene that checks terrain rects
- Pass terrain info into Squad.update() - modify speed, ranged accuracy, charge bonus
- Visual indicator: tint soldiers slightly when in terrain

---

## 3. Skirmish Mode
**Scope: Medium | Files: main.py (new state), NEW battle/skirmish_setup.py**
**Dependencies: None (but benefits from #1 for post-battle)**

Standalone army builder → battle → results, no campaign.

**Army Builder Screen:**
- Budget selector: 500 / 1000 / 1500 / 2000 gold
- Two columns: Available Units (left) | Your Army (right)
- Click to add/remove squads, shows cost and remaining budget
- General type picker: Commander / Champion / Strategist
- "Fight!" button when army is valid (≥1 squad)
- Enemy army auto-generated to match budget

**Implementation:**
- Add SKIRMISH_SETUP to GameState enum
- Main menu gets two options: "Campaign" and "Skirmish"
- New `SkirmishSetup` class handles the army builder UI + input
- Generates enemy army using budget-matched `create_enemy_army()`
- Launches into BATTLE state with both armies, returns to menu on completion
- Reuse existing battle scene entirely

---

## 4. Unit Persistence Between Battles
**Scope: Medium | Files: main.py, campaign/army.py, battle/battle_scene.py**
**Dependencies: #1 (post-battle screen shows what survived)**

Casualties carry over. Squads that lost soldiers stay weakened.

**Implementation:**
- Change army squads from `(UnitStats, count)` to squad objects with mutable count
- After battle: read `squad.alive_count` from each battle squad, update campaign army
- Squads at 0 soldiers are removed from army
- Track squad kills/veterancy across battles (future: veterancy bonuses)
- `get_battle_data()` exports current counts; `apply_battle_results()` imports survivors
- Pre-battle screen shows "Wounded" indicator for understrength squads

---

## 5. Battle AI Improvements
**Scope: Medium | Files: battle/battle_scene.py**
**Dependencies: #2 (terrain awareness)**

Replace simple "attack nearest" with role-based AI:

**AI Behaviors by Unit Type:**
- **Melee infantry**: Advance in line, engage nearest enemy melee
- **Spearmen**: Hold position, brace against cavalry threats
- **Cavalry**: Wait for engagement, then flank/rear-charge occupied enemies
- **Ranged**: Stay behind melee line, focus fire on highest-value targets
- **Routed units**: Ignore (don't chase routers, focus on threats)

**AI Decision Loop:**
- Phase 1 (Opening): Advance melee line, ranged hold and fire
- Phase 2 (Engaged): Cavalry flanks, ranged switches to priority targets
- Phase 3 (Breaking): Focus fire on wavering enemies to trigger routs

**General AI:**
- Commanders: Auto-use Rally and Second Wind when squads are hurting
- Champions: Seek duels, use Bloodlust before engaging
- Strategists: Precision Volley on ranged clumps, Weaken Resolve on key targets

**Implementation:**
- New `_enemy_ai()` method with phase detection based on engagement state
- Add `_classify_squads()` helper to bucket units by role
- Cavalry waits until melee is engaged, then finds flanking angle
- Ranged targets weakest/most valuable unit in range

---

## 6. Formation System
**Scope: Medium | Files: battle/squad.py, core/settings.py, battle/battle_scene.py**
**Dependencies: None (but synergizes with #5 AI)**

Toggle formations with hotkeys (T to cycle, or number keys while holding Ctrl):

| Formation | Shape | Bonus | Penalty |
|-----------|-------|-------|---------|
| **Line** (default) | Wide, shallow | None | None |
| **Column** | Deep, narrow | +20% charge bonus | -flanking vulnerability |
| **Square** | Dense block | +30% vs cavalry, immune to rear | -25% speed |
| **Loose** | Spread out | -40% ranged damage taken | -20% melee defense |
| **Wedge** | V-shape | +40% charge bonus | -15% defense |

**Implementation:**
- Add `Formation` enum to squad.py
- Modify `_create_formation()` to accept formation type
- Add `set_formation()` method that recalculates soldier positions
- Formation affects: soldier spacing, stat modifiers, charge bonus
- HUD shows current formation name
- Ctrl+1/2/3/4/5 hotkeys in battle_scene.py

---

## 7. Fog of War
**Scope: Medium-Large | Files: battle/battle_scene.py, battle/squad.py**
**Dependencies: #2 (forests block LOS), ties into Strategist Scout Report**

Vision system for battle map:

- Each squad has vision radius (infantry 200, cavalry 250, ranged = range_distance)
- Enemy squads outside all friendly vision are hidden
- Forests block line of sight
- Hills give extended vision radius (+50%)
- Strategist's Scout Report reveals all for its duration

**Implementation:**
- Add `visible` flag to each squad, computed each frame
- `_compute_visibility()` method on BattleScene checks all friendly squad vision
- Hidden squads: don't draw, don't show in targeting
- Fog overlay: dark semi-transparent layer with holes cut for vision
- Enemy AI already knows where player is (omniscient AI is fine for now)

---

## 8. Save/Load System
**Scope: Medium | Files: NEW core/save_system.py, campaign/army.py, campaign_scene.py, main.py**
**Dependencies: #4 (persistent squads need saving)**

JSON-based save file for campaign state:

**Saved Data:**
- Player army: squads, general, gold, position, general XP/level
- All enemy armies: composition, position
- All settlements: owner, recruitment pool
- Turn counter, campaign state

**Implementation:**
- `SaveData` class that serializes/deserializes campaign state
- Save on campaign map: Ctrl+S (or auto-save each turn)
- Load from main menu: "Continue" option
- Save file: `~/.2d-total-war/save.json`
- Version field for future save compatibility

---

## 9. Sound Design (Placeholder)
**Scope: Medium | Files: NEW core/audio.py, battle scenes, campaign**
**Dependencies: None**

Procedurally generated placeholder sounds using pygame.mixer:

- **Charge**: Rising pitch sweep
- **Melee clash**: Random short noise bursts
- **Arrow volley**: Whoosh + thuds
- **Ability activation**: Distinct tone per type
- **Routing**: Horn/trumpet sound
- **Victory/Defeat**: Fanfare or dirge
- **Campaign**: Simple BGM loop, click sounds for UI

**Implementation:**
- `AudioManager` singleton with `play(event_name)` interface
- Generate sounds programmatically with pygame.sndarray (no asset files needed)
- Volume controls in settings
- Battle events emit sound calls at key moments (charge impact, ability use, rout)

---

## 10. Recruitment Depth / Veterancy
**Scope: Medium | Files: campaign/army.py, battle/squad.py, data/unit_types.py**
**Dependencies: #4 (persistence), #8 (save/load)**

Squads gain veterancy from battle experience:

| Rank | Battles | Bonus |
|------|---------|-------|
| Raw | 0 | None |
| Trained | 1 | +5% attack, +5% defense |
| Veteran | 3 | +10% attack, +10% defense, +5% morale |
| Elite | 6 | +15% all stats, -10% exhaustion rate |
| Legendary | 10 | +25% all stats, -20% exhaustion rate, unique name |

**Implementation:**
- Add `battles_survived`, `total_kills` to squad persistence data
- Veterancy rank computed from battles_survived
- Stat modifiers applied as multipliers in combat calculations
- Visual: chevron indicators on squad label (one chevron per rank)
- Campaign army panel shows veterancy rank

---

## 11. Siege Battles
**Scope: Large | Files: NEW battle/siege_scene.py, campaign integration**
**Dependencies: #2 (terrain), #5 (AI), #6 (formations)**

Special battle map when attacking castles:

- **Walls**: Blocking terrain with gate
- **Gate**: Must be destroyed (HP bar) or opened
- **Towers**: Auto-fire arrows at attackers in range
- **Ladders**: Infantry can scale walls slowly (single-file, vulnerable)
- **Defender advantage**: +30% defense on walls, ranged fire from elevation

**Implementation:**
- New `SiegeScene` that extends BattleScene with wall/gate objects
- Wall segments as collision objects soldiers path around
- Siege AI: attackers converge on gate/ladders, defenders man walls
- Triggered when attacking a Castle settlement on campaign map

---

## 12. Weather Effects
**Scope: Medium | Files: battle/battle_scene.py, core/settings.py**
**Dependencies: #2 (terrain), #7 (fog)**

Random weather per battle with gameplay effects:

| Weather | Visual | Effect |
|---------|--------|--------|
| Clear | Normal | None |
| Rain | Particle overlay | -20% ranged accuracy, +30% exhaustion rate |
| Fog | White overlay, reduced alpha | Vision radius halved |
| Mud | Brown tint ground | -30% movement speed, -50% charge bonus |
| Wind | Directional particles | Ranged accuracy ±15% based on wind direction |

**Implementation:**
- Weather selected randomly at battle start (or influenced by campaign map region)
- Particle system for rain/fog/wind visuals
- Global modifier applied to relevant combat calculations
- HUD shows current weather and effects

---

## 13. Alliance / Diplomacy
**Scope: Large | Files: campaign/ (major rework), NEW campaign/faction.py, campaign/diplomacy.py**
**Dependencies: #8 (save/load), #5 (AI)**

Multiple AI factions that interact:

- **Factions**: 3-4 AI factions with unique unit preferences and aggression levels
- **Relations**: -100 to +100 scale (war < -50, neutral, alliance > 50)
- **Actions**: Declare war, propose alliance, trade, non-aggression pact
- **AI behavior**: Factions fight each other, player can exploit conflicts
- **Diplomacy screen**: Accessible from campaign map, shows relations and options

**Implementation:**
- `Faction` class with personality traits (aggressive, defensive, economic)
- `DiplomacyManager` tracks all faction relationships
- AI factions move armies, capture settlements, recruit units independently
- Campaign map becomes a living world instead of player vs static enemies
- Major refactor of campaign_scene to handle multiple active factions

---

## Implementation Order

| # | Feature | Scope | Dependencies |
|---|---------|-------|--------------|
| 1 | Post-Battle Summary | Small | None |
| 2 | Terrain Combat Effects | Small | None |
| 3 | Skirmish Mode | Medium | None |
| 4 | Unit Persistence | Medium | #1 |
| 5 | Battle AI | Medium | #2 |
| 6 | Formation System | Medium | None |
| 7 | Fog of War | Medium-Large | #2 |
| 8 | Save/Load | Medium | #4 |
| 9 | Sound Design | Medium | None |
| 10 | Veterancy | Medium | #4, #8 |
| 11 | Siege Battles | Large | #2, #5, #6 |
| 12 | Weather Effects | Medium | #2, #7 |
| 13 | Diplomacy | Large | #8, #5 |
