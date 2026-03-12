"""Audio manager with procedurally generated placeholder sounds.

All sounds are synthesized at startup using numpy-free wave math so
the game requires no external audio assets.
"""

import math
import array
import pygame

# Global audio manager singleton
_manager = None


def get_audio():
    """Return the global AudioManager (lazy-initialized)."""
    global _manager
    if _manager is None:
        _manager = AudioManager()
    return _manager


class AudioManager:
    """Manages all game audio: procedural SFX and volume control."""

    def __init__(self):
        self.volume = 0.4
        self.sounds = {}
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.enabled = True
        except (pygame.error, Exception):
            self.enabled = False
            return

        self._generate_sounds()

    def _generate_sounds(self):
        """Generate all placeholder sounds procedurally."""
        self.sounds["charge"] = self._make_rising_sweep(0.4, 200, 600)
        self.sounds["melee_clash"] = self._make_noise_burst(0.15)
        self.sounds["arrow_volley"] = self._make_whoosh(0.3)
        self.sounds["ability"] = self._make_tone(0.3, 523, decay=True)  # C5
        self.sounds["rout"] = self._make_horn(0.5, 220)
        self.sounds["victory"] = self._make_fanfare(0.8)
        self.sounds["defeat"] = self._make_dirge(0.8)
        self.sounds["click"] = self._make_click(0.08)
        self.sounds["save"] = self._make_tone(0.2, 880, decay=True)

    def play(self, name):
        """Play a sound by name."""
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            sound.set_volume(self.volume)
            sound.play()

    def set_volume(self, vol):
        """Set master volume (0.0 - 1.0)."""
        self.volume = max(0.0, min(1.0, vol))

    # ── Sound Generators ─────────────────────────────────────────────

    def _make_samples(self, duration, sample_func):
        """Create a pygame.mixer.Sound from a sample function."""
        rate = 22050
        n_samples = int(rate * duration)
        samples = array.array("h")  # signed 16-bit
        for i in range(n_samples):
            t = i / rate
            val = sample_func(t, duration)
            # Clamp to 16-bit range
            val = max(-32767, min(32767, int(val * 32767)))
            samples.append(val)
        return pygame.mixer.Sound(buffer=samples)

    def _make_rising_sweep(self, duration, freq_start, freq_end):
        """Rising pitch sweep - used for charge sounds."""
        def sample(t, dur):
            freq = freq_start + (freq_end - freq_start) * (t / dur)
            envelope = 1.0 - (t / dur) * 0.3
            return math.sin(2 * math.pi * freq * t) * envelope * 0.5
        return self._make_samples(duration, sample)

    def _make_noise_burst(self, duration):
        """Short noise burst - used for melee clash."""
        import random
        # Pre-generate noise to avoid non-determinism in the sample func
        rate = 22050
        n = int(rate * duration)
        noise = [random.uniform(-1, 1) for _ in range(n)]
        def sample(t, dur):
            idx = int(t * rate)
            if idx >= n:
                return 0
            envelope = max(0, 1.0 - t / dur * 3)
            return noise[idx] * envelope * 0.4
        return self._make_samples(duration, sample)

    def _make_whoosh(self, duration):
        """Whoosh sound - used for arrow volleys."""
        import random
        rate = 22050
        n = int(rate * duration)
        noise = [random.uniform(-1, 1) for _ in range(n)]
        def sample(t, dur):
            idx = int(t * rate)
            if idx >= n:
                return 0
            # Bandpass-ish: mix noise with a sine
            envelope = math.sin(math.pi * t / dur)  # rise and fall
            tone = math.sin(2 * math.pi * 800 * t) * 0.2
            return (noise[idx] * 0.3 + tone) * envelope * 0.4
        return self._make_samples(duration, sample)

    def _make_tone(self, duration, freq, decay=False):
        """Pure tone with optional decay - used for ability activation."""
        def sample(t, dur):
            envelope = max(0, 1.0 - t / dur) if decay else 1.0
            return math.sin(2 * math.pi * freq * t) * envelope * 0.4
        return self._make_samples(duration, sample)

    def _make_horn(self, duration, freq):
        """Horn/trumpet sound - used for routing."""
        def sample(t, dur):
            # Square wave + slight vibrato
            vibrato = math.sin(2 * math.pi * 5 * t) * 10
            f = freq + vibrato
            envelope = min(1.0, t * 10) * max(0, 1.0 - t / dur * 0.5)
            wave = math.sin(2 * math.pi * f * t)
            # Add harmonics for horn-like timbre
            wave += 0.5 * math.sin(2 * math.pi * f * 2 * t)
            wave += 0.25 * math.sin(2 * math.pi * f * 3 * t)
            return wave / 1.75 * envelope * 0.35
        return self._make_samples(duration, sample)

    def _make_fanfare(self, duration):
        """Victory fanfare - ascending notes."""
        notes = [392, 440, 523, 659, 784]  # G4 A4 C5 E5 G5
        note_dur = duration / len(notes)
        def sample(t, dur):
            idx = min(int(t / note_dur), len(notes) - 1)
            freq = notes[idx]
            local_t = t - idx * note_dur
            envelope = max(0, 1.0 - local_t / note_dur * 0.5)
            wave = math.sin(2 * math.pi * freq * t)
            wave += 0.3 * math.sin(2 * math.pi * freq * 2 * t)
            return wave / 1.3 * envelope * 0.4
        return self._make_samples(duration, sample)

    def _make_dirge(self, duration):
        """Defeat dirge - descending minor notes."""
        notes = [392, 349, 330, 294, 262]  # G4 F4 E4 D4 C4
        note_dur = duration / len(notes)
        def sample(t, dur):
            idx = min(int(t / note_dur), len(notes) - 1)
            freq = notes[idx]
            local_t = t - idx * note_dur
            envelope = max(0, 1.0 - local_t / note_dur * 0.3)
            wave = math.sin(2 * math.pi * freq * t)
            return wave * envelope * 0.35
        return self._make_samples(duration, sample)

    def _make_click(self, duration):
        """Short UI click."""
        def sample(t, dur):
            envelope = max(0, 1.0 - t / dur * 5)
            return math.sin(2 * math.pi * 1000 * t) * envelope * 0.3
        return self._make_samples(duration, sample)
