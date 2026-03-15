# Phase 3: Fantasy Conversion & RPG Foundation

This document outlines Phase 3 — the transformation from a medieval Total War prototype
into a high-fantasy strategy RPG. Mount & Blade overworld, Total War combat, personal
story of rising from lone warband leader to king.

**Status**: PLANNING — awaiting green light to begin implementation.

**Phase 3 Goal**: The game becomes playable as a fantasy game with character creation,
10+ races, magic, traits, and a 60-80 settlement hand-crafted world map.

**Phase 4** (future): Living world — trade routes, shifting borders, random events,
demon invasion endgame crisis, deep AI diplomacy, settlement building depth.

**Phase 5** (future): Godot port.

---

## Part A: Player Character System

### A1. Character Creation Screen

New game state: `CHARACTER_CREATION` between `MAIN_MENU` and `CAMPAIGN`.

**Step 1 — Race Selection**:

| Race | Starting Region | Diplomacy Bias | Starting Units |
|------|----------------|---------------|----------------|
| Human | Central Plains | Neutral to all, slight bonus with Dwarves | Militia, Swordsmen |
| High Elf | Arcane Spires (east) | Friendly with Wood Elves, hostile to Dark Elves/Orcs | Spellblades, Mage Apprentices |
| Wood Elf | Northwest Forests | Friendly with High Elves, wary of Humans/Dwarves | Deepwood Rangers, Glade Runners |
| Sea Elf | Southwest Coast | Trade-friendly to all, close ties with Dark Elves | Corsair Marines, Tide Callers |
| Snow Elf | Far North Tundra | Isolationist — neutral-to-cold with everyone | Frost Wardens, Steppe Riders |
| Dark Elf | Underground/South) | Allied with Sea Elves (trade), hostile to High/Wood Elves | Shadowblades, Slave Soldiers |
| Dwarf | Northeast Mountains | Friendly with Humans, distrust Elves | Ironbreakers, Tunnel Fighters |
| Orc | Southeast Wastes | Hostile to most, grudging respect for strong factions | Orc Boyz, Goblin Skirmishers |
| Undead | Cursed Lands (scattered) | Hated by all living races | Skeleton Warriors, Zombies |
| Troll/Ogre | Wild Mountains | Neutral (feared), tradeable with Orcs | Troll Brutes, Ogre Bulls |
| Beastfolk | Southern Steppes | Wary of settled races, neutral to Orcs | Gor Warriors, Centigors |

- Race determines starting position on the world map
- Race determines base reputation modifiers with all factions
- Race determines which faction's settlements grant full recruitment access
- Other race recruitment available at reduced roster if reputation is high enough

**Step 2 — Class Selection**:

| Class | Combat Role | Progression Fantasy |
|-------|------------|-------------------|
| **Warlord** | Leadership, biggest armies, morale aura | Squad size bonuses, army capacity, multi-army command at high level |
| **Battlemage** | Spellcaster, access to magic from level 1 | Learn spell schools, devastating magic at high level, fewer troops |
| **Champion** | Personal combat, dueling, intimidation | Solo power, duel bonuses, fast kill-based leveling |
| **Rogue** | Economy, spies, sabotage, ambush | Bribe garrisons, incite rebellions, cheap mercs, assassination at high level |
| **Engineer** | Constructs, siege specialist, building bonuses | Build golems/automatons, siege equipment, mobile fortress at high level |
| **Necromancer** | Raise dead, undead summons, dark magic | Raise battlefield casualties, undead army that grows from combat |

- Class determines which ability tree the player unlocks (see A3)
- Class determines starting stats and level-up stat distribution
- Class affects how the player hero unit functions in battle

**Step 3 — Starting Trait Selection**:

Player picks ONE non-race trait that provides a permanent boon:

| Trait | Effect |
|-------|--------|
| **Born Leader** | +10% squad morale across all units |
| **Veteran Campaigner** | Start at level 3 instead of level 1 |
| **Silver Tongue** | +20% reputation gain with all factions |
| **Iron Constitution** | Player hero has +50% health in battle |
| **Merchant Prince** | Start with 2x gold, +15% settlement income |
| **Tactical Genius** | Unlock 2nd formation option from start |
| **Blessed by the Gods** | +10% magic resistance for all units |
| **Scrapper** | +25% loot from battles |

**Step 4 — Name and Confirm**.

### A2. Player Leveling (1-50)

The player character levels up through XP gained from battles, quests, and campaign actions.

