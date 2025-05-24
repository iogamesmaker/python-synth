import numpy as np

class ADSREnvelope:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.set_parameters(0.1, 0.1, 0.7, 0.2)
        self.current_time = 0
        self.state = 'attack'
        self.level = 0

    def set_parameters(self, attack, decay, sustain, release):
        """Set ADSR parameters in seconds, sustain is amplitude level 0-1."""
        self.attack = max(0.01, attack)  # Minimum 10ms to prevent zeros
        self.decay = decay
        self.sustain = sustain
        self.release = release

        # Calculate rates (change per sample)
        self.attack_rate = 1.0 / (self.attack * self.sample_rate)
        self.decay_rate = (1.0 - self.sustain) / (self.decay * self.sample_rate)
        self.release_rate = self.sustain / (self.release * self.sample_rate)

    def get_envelope(self, buffer_size, is_release=False):
        """Generate envelope samples for the current buffer."""
        envelope = np.zeros(buffer_size)

        if is_release and self.state != 'release':
            self.state = 'release'

        for i in range(buffer_size):
            if self.state == 'attack':
                self.level += self.attack_rate
                if self.level >= 1.0:
                    self.level = 1.0
                    self.state = 'decay'

            elif self.state == 'decay':
                self.level -= self.decay_rate
                if self.level <= self.sustain:
                    self.level = self.sustain
                    self.state = 'sustain'

            elif self.state == 'release':
                self.level -= self.release_rate
                if self.level <= 0:
                    self.level = 0

            envelope[i] = max(0, min(1, self.level))

        return envelope

    def reset(self):
        """Reset envelope to initial state."""
        self.current_time = 0
        self.state = 'attack'
        self.level = 0

class AudioEffects:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate

    def apply_tremolo(self, audio, rate=5, depth=0.5):
        """Apply tremolo effect (amplitude modulation)."""
        t = np.linspace(0, len(audio)/self.sample_rate, len(audio))
        modulator = 1 - depth/2 * (1 + np.sin(2 * np.pi * rate * t))
        return audio * modulator

    def apply_delay(self, audio, delay_time=0.1, feedback=0.3):
        """Apply delay effect."""
        delay_samples = int(delay_time * self.sample_rate)
        if delay_samples >= len(audio):
            delay_samples = len(audio) - 1
        output = np.copy(audio)
        for i in range(3):  # Number of delay repetitions
            delayed = np.zeros_like(audio)
            delayed[delay_samples:] = audio[:-delay_samples] * (feedback ** (i+1))
            output += delayed
        return output / 2  # Normalize volume

    def apply_reverb(self, audio, room_size=0.5):
        """Apply simple reverb effect."""
        delays = [int(self.sample_rate * t) for t in [0.03, 0.05, 0.07]]
        delays = [min(d, len(audio) - 1) for d in delays]  # Ensure delays don't exceed buffer
        decay = [0.3, 0.2, 0.1]
        output = np.copy(audio)

        for delay, amp in zip(delays, decay):
            delayed = np.zeros_like(audio)
            delayed[delay:] = audio[:-delay] * (amp * room_size)
            output += delayed

        return output / 2
