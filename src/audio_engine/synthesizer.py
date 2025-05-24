import numpy as np
import sounddevice as sd
import threading
from collections import defaultdict
from .waveforms import WaveformGenerator
from .effects import ADSREnvelope, AudioEffects

class Voice:
    """Represents a single voice in the synthesizer."""
    def __init__(self, frequency, velocity=1.0):
        self.frequency = frequency
        self.velocity = velocity
        self.phase = 0
        self.is_active = True
        self.envelope = ADSREnvelope()  # Each voice gets its own envelope
        self.release_start = False

class Synthesizer:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.voices = {}  # frequency -> Voice
        self.buffer_size = 1024
        self.is_playing = False
        self.stream = None

        # Audio components
        self.waveform_gen = WaveformGenerator(sample_rate)
        self.effects = AudioEffects(sample_rate)

        # Parameters
        self.volume = 0.5
        self.waveform_type = 'sine'
        self.effects_params = {
            'tremolo_rate': 5,
            'tremolo_depth': 0.3,
            'delay_time': 0.1,
            'delay_feedback': 0.3,
            'reverb_size': 0.3
        }
        self.effects_enabled = {
            'tremolo': False,
            'delay': False,
            'reverb': False
        }

        # ADSR default parameters
        self.adsr_params = {
            'attack': 0.1,
            'decay': 0.1,
            'sustain': 0.7,
            'release': 0.2
        }

        # Set up sounddevice
        sd.default.samplerate = self.sample_rate
        sd.default.channels = 1
        sd.default.dtype = 'float32'

    def start_stream(self):
        """Initialize and start the audio stream."""
        self.is_playing = True
        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                callback=self._audio_callback,
                blocksize=self.buffer_size
            )
            self.stream.start()
            print("Audio stream started successfully")
        except Exception as e:
            print(f"Error starting audio stream: {e}")
            print("\nAvailable audio devices:")
            print(sd.query_devices())
            raise

    def _audio_callback(self, outdata, frames, time, status):
        """Audio callback function for real-time audio synthesis.

        Args:
            outdata: numpy array for output audio data
            frames: number of frames to generate
            time: stream time
            status: status of the stream
        """
        if status:
            print(status)

        # Generate audio for all active voices
        audio = np.zeros(frames)

        for freq, voice in list(self.voices.items()):
            if voice.is_active:
                # Generate basic waveform
                wave = self.waveform_gen.generate_wave(
                    freq, frames/self.sample_rate, self.waveform_type
                )

                # Get envelope for this voice
                envelope = voice.envelope.get_envelope(
                    frames,
                    is_release=voice.release_start
                )

                # If release is complete, remove the voice
                if voice.release_start and np.all(envelope < 0.001):
                    del self.voices[freq]
                    continue

                wave *= envelope * voice.velocity
                audio += wave

        # Apply effects if enabled
        if self.effects_enabled['tremolo']:
            audio = self.effects.apply_tremolo(
                audio,
                self.effects_params['tremolo_rate'],
                self.effects_params['tremolo_depth']
            )

        if self.effects_enabled['delay']:
            audio = self.effects.apply_delay(
                audio,
                self.effects_params['delay_time'],
                self.effects_params['delay_feedback']
            )

        if self.effects_enabled['reverb']:
            audio = self.effects.apply_reverb(
                audio,
                self.effects_params['reverb_size']
            )

        # Apply master volume and prevent clipping
        audio = np.clip(audio * self.volume, -1, 1)
        outdata[:] = audio.reshape(-1, 1)

    def play_note(self, frequency, state, velocity=1.0):
        """Play or release a note.

        Args:
            frequency (float): The frequency of the note in Hz
            state (bool): True for note on, False for note off
            velocity (float): The velocity/volume of the note (0.0 to 1.0)
        """
        if state:  # Note On
            voice = Voice(frequency, velocity)
            voice.envelope.set_parameters(
                self.adsr_params['attack'],
                self.adsr_params['decay'],
                self.adsr_params['sustain'],
                self.adsr_params['release']
            )
            self.voices[frequency] = voice
        else:  # Note Off
            if frequency in self.voices:
                self.voices[frequency].release_start = True

    def set_waveform(self, waveform_type):
        """Set the current waveform type.

        Args:
            waveform_type (str): One of 'sine', 'square', 'triangle', 'saw'
        """
        if waveform_type in ['sine', 'square', 'triangle', 'saw']:
            self.waveform_type = waveform_type

    def set_adsr(self, attack, decay, sustain, release):
        """Set ADSR envelope parameters.

        Args:
            attack (float): Attack time in seconds
            decay (float): Decay time in seconds
            sustain (float): Sustain level (0.0 to 1.0)
            release (float): Release time in seconds
        """
        self.adsr_params.update({
            'attack': max(0.01, float(attack)),
            'decay': max(0.01, float(decay)),
            'sustain': max(0.0, min(1.0, float(sustain))),
            'release': max(0.01, float(release))
        })

    def set_effect_param(self, param, value):
        """Set an effect parameter.

        Args:
            param (str): The parameter name
            value (float): The parameter value
        """
        if param in self.effects_params:
            self.effects_params[param] = float(value)

    def toggle_effect(self, effect, state):
        """Enable/disable an effect.

        Args:
            effect (str): The effect name
            state (bool): True to enable, False to disable
        """
        if effect in self.effects_enabled:
            self.effects_enabled[effect] = bool(state)

    def set_volume(self, volume):
        """Set the master volume.

        Args:
            volume (float): Volume level (0.0 to 1.0)
        """
        self.volume = max(0.0, min(1.0, float(volume)))

    def get_active_voices(self):
        """Get the number of currently active voices.

        Returns:
            int: Number of active voices
        """
        return len(self.voices)

    def stop_stream(self):
        """Stop and clean up the audio stream."""
        self.is_playing = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
                print("Audio stream stopped successfully")
            except Exception as e:
                print(f"Error stopping audio stream: {e}")
        self.voices.clear()

    def reset(self):
        """Reset the synthesizer to its default state."""
        self.voices.clear()
        self.volume = 0.5
        self.waveform_type = 'sine'
        self.effects_enabled = {k: False for k in self.effects_enabled}
        self.adsr_params = {
            'attack': 0.1,
            'decay': 0.1,
            'sustain': 0.7,
            'release': 0.2
        }
