import tkinter as tk
from src.audio_engine.note_manager import NoteManager

class PianoKey(tk.Canvas):
    def __init__(self, parent, is_black=False, width=40, height=120):
        super().__init__(
            parent,
            width=width,
            height=height,
            highlightthickness=1,
            highlightbackground='#444444',
            bg='black' if is_black else 'white'
        )
        self.is_black = is_black
        self.is_pressed = False
        self.width = width
        self.height = height
        self.bind('<Button-1>', self.on_press)
        self.bind('<ButtonRelease-1>', self.on_release)
        self.bind('<Enter>', self.on_hover)
        self.bind('<Leave>', self.on_leave)
        self.draw()

    def draw(self):
        self.delete('all')

        # Determine colors based on state and type
        if self.is_black:
            fill_color = '#222222' if self.is_pressed else 'black'
            highlight_color = '#444444'
        else:
            fill_color = '#CCCCCC' if self.is_pressed else 'white'
            highlight_color = '#888888'

        # Draw main key rectangle
        self.create_rectangle(
            2, 2,
            self.width - 2,
            self.height - 2,
            fill=fill_color,
            outline=highlight_color,
            width=1
        )

        # Add shading effects for 3D look
        if not self.is_pressed:
            # Top highlight
            self.create_line(2, 2, self.width-2, 2, fill='white' if not self.is_black else '#444444')
            # Left highlight
            self.create_line(2, 2, 2, self.height-2, fill='white' if not self.is_black else '#444444')
            # Bottom shadow
            self.create_line(2, self.height-2, self.width-2, self.height-2, fill='#666666')
            # Right shadow
            self.create_line(self.width-2, 2, self.width-2, self.height-2, fill='#666666')

    def on_press(self, event=None):
        self.is_pressed = True
        self.draw()
        self.event_generate('<<KeyPressed>>')

    def on_release(self, event=None):
        self.is_pressed = False
        self.draw()
        self.event_generate('<<KeyReleased>>')

    def on_hover(self, event):
        if not self.is_pressed:
            self.configure(bg='#EEEEEE' if not self.is_black else '#333333')

    def on_leave(self, event):
        if not self.is_pressed:
            self.configure(bg='white' if not self.is_black else 'black')

