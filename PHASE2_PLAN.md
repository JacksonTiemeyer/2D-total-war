# Phase 2: Battle Overhaul + Campaign Sandbox

This document outlines the next major development phase. Nothing here should be implemented until explicitly approved.

**Status**: PLANNING — awaiting green light to begin implementation.

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
- Cavalry can punch through thin infantry lines on a charge but gets stuck in deep formations. Tied to formation depth + mass differential

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
- **Force March** on campaign map: trades army HP/morale for faster map movement

### A6. General Leveling Fix
- **Current (broken)**: Generals gain XP during battle from kills/abilities
- **Correct behavior**: Generals gain XP only upon **completing a battle**
- XP awarded based on: battle outcome (win = full, loss = partial), enemy army strength, casualties ratio
- Proposed XP formula: `base_xp * (1 + enemy_strength/player_strength) * win_mult * (1 - casualty_ratio * 0.5)`
- Level-up checks happen on the campaign map after returning from battle
- Remove in-battle XP gain entirely

### A7. Ranged & Cavalry Attack Behavior — Maximum Range Engagement
- When a ranged unit (archers, horse archers, etc.) or cavalry with ranged capability is ordered to attack a target, they should position themselves at **maximum effective range** rather than closing distance
- They fire from the furthest point where they are JUST within range
- They only move closer if:
  - The target moves out of range (they follow to maintain max range)
  - An enemy enters melee distance (triggers skirmish retreat if enabled, or melee engagement)
- This applies by default — no stance toggle needed, it's inherent to ranged attack behavior
- Combined with Skirmish Stance (A3): ranged units at max range who see enemies approaching will begin retreating before enemies reach melee distance

### A8. Targeting Indicator — Hover Only
- Currently: targeting indicators are always visible (clutters battlefield)
- **New behavior**: targeting indicators (lines, circles, highlights) only appear when the player **hovers the mouse over a unit/squad**
- On hover: show the squad's current target, attack range circle, and engagement state
- When not hovering: battlefield stays clean with only unit shapes + health bars visible
- Selected units still show their movement/attack orders (waypoint lines)

### A9. Faction Specialty Units
Each faction gets 1-2 unique units that only they can recruit. These are elite or mechanically distinct:

| Faction | Specialty Unit | Description |
|---------|---------------|-------------|
| **Iron Empire** | **Ironclad Legionnaires** — ultra-heavy infantry with massive mass value; nearly immovable in defensive stance. Slow but devastating in a hold | Shield wall specialists |
| **Iron Empire** | **Siege Engineers** — deploy battlefield barricades/obstacles mid-fight (future: siege weapons) | Utility/siege |
| **Forest Alliance** | **Shadowstalkers** — stealth archers that are invisible until they fire or an enemy gets very close | Ambush specialists |
| **Forest Alliance** | **Treewarden Sentinels** — spearmen with forest terrain bonus (+defense, +speed in trees) | Terrain specialists |
| **Desert Raiders** | **Sandstorm Riders** — horse archers with `can_fire_while_moving` (only faction to have this) | Mobile ranged cavalry |
| **Desert Raiders** | **Dune Assassins** — small squad, very fast, bonus damage on charge, weak in prolonged melee | Shock troops |
| **Northern Holds** | **Berserkers** — ignore exhaustion penalties, gain damage as health drops, cannot retreat (no rout) | Glass cannon melee |
| **Northern Holds** | **Shieldwall Veterans** — highest brace bonus in game, massive morale, slow | Defensive anchor |
| **Maritime Republic** | **Corsair Crossbowmen** — shorter range than archers but higher damage, armor-piercing | Anti-armor ranged |
| **Maritime Republic** | **Marine Boarders** — fast infantry, bonus in close quarters, good against cavalry (hook weapons) | Anti-cavalry |
| **Steppe Horde** | **Khan's Chosen** — elite heavy cavalry, highest mass + charge bonus in game | Shock cavalry |
| **Steppe Horde** | **Horse Archers** — lighter than Sandstorm Riders but faster, can skirmish while mounted | Kiting cavalry |
| **Holy Order** | **Templar Knights** — heavy cavalry with morale aura (nearby friendlies gain morale), immune to fear | Morale anchor + cavalry |
| **Holy Order** | **Flagellants** — cheap, high damage, low defense, immune to rout but die fast | Zealot swarm |

