import numpy as np

class WaveformGenerator:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate

    def generate_wave(self, frequency, duration, waveform_type='sine'):
        """Generate any type of waveform."""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)

        if waveform_type == 'sine':
            return self.generate_sine(t, frequency)
        elif waveform_type == 'square':
            return self.generate_square(t, frequency)
        elif waveform_type == 'triangle':
            return self.generate_triangle(t, frequency)
        elif waveform_type == 'saw':
            return self.generate_saw(t, frequency)
        else:
            return self.generate_sine(t, frequency)

    def generate_sine(self, t, frequency):
        return 0.5 * np.sin(2 * np.pi * frequency * t)

    def generate_square(self, t, frequency):
        return 0.5 * np.sign(np.sin(2 * np.pi * frequency * t))

    def generate_triangle(self, t, frequency):
        return 0.5 * (2 * np.abs(2 * (frequency * t % 1) - 1) - 1)

    def generate_saw(self, t, frequency):
        return 0.5 * (2 * (frequency * t % 1) - 1)
