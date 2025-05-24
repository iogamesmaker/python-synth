import tkinter as tk
from typing import Callable
from src.audio_engine.music_theory import NoteManager

class PianoKey(tk.Canvas):
    """A custom widget for piano keys with better visuals"""
    def __init__(self, parent, is_black=False, **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.is_black = is_black
        self.is_pressed = False
        self.bind('<Button-1>', self.on_press)
        self.bind('<ButtonRelease-1>', self.on_release)
        self.bind('<Enter>', self.on_hover)
        self.bind('<Leave>', self.on_leave)
        self.draw()

    def draw(self):
        self.delete('all')  # Clear canvas
        if self.is_black:
            # Black key with gradient
            self.create_rectangle(
                2, 2,
                self.winfo_width()-2, self.winfo_height()-2,
                fill='#111111' if self.is_pressed else 'black',
                outline='#333333',
                width=1
            )
            if not self.is_pressed:
                # Add glossy effect
                self.create_rectangle(
                    4, 4,
                    self.winfo_width()/2, self.winfo_height()-4,
                    fill='#333333',
                    outline='#333333'
                )
        else:
            # White key with gradient and shadow
            self.create_rectangle(
                2, 2,
                self.winfo_width()-2, self.winfo_height()-2,
                fill='#EEEEEE' if self.is_pressed else 'white',
                outline='#CCCCCC',
                width=1
            )
            if not self.is_pressed:
                # Add glossy effect
                self.create_rectangle(
                    4, 4,
                    self.winfo_width()/3, self.winfo_height()-4,
                    fill='white',
                    outline='',
                    stipple='gray50'
                )

    def on_press(self, event):
        self.is_pressed = True
        self.draw()
        self.event_generate('<<KeyPressed>>')

    def on_release(self, event):
        self.is_pressed = False
        self.draw()
        self.event_generate('<<KeyReleased>>')

    def on_hover(self, event):
        if not self.is_pressed:
            self.configure(cursor='hand2')
            if self.is_black:
                self.create_rectangle(
                    2, 2, self.winfo_width()-2, self.winfo_height()-2,
                    fill='#333333',
                    outline='#444444',
                    width=1
                )
            else:
                self.create_rectangle(
                    2, 2, self.winfo_width()-2, self.winfo_height()-2,
                    fill='#F8F8F8',
                    outline='#DDDDDD',
                    width=1
                )

    def on_leave(self, event):
        if not self.is_pressed:
            self.configure(cursor='')
            self.draw()

class PianoKeyboard(tk.Frame):
    def __init__(self, parent, play_callback):
        super().__init__(parent)
        self.play_callback = play_callback
        self.note_manager = NoteManager()
        self.keys = {}
        self.pressed_keys = set()

        # Configure frame
        self.configure(bg='#2C3E50', width=150)  # Fixed width for vertical keyboard
        self.pack_propagate(False)

        # Create keyboard container
        self.keyboard_frame = tk.Frame(self, bg='#2C3E50', width=150)
        self.keyboard_frame.pack(fill='both', expand=True)

        # Create piano keys
        self.create_keyboard()

        # Bind computer keyboard events
        self.bind_all('<KeyPress>', self.on_key_press)
        self.bind_all('<KeyRelease>', self.on_key_release)

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
        white_notes = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
        black_notes = ['C#', 'D#', 'F#', 'G#', 'A#']
        key_height = 40  # Height of white keys

        # Create two octaves (from bottom to top)
        for octave in [4, 5]:
            # Create white keys
            for i, note in enumerate(reversed(white_notes)):  # Reverse for bottom-to-top
                note_name = f"{note}{octave}"
                key = PianoKey(
                    self.keyboard_frame,
                    is_black=False,
                    width=120,
                    height=key_height
                )
                key.place(x=0, y=(13-i-7*octave)*key_height)  # Position from bottom

                freq = self.note_manager.get_frequency(note_name)
                key.bind('<<KeyPressed>>',
                        lambda e, f=freq: self.play_callback(f, True))
                key.bind('<<KeyReleased>>',
                        lambda e, f=freq: self.play_callback(f, False))

                self.keys[note_name] = key

            # Create black keys
            black_positions = [1, 2, 4, 5, 6]  # Relative to white keys
            for i, note in enumerate(reversed(black_notes)):  # Reverse for bottom-to-top
                note_name = f"{note}{octave}"
                key = PianoKey(
                    self.keyboard_frame,
                    is_black=True,
                    width=80,
                    height=key_height * 0.6
                )
                y_pos = (13-black_positions[i]-7*octave)*key_height + key_height*0.2
                key.place(x=0, y=y_pos)

                freq = self.note_manager.get_frequency(note_name)
                key.bind('<<KeyPressed>>',
                        lambda e, f=freq: self.play_callback(f, True))
                key.bind('<<KeyReleased>>',
                        lambda e, f=freq: self.play_callback(f, False))

                self.keys[note_name] = key

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
        if event.keysym.lower() not in self.pressed_keys:
            note = self.note_manager.get_note_from_key(event.keysym)
            if note and note in self.keys:
                self.pressed_keys.add(event.keysym.lower())
                self.keys[note].is_pressed = True
                self.keys[note].draw()
                freq = self.note_manager.get_frequency(note)
                self.play_callback(freq, True)

    def on_key_release(self, event):
        note = self.note_manager.get_note_from_key(event.keysym)
        if note and note in self.keys:
            self.pressed_keys.discard(event.keysym.lower())
            self.keys[note].is_pressed = False
            self.keys[note].draw()
            freq = self.note_manager.get_frequency(note)
            self.play_callback(freq, False)