| Level Range | Tier | Max Squads | Squad Size Mult | Unlocks |
|-------------|------|-----------|-----------------|---------|
| 1-5 | Wanderer | 2-3 | 0.5x | Fighting goblins, bandits, small encounters |
| 6-10 | Mercenary | 3-5 | 0.65x | Can take on minor armies, enter tournaments |
| 11-15 | Captain | 5-7 | 0.8x | Can capture villages, join factions as vassal |
| 16-20 | Minor Lord | 7-9 | 1.0x | Can capture towns, command respect |
| 21-30 | Major Lord | 9-12 | 1.15x | Can found own faction, siege castles |
| 31-40 | War Chief | 12-15 | 1.3x | Vassals of your own, faction leader |
| 41-50 | Overlord/King | 15-20 | 1.5x | Multiple armies (companions lead detachments), endgame power |

- **Squad Size Mult**: A level 1 player's Swordsmen squad of 24 would actually be 12 (0.5x). At level 20, full 24. At level 50, 36 (1.5x).
- **XP Sources**: Battle completion (scaled by enemy strength), quest completion, settlement capture, duel victories, diplomacy actions.
- **Stat Growth**: Each level grants stat points distributed by class (Warlord → leadership, Champion → combat, Battlemage → magic power, etc.)

### A3. Class Ability Trees

Each class gets abilities that unlock as they level. Replace the current Commander/Champion/Strategist system.

**Warlord Abilities** (unlocked every 5 levels):
1. **Rally** (Lv 1) — +20 morale to nearby squads
2. **Forced March** (Lv 5) — Temporarily boost army speed on campaign map
3. **Second Wind** (Lv 10) — Remove exhaustion from nearby squads
4. **Hold the Line** (Lv 15) — Prevent routing for 10 seconds
5. **Inspiring Charge** (Lv 20) — All squads get +50% charge bonus for 8 seconds
6. **War Cry** (Lv 25) — Mass morale boost + enemy morale penalty
7. **Iron Discipline** (Lv 30) — Squads immune to flanking morale penalty for 15s
8. **Detachment Command** (Lv 35) — Can split army, companion leads second force
9. **Legendary Commander** (Lv 40) — Passive: all squads get +15% all stats
10. **Overlord's Decree** (Lv 45) — Passive: army size limit +5, all upkeep -20%

**Battlemage Abilities**:
1. **Arcane Bolt** (Lv 1) — Single-target magic damage
2. **Mana Shield** (Lv 5) — Temporary damage reduction aura
3. **Elemental Blast** (Lv 10) — AOE damage (element based on learned school)
4. **Enchant Weapons** (Lv 15) — Nearby squads deal magic damage for 15s
5. **Summon Elemental** (Lv 20) — Summon a temporary Large combat unit
6. **Chain Lightning** (Lv 25) — Bouncing damage across multiple squads
7. **Arcane Storm** (Lv 30) — Massive AOE, Warhammer-level destruction
8. **Mass Teleport** (Lv 35) — Relocate a squad anywhere on battlefield
9. **Mage Lord** (Lv 40) — Passive: spell costs -30%, cooldowns -25%
10. **Cataclysm** (Lv 45) — Ultimate spell, can delete a squad

**Champion Abilities**:
1. **Bloodlust** (Lv 1) — +50% personal attack for 8s
2. **Intimidate** (Lv 5) — -15 morale to nearby enemies
3. **Challenge** (Lv 10) — Force enemy general into duel
4. **Rampage** (Lv 15) — AOE melee damage around hero
5. **Deathblow** (Lv 20) — Massive single-target damage
6. **Terrifying Presence** (Lv 25) — Passive terror aura
7. **Unstoppable** (Lv 30) — Immune to CC/slow effects for 15s
8. **Slayer** (Lv 35) — Anti-large bonus, bonus damage to heroes/monsters
9. **One-Man Army** (Lv 40) — Personal stats become monstrous
10. **Avatar of War** (Lv 45) — Temporary transformation: massive size, damage, health

**Rogue Abilities**:
1. **Ambush** (Lv 1) — Start battle with positional advantage
2. **Scout Network** (Lv 5) — See enemy army composition on campaign map
3. **Poisoned Weapons** (Lv 10) — Squad gains poison damage for 15s
4. **Bribe** (Lv 15) — Reduce enemy settlement garrison before siege
5. **Shadowstep** (Lv 20) — Teleport hero behind enemy lines
6. **Sabotage** (Lv 25) — Damage enemy settlement buildings on campaign map
7. **Incite Rebellion** (Lv 30) — Cause revolt in enemy territory
8. **Assassinate** (Lv 35) — Campaign action: attempt to kill enemy general
9. **Master of Coin** (Lv 40) — Passive: +40% all gold income
10. **Shadow War** (Lv 45) — Passive: enemies cannot see your army on campaign map

