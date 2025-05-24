class NoteManager:
    def __init__(self):
        # Define base frequencies for octave 4 (middle C to B)
        self.base_notes = {
            'C': 261.63,
            'C#': 277.18, 'Db': 277.18,
            'D': 293.66,
            'D#': 311.13, 'Eb': 311.13,
            'E': 329.63,
            'F': 349.23,
            'F#': 369.99, 'Gb': 369.99,
            'G': 392.00,
            'G#': 415.30, 'Ab': 415.30,
            'A': 440.00,
            'A#': 466.16, 'Bb': 466.16,
            'B': 493.88
        }

        # Generate full note-to-frequency mapping
        self.note_to_freq = {}
        self._generate_all_octaves()

        # Generate computer keyboard mapping (2 octaves)
        self.key_to_note = {
            'z': 'C4', 's': 'C#4', 'x': 'D4', 'd': 'D#4', 'c': 'E4', 'v': 'F4',
            'g': 'F#4', 'b': 'G4', 'h': 'G#4', 'n': 'A4', 'j': 'A#4', 'm': 'B4',
            'q': 'C5', '2': 'C#5', 'w': 'D5', '3': 'D#5', 'e': 'E5', 'r': 'F5',
            '5': 'F#5', 't': 'G5', '6': 'G#5', 'y': 'A5', '7': 'A#5', 'u': 'B5'
        }

    def _generate_all_octaves(self):
        """Generate frequencies for notes in octaves 0-8."""
        for octave in range(9):  # 0-8
            for note, freq in self.base_notes.items():
                # Calculate frequency for current octave
                # Formula: f = f0 * (2^n) where n is octaves from middle C
                octave_multiplier = 2 ** (octave - 4)  # relative to octave 4
                self.note_to_freq[f"{note}{octave}"] = freq * octave_multiplier

    def get_frequency(self, note):
        """Get frequency for a given note (e.g., 'A4', 'C#5')."""
        return self.note_to_freq.get(note)

    def get_note_from_key(self, key):
        """Get note name from computer keyboard key."""
        return self.key_to_note.get(key.lower())