- Specialty units are recruited only at faction-specific buildings (e.g., Iron Empire Barracks, Forest Alliance Grove)
- Player can access these by joining the faction or capturing their settlements

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

Early game feels like a mercenary sandbox — take contracts from any side, build up gold and reputation, then commit to a faction or go independent.

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

- Quest board: accessible when player enters a faction's settlement (see B9)
- Active quest tracker shown on campaign HUD
- Time limits on some quests (N days to complete)
- Failing/ignoring quests has small rep penalty
- Recruitment as quest reward: some quests grant soldiers directly instead of/in addition to gold

### B4. Expanded Map Content

#### More Factions (8 total):
1. **Iron Empire** — militaristic, heavy infantry + siege focus
2. **Forest Alliance** — guerrilla tactics, archers + light infantry, forest terrain bonus
3. **Desert Raiders** — fast cavalry, hit-and-run, desert terrain bonus
4. **Northern Holds** — hardy infantry, defensive, mountain terrain bonus
5. **Maritime Republic** — balanced, trade-focused, coastal settlements
6. **Steppe Horde** — all cavalry, nomadic (fewer settlements, more roaming armies)
7. **Holy Order** — elite but small armies, high morale, crusade mechanics
8. **Free Cities Confederation** — loose alliance of independent towns, weak military but rich; hires mercenaries

#### More Settlements:
- Target: 30-40 settlements
- Settlement types:
  - **Castle**: military focus, recruits elite troops, high defense
  - **Town**: economic focus, generates gold, medium defense, has tavern + bounty board
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

#### Increased Battle Map Size:
- Battle map increased to support larger engagements and terrain variety
- More room for flanking, ranged positioning, and cavalry charges

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
- **NPC generals have permadeath** — if killed in battle, they're gone forever. This makes betrayals and assassinations impactful
- **Player is captured, not killed** — on defeat, player is captured and must be ransomed (costs gold) or escapes after time passes

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
| **Peasant Caravans** | 10-30, weak | Travel between villages trading goods, easy targets | Gold + supplies |

- Roaming armies respawn periodically in wilderness areas
- Bandit camps: static locations that spawn bandit armies until destroyed
- Clearing bandit camps = quest reward + removes spawn point
- Mercenary bands cycle between settlements looking for employers
- **Mercenary encounter events**: while traveling, player may encounter a mercenary band and can hire them on the spot (if they have gold)

#### Stronghold Escalation System
- Roaming groups (bandits, cultists, cannibals) track their **battle wins**
- After winning enough battles (against AI patrols, other roaming groups, peasant caravans), they grow:
  - **Stage 1 — Warband**: default spawned group, small, basic
  - **Stage 2 — Encampment**: group claims a map location, builds a camp. Spawns additional patrols nearby
  - **Stage 3 — Stronghold**: fortified location, larger garrison, acts like a mini-settlement. Must be assaulted to clear
- Strongholds generate quests automatically ("Clear the bandit stronghold near X")
- If left unchecked, strongholds can threaten faction borders and disrupt trade routes
- Factions will eventually send armies to clear strongholds in their territory (AI priority task)
- **Cultist strongholds** might have unique effects: cursed land (morale debuff nearby), dark rituals (spawn elite units)
- **Cannibal dens** could ambush passing armies with traps (pre-battle debuff)

#### Random Events (Campaign)
- Events trigger based on time, location, or conditions:

| Event | Trigger | Effect |
|-------|---------|--------|
| **Bandit Uprising** | Bandits left unchecked too long | Massive bandit army spawns |
| **Plague** | Random, affects a region | Settlement production halved, army attrition |
| **Harvest Festival** | Seasonal | Settlement morale boost, bonus recruits |
| **Merchant Caravan** | Random encounter on roads | Buy/sell equipment and supplies |
| **Refugee Crisis** | Faction at war loses settlement | Refugees flee to neutral territory, can be recruited cheaply |
| **Mercenary Tournament** | At towns periodically | Compete for gold + reputation |
| **Eclipse/Omen** | Random | Morale effects, cultist activity spikes |
| **Desertion Wave** | Army morale very low | Soldiers leave an army, become deserter roaming group |