**Engineer Abilities**:
1. **Construct Golem** (Lv 1) — Build a basic combat automaton (campaign, takes time)
2. **Fortify Position** (Lv 5) — Create temporary barricade on battlefield
3. **Field Artillery** (Lv 10) — Deploy a cannon/ballista on battlefield
4. **Improved Constructs** (Lv 15) — Golems get +30% stats
5. **Siege Expert** (Lv 20) — +50% wall/gate damage in sieges
6. **Mechanical Army** (Lv 25) — Can field up to 3 golem squads simultaneously
7. **Experimental Weaponry** (Lv 30) — Squad gains fire or explosive ranged attacks
8. **Mobile Fortress** (Lv 35) — Campaign: deployable defensive position
9. **Master Engineer** (Lv 40) — Passive: golem build time halved, no upkeep
10. **War Machine** (Lv 45) — Deploy a Massive-class siege engine in battle

**Necromancer Abilities**:
1. **Raise Dead** (Lv 1) — Raise skeleton squad from battlefield casualties
2. **Life Drain** (Lv 5) — Steal health from enemies, heal self
3. **Summon Wraith** (Lv 10) — Summon ethereal unit (50% phys resist)
4. **Corpse Explosion** (Lv 15) — Detonate dead bodies for AOE damage
5. **Death Aura** (Lv 20) — Nearby enemies take DOT, undead allies heal
6. **Animate Legion** (Lv 25) — Raise multiple squads at once
7. **Soul Harvest** (Lv 30) — Every kill restores mana/ability charges
8. **Dread Lord** (Lv 35) — Terror aura + all undead gain fear immunity
9. **Lich Transformation** (Lv 40) — Passive: hero becomes undead (regen, no morale, weakness to holy)
10. **Army of the Damned** (Lv 45) — Raise an entire defeated army as undead servants

### A4. Companion System

Named NPCs that can be recruited and serve as additional hero units.

- **Finding companions**: taverns, quest rewards, post-battle recruitment of captured generals
- **Max companions**: scales with level (1 at Lv 5, 2 at Lv 15, 3 at Lv 25, 4 at Lv 35, 5 at Lv 45)
- **Each companion has**: name, race, class, level, abilities, loyalty, personality
- **In battle**: companions deploy as additional hero units alongside the player
- **On campaign**: high-level companions (Lv 35+ Warlord) can lead detached armies
- **Loyalty**: companions may leave if mistreated (losing too many battles, unpaid, betraying their race)
- **Leveling**: companions gain XP from battles they participate in

### A5. Capture & Ransom (Player Defeat)

When the player loses a battle:
- Player is captured, NOT killed (never permadeath)
- Captor faction holds player for 5-15 days
- Player can pay ransom (gold) for immediate release
- Otherwise, automatic escape after the holding period
- On capture: army partially disbands (lose 30-50% of squads), companions scatter (rejoin after release)
- Gold and items preserved (minus ransom if paid)

---

## Part B: Fantasy Races & Unit Roster

### B1. Trait System

Tags on unit definitions that enable special rules in combat.

**Movement Traits**:
- `flying` — Ignores terrain, can move over obstacles, vulnerable to ranged
- `burrowing` — Can tunnel under walls in siege, ambush from underground
- `aquatic` — Can cross water terrain, bonus fighting near water
- `mounted` — Cavalry-class movement, charge bonuses (replaces `is_cavalry`)

**Durability Traits**:
- `undead` — Immune to morale, immune to fear/terror, takes bonus holy damage
- `regenerating` — Recovers HP slowly during battle
- `ethereal` — 50% physical damage reduction, vulnerable to magic
- `armored_construct` — Immune to morale, immune to poison, no exhaustion
- `large` — Takes bonus from anti-large, harder to flank
- `massive` — Single-entity unit, area attacks, terror aura

**Offensive Traits**:
- `fire_attack` — Deals fire damage, bonus vs regenerating/undead
- `poison_attack` — Damage over time on hit
- `anti_large` — Bonus damage vs large/massive units
- `anti_infantry` — Bonus damage vs normal/small units
- `fear` — Causes morale penalty to nearby enemies
- `terror` — Stronger fear effect (dragons, demons, massive units)
- `frenzy` — Attack speed increases as health drops

**Special Traits**:
- `spellcaster` — Can cast spells from a spell list
- `summoner` — Can summon temporary units
- `unbreakable` — Cannot rout (but can still die)
- `stealthy` — Hidden until attacking or within close range
- `fire_while_moving` — (existing, becomes a trait)
- `can_brace` — (existing, becomes a trait)

