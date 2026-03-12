# Phase 2: Battle Overhaul + Campaign Sandbox

This document outlines the next major development phase. Nothing here should be implemented until explicitly approved.

---

## Part A: Battle Improvements

### A1. Unit Collision & Mass System
- Soldiers should physically block enemy soldiers from passing through
- Collision checks between opposing soldiers within a configurable radius
- **Mass matters**: heavier units (cavalry, armored infantry) push through lighter units; lighter units get shoved aside
- Collision resolution: each frame, check soldier-soldier overlap between opposing squads. Push apart based on mass ratio (e.g., cavalry mass 3.0 vs militia mass 1.0 → militia gets pushed 75%, cavalry 25%)
- Friendly soldiers should have soft collision (slight nudge) to prevent stacking but allow formation movement
- **Engagement lock**: when two infantry squads collide, soldiers in contact become "engaged" and cannot freely walk past. They must fight or rout to disengage. This is what creates a battle line
- Performance consideration: use spatial grid/buckets to avoid O(n^2) collision checks across entire battlefield

**Open question**: Should cavalry be able to punch through infantry lines on a charge? In Total War, a heavy cavalry charge can break through a thin line but gets stuck in deep formations. We could tie this to formation depth + mass differential.

### A2. Distinct Unit Shapes
Current: all soldiers are circles. Proposed shapes:

| Unit Type | Shape | Color Hint |
|-----------|-------|------------|
| Swordsmen / Melee Infantry | Square (filled) | Team color |
| Spearmen / Polearm | Diamond (rotated square) | Team color |
| Archers / Ranged | Triangle (pointing toward facing) | Team color, lighter |
| Cavalry | Larger oval / elongated ellipse | Team color |
| Generals | Star or circle with ring | Gold accent |
| Siege units (future) | Rectangle | Grey accent |

- Shape is determined by unit_stats flags: `is_cavalry`, `is_ranged`, `is_spear`, or fallback to melee infantry
- Shapes rotate with facing_angle so you can see which way units point

### A3. Skirmish Stance (Ranged Units)
- New toggle: **Skirmish Mode** (hotkey: `S`)
- When enabled, ranged units attempt to maintain distance from approaching enemies
- Behavior: if an enemy squad enters `range_distance * 0.4`, the ranged squad auto-retreats backward while continuing to fire (kiting)
- Ranged units **cannot fire while running** — they must stop briefly (0.5s) to loose a volley, then resume retreating
- Exception hook: a future `can_fire_while_moving` flag on unit_stats for special units (horse archers, etc.)
- If cornered (map edge or blocked by friendly units), they stop retreating and fight in melee

### A4. Defensive Stance
- New toggle: **Defensive Stance** (hotkey: `D`)
- Unit holds position and will not chase enemies
- Will engage enemies that come within `MELEE_RANGE * 3` but returns to held position after enemy retreats or dies
- Synergizes with bracing — spearmen in defensive stance auto-brace
- Counter-charge: if an enemy charges a unit in defensive stance, and the defending unit is cavalry, they perform a short counter-charge (move forward ~50 units then stop) for charge bonus without overextending
- Visual indicator: shield icon or anchor symbol drawn on the squad

### A5. Movement Speed Tiers
Current: units have one speed. Proposed three tiers:

| Mode | Speed Multiplier | Exhaustion Rate | Trigger |
|------|-----------------|-----------------|---------|
| **Walk** | 0.5x | 0 (none) | Default idle movement, hold Shift+right-click |
| **March** | 1.0x (current base) | 0.25x current rate | Normal right-click move |
| **Run/Charge** | 1.4x (infantry) / 1.6x (cavalry) | 1.0x current rate | Attack order or double-right-click |

- Walk: for repositioning without tiring troops. Good for long flanking maneuvers
- March: standard movement. Light exhaustion over time
- Run: fast movement, heavy exhaustion. Automatically triggered when charging
- HUD indicator shows current movement mode per squad
- Exhaustion thresholds may need retuning since walk produces zero exhaustion

**Thought**: We could also add a "Force March" on the campaign map that trades army HP/morale for faster map movement.

### A6. General Leveling Fix
- **Current (broken)**: Generals gain XP during battle from kills/abilities
- **Correct behavior**: Generals gain XP only upon **completing a battle**
- XP awarded based on: battle outcome (win = full, loss = partial), enemy army strength, casualties ratio
- Proposed XP formula: `base_xp * (1 + enemy_strength/player_strength) * win_mult * (1 - casualty_ratio * 0.5)`
- Level-up checks happen on the campaign map after returning from battle
- Remove in-battle XP gain entirely

---

## Part B: Campaign Overhaul

### B1. Real-Time Campaign Map (Mount & Blade Style)
- **Remove turn-based system entirely**
- Time advances continuously while the player moves (or at a configurable tick rate)
- When player is stationary, time pauses (or can be unpaused with a key)
- Pause/speed controls: Space = pause, 1/2/3 = speed multipliers
- All AI armies move simultaneously based on their current orders
- Day/night cycle (cosmetic initially, gameplay implications later)
- Time unit: "days" — movement speed determines how far an army travels per day