### B9. Interactable Settlements
- **New feature**: player can enter any settlement they are not at war with
- Entering a settlement opens a **settlement interaction screen** (not a battle):

#### Settlement Interior Menu:
| Feature | Available At | Description |
|---------|-------------|-------------|
| **Tavern** | Towns, Castles | Hire mercenary bands, hear rumors, find bounty board |
| **Bounty Board** | Towns, Taverns | Faction-independent quests: kill bandit leader, clear stronghold, escort merchant, etc. |
| **Recruitment Office** | All settlements | Recruit soldiers (type depends on faction + settlement type) |
| **Market** | Towns | Buy/sell equipment (future), trade goods |
| **Faction Leader Audience** | Capital only | Request quests, pledge allegiance, negotiate |
| **Garrison Management** | Owned settlements | Assign soldiers to defend the settlement |
| **Rest & Recover** | All settlements | Heal wounded soldiers, restore morale (costs time) |

- Settlement access rules:
  - **Friendly/Neutral faction**: full access
  - **At war**: cannot enter (must siege/assault)
  - **Player-owned**: full access + garrison management + tax collection
- Bounty Board quests refresh periodically and are independent of faction reputation
- Tavern rumors can hint at: nearby strongholds, faction politics, quest opportunities, incoming wars

### B10. Economy System
- **Decided**: implement economy framework now — too many systems depend on it
- Currency: **Gold**
- Income sources:
  - Quest rewards
  - Battle loot (scales with enemy army strength)
  - Settlement taxes (if player owns settlements)
  - Trade (selling goods at markets — future depth)
  - Ransoming captured generals
- Expenses:
  - Army upkeep (gold per day per soldier, scales with unit quality)
  - Recruitment costs
  - Mercenary hiring fees
  - Bribes and diplomacy
  - Settlement upgrades (future)
- If player cannot pay upkeep: morale drops, desertion risk increases
- AI factions also have economies — weak factions may field fewer/worse armies

### B11. Recruitment System
- **Primary**: recruit at settlements (costs gold + time, unit type depends on settlement/faction)
- **Secondary**: hire mercenary bands (encounter on roads or at taverns)
- **Tertiary**: quest rewards sometimes grant soldiers
- **Future**: absorb prisoners from defeated armies
- Faction membership unlocks elite/specialty unit recruitment at that faction's buildings
- Army size limit tied to player renown/level:
  - Start: ~60 soldiers
  - Mid-game: ~150 soldiers
  - Late-game (faction leader): ~300+ soldiers
- AI armies scale with a hidden **Weak/Normal/Elite** classification relative to player power, ensuring fair challenge scaling

### B12. Diplomacy — Dual-Layer Reputation
- **Faction reputation** (-100 to 100): how the faction as a whole views the player
  - Affected by: quests completed, battles fought for/against, settlements taken
  - Determines: access to faction settlements, ability to join, quest availability
- **Individual general opinion** (-100 to 100): how each named general personally views the player
  - Affected by: direct interactions, bribes, shared battles, betrayals
  - Determines: persuasion success chance, betrayal willingness, alliance likelihood
- A general might personally like the player even if their faction doesn't (or vice versa)
- This dual system enables nuanced politics: befriend a general → convince them to defect → weaken the enemy faction from within

### B13. Fog of War (Campaign Map)
- Player has limited vision radius on the campaign map
- Can only see:
  - Area around own army (vision radius scales with army scout stat)
  - Area around owned settlements
  - Area around allied faction settlements (if allied)
- Unknown territory shown as darkened/greyed overlay
- Enemies in fog are invisible — enables ambushes and surprises
- Scouting: future unit type "Scouts" could extend vision radius
- Faction borders are always visible (common knowledge) but army positions within fog are hidden

---

## Part C: UI & HUD Overhaul

### C1. Mouse-Friendly Battle UI
Current UI is keyboard-heavy. New UI should be primarily mouse-driven:

#### Battle HUD Layout:
```
┌──────────────────────────────────────────────────────────┐
│  [Pause] [Speed: 1x 2x 3x]              [Mini-map]      │
│                                                          │
│                                                          │
│                    BATTLE MAP                            │
│                                                          │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │ Selected Unit Panel                              │     │
│  │ [Icon] Swordsmen (45/60) | Morale: ███░ | Stam: ██░│  │
│  │ [Walk] [March] [Run] | [Defensive] [Skirmish]   │     │
│  │ [Attack] [Move] [Hold] [Retreat]                 │     │
│  └─────────────────────────────────────────────────┘     │
│  [Unit Cards: clickable squad portraits along bottom]    │
└──────────────────────────────────────────────────────────┘
```

- **Bottom panel**: shows selected unit stats, stance toggles as clickable buttons
- **Unit cards**: row of squad portraits at screen bottom, click to select, double-click to center camera
- **Right-click context menu**: right-click on map for Move/Attack/Patrol; right-click on enemy for Attack/Charge
- **Drag selection**: click + drag to box-select multiple squads
- **Stance buttons**: toggle Walk/March/Run and Defensive/Skirmish with mouse clicks (hotkeys still work)
- **Tooltip on hover**: hover over any button/unit for detailed info

### C2. Campaign Map HUD
```
┌──────────────────────────────────────────────────────────┐
│  Day: 47 | Gold: 1,250 | Army: 85/120                   │
│  [Pause] [▶] [▶▶] [▶▶▶]                    [Mini-map]   │
│                                                          │
│                    CAMPAIGN MAP                           │
│                                                          │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │ [Quest Log] [Army Management] [Diplomacy]       │     │
│  │ Active Quest: Hunt Bandits near Iron Pass (2/5)  │     │
│  └─────────────────────────────────────────────────┘     │
│  [Notification feed: "Bandits spotted near Oakvale"]     │
└──────────────────────────────────────────────────────────┘
```

- **Top bar**: day counter, gold, army size, speed controls
- **Bottom bar**: quest tracker, quick-access buttons for major menus
- **Notification feed**: scrolling text for events (battles nearby, quest updates, diplomacy changes)
- **Click settlements** to open settlement interaction menu (B9)
- **Click armies** to inspect (if visible) — shows army composition estimate
- **Right-click** for contextual actions: move to, attack, enter settlement

### C3. Settlement Interaction UI
- Full-screen overlay when entering a settlement
- Tab-based navigation: Tavern | Recruit | Market | Quests | Garrison
- Each tab shows available actions as clickable cards/buttons
- Bounty board shown as a list of available quests with reward previews
- "Leave Settlement" button to return to campaign map

### C4. Army Management Panel
- Accessible from campaign HUD
- Shows all squads in player's army: type, count, morale, stamina
- Drag-and-drop to reorganize squad order
- Disband button per squad (soldiers are lost)
- Split army (future: create second army if player has a general to lead it)

---

## Part D: Additional Systems (Approved)

### D1. Terrain-Specific Battles
- Battle map generated based on campaign map terrain where armies meet:
  - **Plains**: open field, default
  - **Forest**: trees block ranged attacks, movement penalties, ambush bonuses
  - **Mountains**: elevation advantages, narrow passes
  - **Desert**: exhaustion penalties increased, cavalry bonuses
  - **Coastal**: half the map is water (impassable), narrow fighting area
  - **Settlement siege**: walls, gates, defensive positions (future depth)
- Terrain modifiers affect unit stats during battle

### D2. Seasons & Weather
- 4 seasons cycle: Spring → Summer → Autumn → Winter
- Each season lasts N campaign days
- Effects:

| Season | Campaign Effect | Battle Effect |
|--------|----------------|---------------|
| **Spring** | Normal movement | Normal |
| **Summer** | Desert factions +speed | Exhaustion builds faster |
| **Autumn** | Harvest — settlements produce bonus gold | Mud — cavalry charge reduced |
| **Winter** | Movement speed reduced, attrition in mountains | Snow — ranged accuracy reduced |

### D3. Supply Lines
- Armies far from friendly territory (owned/allied settlements) suffer:
  - Gradual morale loss
  - Increased desertion chance
  - Slower recovery from battles