### B2. Damage Type System

Six damage types replace the current flat damage model.

| Type | Strong Against | Weak Against | Special |
|------|---------------|-------------|---------|
| `physical` | Default | High armor | Standard melee/ranged |
| `magical` | Armored units | Magic-resistant | Ignores physical armor |
| `fire` | Regenerating, Undead, Treants | Fire-immune (Demons) | DOT component |
| `holy` | Undead, Demons | Living (reduced) | Anti-evil bonus |
| `poison` | Living units | Undead, Constructs (immune) | Stacking DOT |
| `ice` | Flying, Cavalry (slows) | Ice-immune (Snow Elves) | Slow effect |

Each unit has:
- `damage_type` — Primary damage dealt (default: physical)
- `magic_resistance` — 0-100 scale, reduces magical/elemental damage
- `damage_vulnerabilities` — List of types that deal bonus damage
- `damage_immunities` — List of types that deal no damage

### B3. Unit Size Categories

| Size | Examples | Soldiers Per Squad | Interactions |
|------|----------|-------------------|-------------|
| `small` | Goblins, Gnomes | 30-40 | Bonus evasion, penalty to damage output |
| `normal` | Humans, Elves, Orcs, Dwarves | 16-24 | Standard baseline |
| `large` | Cavalry, Trolls, Treants, Ogres | 4-12 | Charge bonus, anti-large weapons effective |
| `massive` | Dragons, Mushroom Hulks, Tanks, Golems | 1 | Single-entity, area attacks, terror |

### B4. Racial Unit Rosters

Each race gets 8-12 unique unit types spanning infantry, ranged, cavalry, elite, and special.

**HUMANS** — Renaissance/gunpowder theme:
- Levy Militia (cheap infantry, small squads early game)
- Men-at-Arms (reliable swords & shields)
- Halberdiers (anti-large polearms, can_brace)
- Longbowmen (long-range archers)
- Handgunners (short-range, armor-piercing, gunpowder)
- Knights (heavy cavalry, devastating charge)
- Pistoliers (mounted ranged, fire_while_moving)
- War Wagon (massive, mobile fortress, carries gunners)
- Cannon (massive, siege artillery, extreme range)
- Greatswords (elite two-handed infantry)

**HIGH ELVES** — Magic and elegance:
- Spellblades (infantry with magical weapons, magic damage)
- Phoenix Guard (elite halberd infantry, fire-immune)
- Mage Apprentices (ranged, spellcaster trait, arcane bolts)
- Silver Helms (medium cavalry, anti-large)
- Dragon Princes (elite cavalry, fire_attack)
- Eagle Archers (long-range, high accuracy)
- Archmage (hero unit, powerful spellcaster)
- Phoenix (massive, flying, fire_attack, regenerating)

**WOOD ELVES** — Forest guerrillas:
- Glade Runners (fast skirmisher infantry)
- Deepwood Rangers (elite archers, stealthy)
- Wardancers (unbreakable melee, frenzy)
- Wild Riders (fast cavalry, charge specialists)
- Treekin (large, regenerating, living wood)
- Treant (massive, summoned or recruited, anti-infantry)
- Giant Eagle (large, flying, fast)
- Waywatchers (elite stealthy ranged, armor-piercing)

**SEA ELVES** — Naval pirates and water magic:
- Corsair Reavers (fast melee infantry, poison_attack)
- Tide Callers (ranged, spellcaster, ice damage)
- Harpoonists (ranged, anti_large, armor-piercing)
- Sea Dragon Knights (large cavalry, aquatic)
- Storm Mages (hero support, chain lightning spells)
- Kraken Spawn (massive, summoned, aquatic, terror)

**SNOW ELVES** — Steppe warrior-monks, ice magic:
- Frost Wardens (heavy infantry, ice-immune, can_brace)
- Steppe Riders (fast cavalry, fire_while_moving, bows)
- Ice Shamans (ranged, spellcaster, ice damage)
- Mammoth Riders (massive, mounted, terror, charge bonus)
- Blizzard Guard (elite infantry, ice_attack, anti_large)
- Frost Wyrm (massive, flying, ice_attack, terror)

**DARK ELVES** — Cruelty, demons, debuffs:
- Shadowblades (melee infantry, poison_attack, stealthy)
- Slave Soldiers (cheap fodder, large squads, expendable)
- Darkshards (crossbow ranged, armor-piercing)
- Cold One Knights (large cavalry, fear, armored mounts)
- Witch Elves (frenzy, unbreakable, glass cannon)
- Hydra (massive, regenerating, terror, multi-attack)
- Dark Sorceress (hero, spellcaster, debuff specialist)