class PianoKeyboard(tk.Frame):
    def __init__(self, parent, play_callback):
        super().__init__(parent)
        self.play_callback = play_callback
        self.note_manager = NoteManager()
        self.keys = {}
        self.pressed_keys = set()

        # Fixed dimensions for keyboard
        self.white_key_width = 40
        self.white_key_height = 140
        self.black_key_width = 24
        self.black_key_height = 90

        # Define key bindings for two octaves
        self.key_bindings = {
            # Lower octave
            'z': 'C4', 's': 'C#4', 'x': 'D4', 'd': 'D#4',
            'c': 'E4', 'v': 'F4', 'g': 'F#4', 'b': 'G4',
            'h': 'G#4', 'n': 'A4', 'j': 'A#4', 'm': 'B4',
            # Upper octave
            'q': 'C5', '2': 'C#5', 'w': 'D5', '3': 'D#5',
            'e': 'E5', 'r': 'F5', '5': 'F#5', 't': 'G5',
            '6': 'G#5', 'y': 'A5', '7': 'A#5', 'u': 'B5'
        }

        # Configure frame
        self.configure(
            bg='#1E1E1E',
            width=self.white_key_width * 7,
            height=self.white_key_height * 2
        )
        self.pack_propagate(False)

        # Create keyboard container
        self.keyboard_frame = tk.Frame(
            self,
            bg='#1E1E1E',
            width=self.white_key_width * 7,
            height=self.white_key_height * 2
        )
        self.keyboard_frame.pack(expand=True, fill='both')
        self.keyboard_frame.pack_propagate(False)

        # Create piano keys
        self.create_keyboard()

        # Bind keyboard events
        self.bind_all('<KeyPress>', self.on_key_press)
        self.bind_all('<KeyRelease>', self.on_key_release)
        self.bind_all('<space>', self.stop_all_notes)

    def create_octave_labels(self):
        label_frame = tk.Frame(self.keyboard_frame, bg='#2C3E50')
        label_frame.pack(fill='x', pady=(0, 5))

        for octave in [4, 5]:
            label = tk.Label(
                label_frame,
                text=f"Octave {octave}",
                font=('Helvetica', 10),
                fg='white',
                bg='#2C3E50'
            )
            label.pack(side='left', padx=20)

    def create_keyboard(self):
        # Notes in each octave
        white_notes = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
        black_notes = ['C#', 'D#', 'F#', 'G#', 'A#']
        black_positions = [0, 1, 3, 4, 5]  # Relative to white keys

        # Create two octaves
        for octave in range(4, 6):
            base_y = (octave - 4) * (self.white_key_height * 7)

            # Create white keys first
            for i, note in enumerate(white_notes):
                note_name = f"{note}{octave}"
                y = base_y + (i * self.white_key_height)

                key = PianoKey(
                    self.keyboard_frame,
                    is_black=False,
                    width=self.white_key_width,
                    height=self.white_key_height
                )
                key.place(x=0, y=y)

                freq = self.note_manager.get_frequency(note_name)
                key.bind('<<KeyPressed>>', lambda e, f=freq: self.play_callback(f, True))
                key.bind('<<KeyReleased>>', lambda e, f=freq: self.play_callback(f, False))

                self.keys[note_name] = key

            # Create black keys on top
            for i, (note, pos) in enumerate(zip(black_notes, black_positions)):
                note_name = f"{note}{octave}"
                y = base_y + (pos * self.white_key_height)

                # Adjust black key position to be slightly lower (0.5 keys down)
                adjusted_y = y + ((self.white_key_height - self.black_key_height) * 0.75)

                key = PianoKey(
                    self.keyboard_frame,
                    is_black=True,
                    width=self.black_key_width,
                    height=self.black_key_height
                )
                key.place(
                    x=self.white_key_width - (self.black_key_width // 2),
                    y=adjusted_y
                )

                freq = self.note_manager.get_frequency(note_name)
                key.bind('<<KeyPressed>>', lambda e, f=freq: self.play_callback(f, True))
                key.bind('<<KeyReleased>>', lambda e, f=freq: self.play_callback(f, False))

                self.keys[note_name] = key

    def stop_all_notes(self, event=None):
        """Stop all currently playing notes"""
        for note_name in self.keys:
            freq = self.note_manager.get_frequency(note_name)
            self.play_callback(freq, False)
            if note_name in self.keys:
                self.keys[note_name].is_pressed = False
                self.keys[note_name].draw()
        self.pressed_keys.clear()

    def create_legend(self):
        legend_frame = tk.Frame(self, bg='#2C3E50', pady=10)
        legend_frame.pack(fill='x')

        # Create legend title
        legend_title = tk.Label(
            legend_frame,
            text="Keyboard Mapping",
            font=('Helvetica', 12, 'bold'),
            fg='white',
            bg='#2C3E50'
        )
        legend_title.pack(pady=(0, 5))

        # Create legend content
        legend_text = (
            "Lower Octave: Z,X,C,V,B,N,M (white keys) | S,D,G,H,J (black keys)\n"
            "Upper Octave: Q,W,E,R,T,Y,U (white keys) | 2,3,5,6,7 (black keys)"
        )
        legend_content = tk.Label(
            legend_frame,
            text=legend_text,
            font=('Helvetica', 10),
            fg='white',
            bg='#2C3E50',
            justify='center'
        )
        legend_content.pack()

    def on_key_press(self, event):
        if event.keysym in self.key_bindings and event.keysym not in self.pressed_keys:
            self.pressed_keys.add(event.keysym)
            note_name = self.key_bindings[event.keysym]
            if note_name in self.keys:
                self.keys[note_name].on_press()

    def on_key_release(self, event):
        if event.keysym in self.key_bindings and event.keysym in self.pressed_keys:
            self.pressed_keys.remove(event.keysym)
            note_name = self.key_bindings[event.keysym]
            if note_name in self.keys:
                self.keys[note_name].on_release()