**Implementation approach**:
- Campaign `update()` runs a fixed timestep loop
- Each army has an AI controller that picks actions per tick
- Player army moves toward mouse/click target
- Collision detection triggers battle when armies meet

### B2. Factionless Player Start
- Player begins as an independent lord — no faction allegiance
- Player's "faction" is `None` or a special `INDEPENDENT` faction
- All factions start at Neutral (0) relations with the player
- Player can:
  - Accept quests from faction leaders to gain reputation
  - Fight bandits near faction territory for small rep gains
  - Trade (future feature) for rep
  - Join a faction once reputation reaches a threshold (e.g., +50)
- Joining a faction:
  - Player becomes a vassal — must answer war calls, can request armies
  - Can rise in rank: Mercenary → Vassal → Lord → General → Faction Leader
  - Rank determines: army size limit, ability to hold settlements, voting power
- Player can leave a faction (reputation hit) or be expelled (if rep drops too low)

**Thought**: Early game could feel like a mercenary sandbox — take contracts from any side, build up gold (future) and reputation, then commit to a faction or go independent.

### B3. Quest System
- Faction leaders (and eventually other NPCs) offer quests
- Quest types:

| Quest Type | Description | Reward |
|------------|-------------|--------|
| **Patrol** | Move to X waypoints within faction borders | Rep + gold |
| **Hunt Bandits** | Destroy N bandit armies near territory | Rep + gold |
| **Escort** | Accompany a trade caravan (AI army) from A to B | Rep + gold |
| **Raid** | Attack enemy faction's settlement or army | Rep + gold + loot |
| **Deliver Message** | Move to another faction's leader (diplomacy) | Rep |
| **Rescue** | Defeat army holding a captured general | High rep |
| **Assassination** | Defeat a specific enemy general (morally grey) | Gold + faction-specific rep |

- Quest board: accessible when player is at a faction's settlement
- Active quest tracker shown on campaign HUD
- Time limits on some quests (N days to complete)
- Failing/ignoring quests has small rep penalty

**Thought**: Could add a "Bounty Board" at taverns/neutral settlements for faction-independent quests (kill bandit leader, clear dungeon, etc.)

### B4. Expanded Map Content

#### More Factions (proposed 6-8 total):
1. **Player Kingdom** → removed as starting faction; becomes joinable
2. **Iron Empire** — militaristic, heavy infantry + siege focus
3. **Forest Alliance** — guerrilla tactics, archers + light infantry, forest terrain bonus
4. **Desert Raiders** — fast cavalry, hit-and-run, desert terrain bonus
5. **Northern Holds** — hardy infantry, defensive, mountain terrain bonus
6. **Maritime Republic** — balanced, trade-focused, coastal settlements
7. **Steppe Horde** — all cavalry, nomadic (fewer settlements, more roaming armies)
8. **Holy Order** — elite but small armies, high morale, crusade mechanics

#### More Settlements:
- Current: 15 settlements. Target: 30-40
- Settlement types:
  - **Castle**: military focus, recruits elite troops, high defense
  - **Town**: economic focus, generates gold, medium defense
  - **Village**: small, generates food/recruits, low defense
- Faction capitals are special (larger garrison, faction leader resides there)

#### Faction Borders:
- Borders defined by settlement ownership + Voronoi-style territorial regions
- Draw colored overlays on the map showing each faction's territory
- AI uses borders to determine patrol routes and detect incursions
- Neutral/unclaimed territory shown in grey

#### More Armies Per Faction:
- Each faction has 3-6 armies (depending on size)
- Each army led by a named general with personality traits
- Army composition reflects faction identity

### B5. AI Army Behaviors
Armies operate on a priority-based task system:

| Priority | Task | Description |
|----------|------|-------------|
| 1 | **Defend Home** | Return to defend settlement under attack |
| 2 | **War Orders** | Attack enemy settlements/armies if at war |
| 3 | **Patrol** | Move between waypoints within faction borders |
| 4 | **Hunt Bandits** | Seek and destroy bandit armies in territory |
| 5 | **Pillage** | Raid enemy faction's villages (if at war) |
| 6 | **Reinforce** | Move to friendly army that's outnumbered |
| 7 | **Idle/Garrison** | Stay at nearest settlement and recover |

- Generals have personality traits affecting behavior:
  - **Aggressive**: prioritizes attack, wider patrol range
  - **Cautious**: avoids fights unless outnumbering, stays near settlements
  - **Loyal**: always follows faction leader's directives
  - **Ambitious**: may betray faction if conditions are right (see B6)
  - **Greedy**: prioritizes pillaging, susceptible to bribes

### B6. General Betrayal & Persuasion
- Each general has hidden `loyalty` score (0-100) to their faction
- Loyalty affected by: faction leader's decisions, battle outcomes, personal grudges, player persuasion
- Low loyalty generals may:
  - Defect to another faction
  - Go independent (become a roaming army)
  - Join the player's faction if persuaded