**DWARVES** — Mountain holds, mech suits, heavy armor:
- Ironbreakers (elite heavy infantry, highest armor)
- Tunnel Fighters (infantry, burrowing, anti_large)
- Thunderers (ranged, gunpowder, armor-piercing)
- Gyrocopter (large, flying, ranged, fire_attack)
- Mech Suit (large, armored_construct, melee powerhouse)
- Cannon (massive, artillery, extreme range)
- Slayers (frenzy, unbreakable, anti_large, no armor)
- Runesmith (hero, magical buffs, enchant weapons)

**ORCS** — Brute force and numbers:
- Orc Boyz (basic melee infantry, decent stats)
- Goblin Skirmishers (small, cheap, ranged, large squads)
- Black Orc Elites (heavy infantry, armored, anti_infantry)
- Boar Riders (large cavalry, devastating charge)
- Troll (large, regenerating, fear, stupid — may rampage)
- Warboss (hero, champion-type, intimidation aura)
- Rock Lobba (massive, catapult, siege)
- Goblin Wolf Riders (small, fast cavalry, harass)

**UNDEAD** — Necromancy and attrition:
- Skeleton Warriors (basic infantry, undead, no morale, fragile)
- Zombies (slow infantry, undead, large squads, regenerating)
- Grave Guard (elite undead infantry, armored)
- Black Knights (large cavalry, undead, ethereal charge)
- Wraith (ethereal, fear, magic damage)
- Varghulf (large, flying, regenerating, terror)
- Bone Giant (massive, undead, anti_infantry)
- Necromancer Lord (hero, summoner, raise dead abilities)

**TROLLS/OGRES** — Monster faction, few but mighty:
- Ogre Bulls (large, basic melee, high health)
- Troll Warriors (large, regenerating, fear)
- Ogre Leadbelchers (large, ranged, crude cannons)
- Stone Troll (large, magic-resistant, armored)
- Sabretusk Pack (cavalry-speed, anti_infantry)
- Giant (massive, terror, anti_infantry, area attacks)
- Ogre Tyrant (hero, champion-type, eating restores health)

**BEASTFOLK** — Fast, cavalry-focused:
- Gor Warriors (basic melee infantry, fast)
- Ungor Raiders (ranged skirmishers, cheap)
- Centigors (large, mounted, fast, charge bonus)
- Minotaurs (large, frenzy, fear, devastating charge)
- Razorgor Chariot (large, anti_infantry, charge specialist)
- Beastlord (hero, champion, terror aura)
- Jabberslythe (massive, flying, terror, poison_attack)

**FERAL GOBLINS** (roaming, non-playable faction):
- Goblin Mob (small, cheap, swarm)
- Goblin Archers (small, low damage, large squad)
- Squig Riders (small, fast, unpredictable)
- Troll (large, hired/allied with goblins)
- Goblin Shaman (spellcaster, unpredictable magic)

**DEMONS** (endgame crisis, non-playable):
- Bloodletters (elite melee, fire_attack, fear)
- Hellfire Archers (ranged, fire damage, armor-piercing)
- Hellhounds (fast, fire_attack, fear)
- Demon Prince (massive, flying, terror, spellcaster)
- Balrog (massive, fire-immune, terror, regenerating)
- Pit Fiend (hero, spellcaster, summoner)

---

## Part C: Magic System

### C1. Winds of Magic

Global mana pool shared by all spellcasters on the battlefield.

- **Pool size**: 100 base, fluctuates each battle (randomly 60-140)
- **Regeneration**: Slow passive regen (1 per 2 seconds)
- **Wind Strength Events**: Random surges (+30 mana) or lulls (-20 mana) during battle
- **Both sides draw from the same pool** — casting drains it for everyone
- **High Elf bonus**: +20% mana regeneration rate
- **Undead bonus**: Raise Dead costs 50% less mana
- **Dwarf penalty**: Cannot use Winds of Magic (rune magic uses separate charges)

### C2. Spell Schools

Spellcasters learn spells from one or more schools based on race and class.

| School | Damage Type | Theme | Primary Users |
|--------|-----------|-------|---------------|
| **Fire** | Fire | Destruction, DOT, anti-undead | High Elves, Humans, Demons |
| **Ice** | Ice | Slow, control, defensive | Snow Elves, some Humans |
| **Shadow** | Magical | Debuffs, stealth, fear | Dark Elves, Necromancers |
| **Life** | Holy | Healing, buffs, anti-undead | Wood Elves, High Elves |
| **Death** | Magical | Necromancy, summons, drain | Undead, Dark Elves, Necromancer class |
| **Heavens** | Magical | Lightning, accuracy buffs, prophecy | High Elves, Humans |
| **Beasts** | Physical | Summon animals, buff cavalry | Wood Elves, Beastfolk |
| **Metal** | Physical | Armor buffs/debuffs, transmutation | Dwarves (rune variant), Engineers |

