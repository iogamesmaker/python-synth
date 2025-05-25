import numpy as np

class NoteManager:
    def __init__(self):
        # Note name to MIDI number mapping
        self.note_to_midi = {}
        self.midi_to_note = {}

        # Initialize note mappings
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        for octave in range(-1, 10):  # MIDI notes cover from C-1 to G9
            for i, note in enumerate(notes):
                midi_number = (octave + 1) * 12 + i
                note_name = f"{note}{octave}"
                self.note_to_midi[note_name] = midi_number
                self.midi_to_note[midi_number] = note_name

        # Computer keyboard to note mapping (2 octaves)
        self.key_to_note = {
            # Lower octave (Z-M)
            'z': 'C4',
            's': 'C#4',
            'x': 'D4',
            'd': 'D#4',
            'c': 'E4',
            'v': 'F4',
            'g': 'F#4',
            'b': 'G4',
            'h': 'G#4',
            'n': 'A4',
            'j': 'A#4',
            'm': 'B4',
            # Upper octave (Q-I)
            'q': 'C5',
            '2': 'C#5',
            'w': 'D5',
            '3': 'D#5',
            'e': 'E5',
            'r': 'F5',
            '5': 'F#5',
            't': 'G5',
            '6': 'G#5',
            'y': 'A5',
            '7': 'A#5',
            'u': 'B5'
        }

    def get_frequency(self, note_name):
        """Convert a note name (e.g., 'A4') to its frequency in Hz."""
        if note_name in self.note_to_midi:
            midi_number = self.note_to_midi[note_name]
            # A4 is MIDI note 69, frequency 440 Hz
            return 440.0 * (2.0 ** ((midi_number - 69) / 12.0))
        return None

    def get_note_from_frequency(self, frequency):
        """Convert a frequency to the closest note name."""
        # Calculate MIDI note number from frequency
        midi_number = int(round(12 * np.log2(frequency/440.0) + 69))
        return self.midi_to_note.get(midi_number)

    def get_note_from_key(self, key):
        """Get note name from computer keyboard key."""
        return self.key_to_note.get(key.lower())

    def get_midi_number(self, note_name):
        """Get MIDI note number from note name."""
        return self.note_to_midi.get(note_name)

    def get_note_name(self, midi_number):
        """Get note name from MIDI note number."""
        return self.midi_to_note.get(midi_number)

    def get_all_notes(self):
        """Get list of all note names."""
        return list(self.note_to_midi.keys())

    def get_octave_notes(self, octave):
        """Get all notes in a specific octave."""
        return [note for note in self.note_to_midi.keys() if note[-1] == str(octave)]

    def is_black_key(self, note_name):
        """Check if a note is a black key."""
        return '#' in note_name

    def get_note_position(self, note_name):
        """Get the position of a note within its octave (0-11)."""
        if note_name in self.note_to_midi:
            return self.note_to_midi[note_name] % 12
        return None

    def get_key_bindings(self):
        """Get the keyboard to note mappings."""
        return self.key_to_note.copy()

    def transpose_note(self, note_name, semitones):
        """Transpose a note by a number of semitones."""
        if note_name in self.note_to_midi:
            midi_number = self.note_to_midi[note_name] + semitones
            return self.midi_to_note.get(midi_number)
        return None