- Player can attempt persuasion when meeting a general (dialogue menu):
  - **Bribe**: costs gold, +loyalty toward player, -loyalty toward faction
  - **Convince**: skill check based on player reputation, general personality
  - **Threaten**: works on cautious generals, backfires on aggressive ones
- If a general betrays, they take their army with them

**Thought**: This creates emergent storylines — a disgruntled general could defect mid-war, turning the tide. The player could engineer betrayals through targeted quests and diplomacy.

### B7. Player Faction Creation
- Player can found their own faction by:
  1. Capturing a neutral settlement (village or castle), OR
  2. Being granted a settlement by a faction they serve (high rank required)
- Once a faction is founded:
  - Player becomes faction leader
  - Can recruit generals (persuade independents or hire mercenaries)
  - Can declare war, propose alliances, set patrol orders
  - AI factions react: nearby factions may declare war or seek alliance
- Growing the faction:
  - Capture more settlements through war
  - Recruit defeated generals
  - Accept vassals (AI lords who want to join)

### B8. Roaming Non-Faction Armies

| Group | Army Size | Behavior | Loot |
|-------|-----------|----------|------|
| **Bandits** | 20-60 soldiers | Ambush near roads, flee from large armies | Gold, basic equipment |
| **Cultists** | 30-80, some "elite" fanatics | Raid villages, sacrifice captives (remove from garrison) | Reputation + unique items |
| **Cannibals** | 15-40, high melee stats | Ambush in forests/swamps, very aggressive | Small gold, reputation |
| **Deserters** | 20-50, mixed composition | Roam after losing battles, may join player if persuaded | Varied |
| **Mercenary Bands** | 40-100, professional | Can be hired by player or AI factions, wander between contracts | N/A (hireable) |
| **Wild Beasts** (optional) | 5-20 | Guard territory (forests, mountains), don't pursue far | Pelts/trophies |

- Roaming armies respawn periodically in wilderness areas
- Bandit camps: static locations that spawn bandit armies until destroyed
- Clearing bandit camps = quest reward + removes spawn point
- Mercenary bands cycle between settlements looking for employers

---

## Part C: Implementation Order (Proposed)

Rough ordering from foundational → dependent:

### Batch 1: Battle Core Fixes
1. **A5** — Movement speed tiers (Walk/March/Run) — foundational for feel
2. **A1** — Unit collision & mass — most impactful gameplay change
3. **A2** — Distinct unit shapes — visual clarity
4. **A6** — General leveling fix — quick fix

### Batch 2: Battle Tactics
5. **A4** — Defensive stance — enables tactical play
6. **A3** — Skirmish stance — ranged unit depth

### Batch 3: Campaign Foundation
7. **B1** — Real-time campaign map — biggest refactor, everything else depends on it
8. **B4** — Expanded map (factions, settlements, borders) — content for the sandbox
9. **B2** — Factionless player start — changes early game flow

### Batch 4: Campaign Depth
10. **B5** — AI army behaviors — makes the world feel alive
11. **B8** — Roaming armies (bandits, etc.) — content + early game opponents
12. **B3** — Quest system — gives the player direction
13. **B7** — Player faction creation — endgame goal

### Batch 5: Emergent Systems
14. **B6** — General betrayal & persuasion — emergent storytelling

---

## Open Questions

1. **Economy**: Should we add gold/resources now or defer? Many systems (quests, mercenaries, bribes) assume currency exists. Minimal version: settlements generate gold per day, armies cost upkeep, battles give loot.

2. **Recruitment**: How does the player get more soldiers? Options: recruit at settlements (costs gold + time), absorb defeated enemies (prisoners), hire mercenary bands. Faction membership could unlock elite unit recruitment.

3. **Army size limits**: Should the player be limited in army size? Mount & Blade uses a "party size" stat that grows with level/renown. Prevents snowballing.

4. **Map scale**: Current battle map is small. Campaign map is also small. Do we want to increase map sizes, or keep them compact for prototype speed? Larger maps + real-time movement could feel empty without enough content.

5. **Fog of war on campaign map**: Should the player have limited vision on the campaign map? Would make scouting important and create ambush opportunities.

6. **Diplomacy overhaul**: Current diplomacy is faction-to-faction. With a factionless player and general-level loyalty, do we need a more granular relationship system? (Player ↔ individual generals, not just factions)

7. **Permadeath**: Should generals (including the player's) have permadeath? High stakes but punishing. Alternative: capture + ransom system.

8. **Save system**: Current save is simple JSON. Real-time campaign with many more entities will need more robust serialization. Worth addressing early.

---

## Additional Ideas (Not Requested, For Discussion)

- **Terrain-specific battles**: battle map generated based on campaign map terrain (fighting in forest = forest battle map, fighting near castle = siege, etc.)
- **Seasons**: weather changes by season, affects movement speed on campaign map, battle modifiers
- **Supply lines**: armies far from friendly territory lose morale/HP over time
- **Naval movement**: coastal factions can move armies by sea (fast but risky)
- **Tournament/Arena**: at major towns, player can enter tournaments for gold + reputation (1v1 or small squad battles)
- **Prisoner system**: defeated generals/soldiers can be captured, ransomed, recruited, or executed (each with reputation consequences)