### C3. Spell List (Core — 4-6 per school)

**Fire School**:
- Fireball (30 mana) — AOE fire damage, medium radius
- Flame Wall (20 mana) — Create a line of fire that damages units crossing it
- Inferno (50 mana) — Large AOE, massive damage, long cast time
- Blazing Sword (15 mana) — Buff: target squad deals fire damage for 15s

**Ice School**:
- Frost Bolt (20 mana) — Single target damage + slow
- Blizzard (40 mana) — AOE ice damage + movement speed debuff
- Ice Wall (25 mana) — Create impassable ice barrier for 20s
- Freeze (30 mana) — Immobilize target squad for 5s

**Shadow School**:
- Shadow Bolt (15 mana) — Fast single target magic damage
- Dread (25 mana) — AOE morale penalty
- Cloak of Shadows (20 mana) — Target squad becomes stealthy for 15s
- Soul Drain (35 mana) — Damage enemy, heal caster

**Life School**:
- Healing Light (20 mana) — Restore HP to target squad
- Shield of Thorns (25 mana) — Reflect damage on target squad
- Regrowth (30 mana) — HOT (heal over time) on large area
- Banishment (40 mana) — Massive damage vs undead/demons only

**Death School**:
- Raise Dead (25 mana) — Summon skeleton squad from corpses
- Spirit Leech (20 mana) — Single target damage, ignores armor
- Curse of Years (35 mana) — DOT that accelerates over time
- Wind of Death (60 mana) — Line AOE, devastating magic damage

**Heavens School**:
- Lightning Bolt (25 mana) — Fast single target, armor-piercing
- Chain Lightning (40 mana) — Bounces between nearby enemies
- Comet (55 mana) — Delayed massive AOE (2s delay, huge damage)
- Wind Blast (15 mana) — Push back and scatter a formation

**Beasts School**:
- Summon Wolves (20 mana) — Temporary wolf pack (fast, flankers)
- Wild Fury (25 mana) — Buff: target squad gains frenzy
- Amber Spear (30 mana) — Magic projectile, anti_large
- Summon Manticore (50 mana) — Temporary massive flying unit

**Metal School** (Rune variant for Dwarves):
- Enchant Armor (20 mana) — +30% armor for target squad
- Searing Doom (30 mana) — AOE that does bonus damage to armored targets
- Transmutation (25 mana) — Reduce enemy armor by 50% for 15s
- Rune of Wrath (40 mana) — Place rune on ground, explodes when enemies cross

### C4. Casting Mechanics

- **Cast time**: Most spells take 1-3 seconds to cast (visible wind-up animation)
- **Interruption**: If the caster takes damage during casting, the spell is cancelled (mana refunded 50%)
- **Range**: Most spells have a range limit; caster must be within range of target
- **Cooldowns**: Each spell has an individual cooldown (15-60 seconds)
- **No counter-spells**: Spells cannot be dispelled, but effects can be outplayed
- **Friendly fire**: AOE spells can hit friendly units if poorly aimed

---

## Part D: World Map Overhaul

### D1. Map Expansion

- **Map size**: 6000x4500 (up from 4000x3000)
- **60-80 hand-crafted settlements** with fixed positions every playthrough
- **Geographic zones** with distinct terrain:
  - Central Plains — Human kingdoms, most settlements, road network
  - Northwest Forests — Wood Elf territory, dense canopy, hidden paths
  - Northeast Mountains — Dwarf holds, few but wealthy and defensible
  - Eastern Highlands — High Elf arcane spires, magical terrain
  - Southwest Coast/Islands — Sea Elf ports, naval territory
  - Southeast Wastes — Orc warbands, harsh terrain, scattered strongholds
  - Far North Tundra — Snow Elf territory, sparse but defensible
  - Underground entrances (south) — Dark Elf access points
  - Cursed Lands (scattered) — Undead territory, blighted terrain
  - Wild Mountains — Troll/Ogre lairs
  - Southern Steppes — Beastfolk roaming grounds
  - Mushroom Forests (small pockets) — Gnome enclaves (placeholder for Phase 4+)

### D2. Settlement Distribution

Rough allocation across 70 settlements:

| Region / Race | Villages | Towns | Castles | Total |
|--------------|----------|-------|---------|-------|
| Humans (Central) | 5 | 4 | 3 | 12 |
| High Elves (East) | 3 | 2 | 2 | 7 |
| Wood Elves (Northwest) | 3 | 2 | 1 | 6 |
| Sea Elves (Southwest) | 2 | 3 | 1 | 6 |
| Snow Elves (North) | 3 | 1 | 2 | 6 |
| Dark Elves (Underground/South) | 2 | 2 | 2 | 6 |
| Dwarves (Northeast) | 2 | 2 | 3 | 7 |
| Orcs (Southeast) | 4 | 2 | 1 | 7 |
| Undead (Cursed Lands) | 3 | 1 | 2 | 6 |
| Troll/Ogre (Wild) | 2 | 1 | 1 | 4 |
| Beastfolk (Steppes) | 2 | 1 | 0 | 3 |
| **Total** | **31** | **21** | **18** | **70** |

Plus ~5-8 neutral/contested settlements at border regions.

### D3. Racial Starting Armies

AI factions begin with 3-5 armies each. The player starts with 1 small warband.

---

## Part E: Data Architecture

### E1. UnitStats Overhaul

The `UnitStats` dataclass in `data/unit_types.py` needs significant expansion:

```python
@dataclass
class UnitStats:
    # Identity
    name: str
    race: str                          # NEW: "human", "high_elf", etc.
    description: str = ""

    # Core stats (existing, kept)
    health: int = 100
    melee_attack: int = 10
    melee_defense: int = 10
    speed: float = 2.0
    charge_bonus: int = 5
    armor: int = 10
    shield: bool = False
    squad_size: int = 20
    cost: int = 100
    upkeep: int = 10
    weapon_strength: int = 10
    armor_penetration: int = 5

    # Ranged (existing, kept)
    ranged_attack: int = 0
    ranged_strength: int = 0
    ranged_armor_penetration: int = 0
    range_distance: int = 0

    # Movement/combat flags (existing → converted to traits)
    mass: float = 1.5
    exhaustion_rate: float = 1.0

    # NEW: Trait system
    traits: tuple = ()                 # e.g., ("mounted", "fire_attack", "large")
    size_category: str = "normal"      # "small", "normal", "large", "massive"
    damage_type: str = "physical"      # primary damage dealt
    magic_resistance: int = 0          # 0-100 scale
    damage_vulnerabilities: tuple = () # e.g., ("fire", "holy")
    damage_immunities: tuple = ()      # e.g., ("poison",)

    # NEW: Magic
    spell_school: str = ""             # if spellcaster trait: "fire", "ice", etc.
    spell_list: tuple = ()             # specific spell names available

    # Derived from traits (computed, not stored)
    @property
    def is_cavalry(self): return "mounted" in self.traits
    @property
    def is_ranged(self): return self.ranged_attack > 0 and self.range_distance > 0
    @property
    def can_brace(self): return "can_brace" in self.traits
    @property
    def is_flying(self): return "flying" in self.traits
```

### E2. Player Character Data Model

New dataclass or class in `campaign/player.py`:

```python
class PlayerCharacter:
    name: str
    race: str              # determines faction affinity, starting position
    player_class: str      # "warlord", "battlemage", "champion", "rogue", "engineer", "necromancer"
    level: int = 1
    xp: int = 0
    trait: str = ""        # selected starting trait

    # Stats (grow with level, weighted by class)
    leadership: int        # army size, morale aura
    combat: int            # personal melee power
    magic_power: int       # spell damage, mana pool contribution
    cunning: int           # economic bonuses, ambush chance
    engineering: int       # construct quality, siege bonuses

    # Abilities (unlocked by class + level)
    abilities: list        # active abilities

    # Companions
    companions: list       # list of CompanionCharacter

    # Reputation per faction
    reputation: dict       # {race: int} — affects recruitment, diplomacy
```

### E3. File Structure Changes

New files needed:
- `data/races.py` — Race definitions, diplomacy matrices, starting data
- `data/spells.py` — Spell definitions (name, school, cost, cooldown, effect)
- `data/traits.py` — Trait definitions and combat rule implementations
- `campaign/player.py` — PlayerCharacter class, leveling, class abilities
- `campaign/companion.py` — Companion system
- `battle/magic.py` — Winds of Magic pool, spell casting, spell effects
- `campaign/char_creation.py` — Character creation UI and flow