- Encourages strategic settlement capture and discourages aimless wandering deep in enemy territory
- Supply wagons (future): slow units that extend supply range

### D4. Naval Movement (Future)
- Coastal settlements with ports allow armies to embark on ships
- Sea travel is fast but risky (pirate encounters, storms)
- Gives Maritime Republic a strategic advantage
- Marked as future — not in initial implementation

### D5. Tournaments & Arena
- Major towns periodically host tournaments
- Player can enter with a small squad (5-10 soldiers) for:
  - Gold prize
  - Reputation boost
  - Chance to recruit impressed warriors
- Bracket-style mini-battles against other competitors
- Good early-game gold/rep source before taking on full armies

### D6. Prisoner & Ransom System
- Defeated generals (NPC) can be captured instead of killed (random chance based on battle outcome)
- Captured generals can be:
  - **Ransomed**: return to their faction for gold. Faction rep improves slightly
  - **Recruited**: attempt to persuade them to join you. Success based on their loyalty + your reputation
  - **Executed**: permanently removes the general. Major reputation hit with their faction, minor hit with all factions. Intimidation bonus
- Player capture (on defeat):
  - Player is held captive for N days
  - Can pay ransom (if they have gold) to release immediately
  - Otherwise, escape after time passes (weaker army upon escape — some soldiers scattered)
  - Player's army disbands partially while captured

---

## Part E: Implementation Order (Revised)

Rough ordering from foundational → dependent:

### Batch 1: Battle Core Fixes
1. **A5** — Movement speed tiers (Walk/March/Run)
2. **A1** — Unit collision & mass system
3. **A2** — Distinct unit shapes
4. **A8** — Targeting indicator (hover only)
5. **A6** — General leveling fix

### Batch 2: Battle Tactics & Polish
6. **A4** — Defensive stance
7. **A3** — Skirmish stance (ranged units)
8. **A7** — Maximum range engagement (ranged/cavalry)
9. **C1** — Battle UI overhaul (mouse-friendly)

### Batch 3: Campaign Foundation
10. **B10** — Economy system (gold framework)
11. **B1** — Real-time campaign map
12. **B4** — Expanded map (factions, settlements, borders)
13. **B13** — Fog of war
14. **C2** — Campaign map HUD

### Batch 4: Campaign Interaction
15. **B9** — Interactable settlements
16. **C3** — Settlement interaction UI
17. **B11** — Recruitment system
18. **B2** — Factionless player start
19. **A9** — Faction specialty units

### Batch 5: Campaign Depth
20. **B5** — AI army behaviors
21. **B8** — Roaming armies + stronghold escalation + random events
22. **B3** — Quest system + bounty board
23. **B12** — Dual-layer diplomacy
24. **C4** — Army management panel
25. **B7** — Player faction creation

### Batch 6: Emergent & Advanced Systems
26. **B6** — General betrayal & persuasion
27. **D6** — Prisoner & ransom system
28. **D1** — Terrain-specific battles
29. **D2** — Seasons & weather
30. **D3** — Supply lines
31. **D5** — Tournaments & arena

### Batch 7: Future (Post-Prototype)
32. **D4** — Naval movement
33. Fantasy conversion (races, magic, monsters)

---

## Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Economy | **Yes** — implement gold framework now. Settlements generate income, armies cost upkeep, battles give loot |
| 2 | Recruitment | **Settlement-based** primary, mercenary bands secondary, quest rewards tertiary. Hiring mercs possible at taverns or on the road |
| 3 | Army size limits | **Yes** — scales with player level/renown. Hidden Weak/Normal/Elite classification ensures minor armies scale with player |
| 4 | Map scale | **Increase battle map**. Stronghold escalation system adds organic content to prevent emptiness |
| 5 | Fog of war | **Yes** — limited vision radius around player army and owned settlements |
| 6 | Diplomacy | **Dual-layer** — faction reputation AND individual general opinion, both tracked separately |
| 7 | Permadeath | **NPCs: permadeath. Player: capture + ransom** |
| 8 | Save system | **Overhaul** — robust serialization to handle real-time campaign state with many entities. Incremental/delta saves for performance |
