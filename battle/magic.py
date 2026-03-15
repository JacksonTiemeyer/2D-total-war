"""Winds of Magic system — global mana pool and spell casting in battle.

The Winds of Magic pool is shared between both sides of the battlefield.
It fluctuates with random surges and lulls, creating strategic tension
around when to cast.

Full implementation in Batch 11.
"""

import random

# ── Winds of Magic Constants ────────────────────────────────────────────

BASE_MANA_POOL = 100
MANA_REGEN_PER_SECOND = 0.5
SURGE_CHANCE_PER_MINUTE = 0.3    # 30% chance of a surge each minute
SURGE_AMOUNT = 30
LULL_CHANCE_PER_MINUTE = 0.2     # 20% chance of a lull each minute
LULL_AMOUNT = 20
MIN_MANA = 0
MAX_MANA = 200


class WindsOfMagic:
    """Global mana pool for a battle. Shared by all casters."""

    def __init__(self, initial_strength=None):
        # Random starting strength each battle (60-140)
        if initial_strength is None:
            initial_strength = random.randint(60, 140)
        self.mana = float(initial_strength)
        self.max_mana = MAX_MANA
        self.regen_rate = MANA_REGEN_PER_SECOND / 60.0  # per frame at 60 FPS
        self._surge_timer = 0

    def update(self):
        """Called each frame. Regenerates mana and checks for surges/lulls."""
        # Passive regeneration
        self.mana = min(self.max_mana, self.mana + self.regen_rate)

        # Surge/lull check every 60 frames (~1 second)
        self._surge_timer += 1
        if self._surge_timer >= 3600:  # every 60 seconds
            self._surge_timer = 0
            if random.random() < SURGE_CHANCE_PER_MINUTE:
                self.mana = min(self.max_mana, self.mana + SURGE_AMOUNT)
            elif random.random() < LULL_CHANCE_PER_MINUTE:
                self.mana = max(MIN_MANA, self.mana - LULL_AMOUNT)

    def can_cast(self, mana_cost):
        """Check if there's enough mana to cast a spell."""
        return self.mana >= mana_cost

    def spend_mana(self, amount):
        """Spend mana. Returns True if successful."""
        if self.mana < amount:
            return False
        self.mana -= amount
        return True

    def refund_mana(self, amount, refund_pct=0.5):
        """Refund mana when a spell is interrupted."""
        refund = amount * refund_pct
        self.mana = min(self.max_mana, self.mana + refund)

    @property
    def mana_pct(self):
        """Current mana as a percentage (0.0 to 1.0)."""
        return self.mana / self.max_mana


class SpellCaster:
    """Tracks spell casting state for a unit/hero that can cast spells.

    Attached to Squad or General objects that have the spellcaster trait.
    Full implementation in Batch 11.
    """

    def __init__(self, spell_list, winds):
        self.spell_list = list(spell_list)  # list of Spell objects
        self.winds = winds                   # reference to shared WindsOfMagic
        self.cooldowns = {}                  # {spell_name: frames_remaining}
        self.casting = None                  # currently casting Spell or None
        self.cast_timer = 0                  # frames remaining in cast
        self.cast_target = None              # (x, y) or target squad

    def can_cast_spell(self, spell):
        """Check if a specific spell can be cast right now."""
        if self.casting is not None:
            return False
        if self.cooldowns.get(spell.name, 0) > 0:
            return False
        return self.winds.can_cast(spell.mana_cost)

    def begin_cast(self, spell, target):
        """Begin casting a spell. Mana is spent upfront."""
        if not self.can_cast_spell(spell):
            return False
        self.winds.spend_mana(spell.mana_cost)
        self.casting = spell
        self.cast_timer = int(spell.cast_time_seconds * 60)  # frames
        self.cast_target = target
        return True

    def interrupt(self):
        """Interrupt current casting. Refunds 50% mana."""
        if self.casting:
            self.winds.refund_mana(self.casting.mana_cost)
            self.casting = None
            self.cast_timer = 0
            self.cast_target = None

    def update(self):
        """Tick casting timer. Returns completed Spell or None."""
        # Tick cooldowns
        for name in list(self.cooldowns):
            self.cooldowns[name] -= 1
            if self.cooldowns[name] <= 0:
                del self.cooldowns[name]

        # Tick casting
        if self.casting and self.cast_timer > 0:
            self.cast_timer -= 1
            if self.cast_timer <= 0:
                # Cast complete
                spell = self.casting
                target = self.cast_target
                self.cooldowns[spell.name] = int(spell.cooldown_seconds * 60)
                self.casting = None
                self.cast_target = None
                return spell, target
        return None