Modified files:
- `data/unit_types.py` — Complete rewrite with fantasy roster + trait system
- `campaign/campaign_scene.py` — Integrate player character, new map, racial settlements
- `campaign/faction.py` — Replace medieval factions with racial factions
- `campaign/settlement.py` — 70 settlements, racial ownership
- `battle/squad.py` — Trait-aware combat (damage types, size interactions)
- `battle/battle_scene.py` — Magic system integration, trait visuals
- `battle/soldier.py` — Damage type handling, trait effects
- `core/settings.py` — New constants for all fantasy systems
- `core/save_system.py` — Save/load player character, magic state
- `main.py` — Character creation state, updated flow

---

## Part F: Implementation Order

### Batch 7: Data Foundation
1. **B1** — Trait system (`data/traits.py`)
2. **B2** — Damage type system (modify `soldier.py`, `squad.py`)
3. **B3** — Unit size categories
4. **E1** — UnitStats overhaul (expand dataclass, backward-compatible)
5. **E3** — New file scaffolding (empty modules with interfaces)

### Batch 8: Fantasy Unit Roster
6. **B4** — All racial unit definitions in `data/unit_types.py` (100+ units)
7. **D1** — New map dimensions (6000x4500)
8. **D2** — 70 hand-crafted settlement positions and ownership
9. Faction overhaul — replace medieval factions with racial factions in `faction.py`

### Batch 9: Player Character
10. **A1** — Character creation screen (race, class, trait, name)
11. **A2** — Player leveling 1-50 (XP, squad size scaling, unlock gates)
12. **E2** — PlayerCharacter data model (`campaign/player.py`)
13. **A5** — Capture & ransom rework for fantasy context

### Batch 10: Class Abilities & Companions
14. **A3** — Class ability trees (6 classes x 10 abilities)
15. **A4** — Companion system (recruitment, battle deployment, leveling)
16. Integrate player hero + companions into battle scene

### Batch 11: Magic System
17. **C1** — Winds of Magic pool (global mana, fluctuation, regen)
18. **C2** — Spell schools and spell definitions (`data/spells.py`)
19. **C3** — Spell casting in battle (targeting, cast time, interruption, effects)
20. **C4** — Casting mechanics, spell visuals (circles, projectiles, AOE indicators)

### Batch 12: Integration & Polish
21. Save/load overhaul for all new systems
22. AI updates — racial army composition, spell-aware battle AI
23. Campaign AI — racial diplomacy, faction behavior differences
24. Balance pass — unit costs, spell damage, leveling curve
25. Feral goblin strongholds as roaming encounters
26. UI updates — character sheet, spell bar, companion panel

---

## Resolved Design Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | Game identity | **Strategy RPG** — M&B overworld, TW combat, personal story |
| 2 | Player progression | **Level 1-50**, squad sizes scale with level, Wanderer → King |
| 3 | Races | **11 playable** (5 elf subraces, Human, Dwarf, Orc, Undead, Troll, Beastfolk) + Goblins (feral) + Demons (crisis) |
| 4 | Elf faction structure | **Mix** — High+Wood Elves friendly, Sea+Dark Elves trading, Snow Elves isolationist |
| 5 | Gnomes | **Deferred to Phase 4+** — mushroom theme, separate from Dwarves |
| 6 | Classes | **6**: Warlord, Battlemage, Champion, Rogue, Engineer, Necromancer |
| 7 | Magic | **Winds of Magic** — shared global pool, Warhammer-level power, interruptible |
| 8 | Demons | **Event-only** — endgame crisis at year 5, not playable |
| 9 | Player death | **Capture & ransom** — never permadeath |
| 10 | Companions | **Yes** — named NPCs, hero units in battle, can lead detached armies |
| 11 | Map | **6000x4500**, 70 settlements, hand-crafted, same every playthrough |
| 12 | Traits/damage types | **Approved** — trait tags on units, 6 damage types, 4 size categories |
| 13 | Victory condition | **Survive the demon invasion** (endgame crisis, Phase 4 implementation) |
| 14 | Code quality | **Clean architecture** — eventual Godot port, maintain separation of concerns |
| 15 | Phase split | **Phase 3** = fantasy foundation. **Phase 4** = living world + endgame. **Phase 5** = Godot |

---

## Open Items for Phase 4

These were discussed but are explicitly deferred:

- Demon invasion endgame crisis (mechanics, portal spawning, faction alliances with demons)
- Trade routes and caravans
- Shifting faction borders
- Random world events (plagues, civil wars, crusades)
- Settlement building chains (unique system — TBD)
- Naval movement
- Gnome faction (mushroom theme)
- Deep AI diplomacy with racial personality
- Procedural companion generation
- Advanced siege mechanics for fantasy (flying units over walls, burrowing under, etc.)
