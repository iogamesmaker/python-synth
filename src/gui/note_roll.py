import tkinter as tk
from tkinter import ttk
import json
import time
import numpy as np

class Note:
    def __init__(self, frequency, start_time, duration, velocity=1.0,
                 waveform='sine', adsr=None, effects=None):
        self.frequency = frequency
        self.start_time = start_time
        self.duration = duration
        self.velocity = velocity
        self.waveform = waveform
        self.adsr = adsr or {'attack': 0.1, 'decay': 0.1, 'sustain': 0.7, 'release': 0.2}
        self.effects = effects or {
            'tremolo': {'enabled': False, 'rate': 5, 'depth': 0.3},
            'delay': {'enabled': False, 'time': 0.1, 'feedback': 0.3},
            'reverb': {'enabled': False, 'size': 0.3}
        }

class NoteGroup:
    def __init__(self, name="Group"):
        self.name = name
        self.notes = []
        self.color = "#" + "".join([hex(x)[2:].zfill(2) for x in
                                   [hash(name) % 256, (hash(name) * 2) % 256, (hash(name) * 3) % 256]])
        self.visible = True
        self.muted = False

class NoteRoll(tk.Frame):
    def __init__(self, parent, synth):
        super().__init__(parent)
        self.synth = synth
        self.groups = []
        self.grid_size = 32  # pixels per grid unit
        self.time_scale = 0.25  # seconds per grid unit
        self.scroll_pos = 0
        self.selected_note = None
        self.playing_position = 0
        self.is_playing = False
        self.current_group = None

        self.setup_ui()
        self.create_default_group()

    def setup_ui(self):
        # Control panel
        control_panel = ttk.Frame(self)
        control_panel.pack(fill='x', padx=5, pady=5)

        # Group controls
        group_frame = ttk.LabelFrame(control_panel, text="Groups")
        group_frame.pack(side='left', padx=5)

        ttk.Button(group_frame, text="New Group",
                  command=self.create_new_group).pack(side='left', padx=2)

        self.group_list = ttk.Combobox(group_frame, state='readonly')
        self.group_list.pack(side='left', padx=2)
        self.group_list.bind('<<ComboboxSelected>>', self.on_group_selected)

        # Playback controls
        playback_frame = ttk.LabelFrame(control_panel, text="Playback")
        playback_frame.pack(side='left', padx=5)

        ttk.Button(playback_frame, text="Play/Stop",
                  command=self.toggle_playback).pack(side='left', padx=2)
        ttk.Button(playback_frame, text="Reset",
                  command=self.reset_playback).pack(side='left', padx=2)

        # Zoom controls
        zoom_frame = ttk.LabelFrame(control_panel, text="Zoom")
        zoom_frame.pack(side='left', padx=5)

        ttk.Button(zoom_frame, text="Zoom In",
                  command=self.zoom_in).pack(side='left', padx=2)
        ttk.Button(zoom_frame, text="Zoom Out",
                  command=self.zoom_out).pack(side='left', padx=2)

        # Note roll canvas
        self.canvas_frame = ttk.Frame(self)
        self.canvas_frame.pack(fill='both', expand=True)

        # Timeline
        self.timeline = tk.Canvas(self.canvas_frame, height=30,
                                bg='#2C3E50', highlightthickness=0)
        self.timeline.pack(fill='x')

        # Main canvas
        self.canvas = tk.Canvas(self.canvas_frame, bg='#1a1a1a',
                              highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        # Scrollbars
        self.x_scroll = ttk.Scrollbar(self.canvas_frame, orient='horizontal',
                                    command=self.scroll_horizontally)
        self.x_scroll.pack(fill='x')

        self.y_scroll = ttk.Scrollbar(self, orient='vertical',
                                    command=self.canvas.yview)
        self.y_scroll.pack(fill='y', side='right')

        # Canvas bindings
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self.canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_canvas_release)
        self.canvas.bind('<Button-3>', self.show_note_config)

        # Start update loop
        self.update_roll()

    def create_default_group(self):
        if not self.groups:  # Only create if no groups exist
            default_group = NoteGroup("Default")
            self.groups.append(default_group)
            self.current_group = default_group
            self.update_group_list()

    def create_new_group(self):
        name = f"Group {len(self.groups) + 1}"
        self.groups.append(NoteGroup(name))
        self.current_group = self.groups[-1]
        self.update_group_list()

    def update_group_list(self):
        names = [group.name for group in self.groups]
        self.group_list['values'] = names
        self.group_list.set(self.current_group.name)

    def on_group_selected(self, event):
        selected = self.group_list.get()
        self.current_group = next(g for g in self.groups if g.name == selected)
        self.redraw()

    def scroll_horizontally(self, *args):
        self.canvas.xview(*args)
        self.timeline.xview(*args)

    def zoom_in(self):
        self.grid_size = min(64, self.grid_size * 1.2)
        self.redraw()

    def zoom_out(self):
        self.grid_size = max(16, self.grid_size / 1.2)
        self.redraw()

    def toggle_playback(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_notes()

    def reset_playback(self):
        self.playing_position = 0
        self.is_playing = False
        self.redraw()

    def play_notes(self):
        if not self.is_playing:
            return

        current_time = self.playing_position * self.time_scale

        # Play notes at current position
        for group in self.groups:
            if group.visible and not group.muted:
                for note in group.notes:
                    if (note.start_time <= current_time and
                        note.start_time + note.duration > current_time):
                        # Configure synth with note settings
                        self.synth.set_waveform(note.waveform)
                        self.synth.set_adsr(**note.adsr)
                        for effect, params in note.effects.items():
                            self.synth.toggle_effect(effect, params['enabled'])
                            if params['enabled']:
                                for param, value in params.items():
                                    if param != 'enabled':
                                        self.synth.set_effect_param(
                                            f"{effect}_{param}", value)

                        # Play the note
                        self.synth.play_note(note.frequency, True, note.velocity)

        self.playing_position += 1
        self.redraw()
        self.after(int(self.time_scale * 1000), self.play_notes)

    def on_canvas_click(self, event):
        """Handle mouse click on canvas."""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        # Convert to time and frequency
        time_pos = (x // self.grid_size) * self.time_scale
        # Calculate MIDI note number (88 keys, starting from A0)
        midi_note = 88 - (y // self.grid_size)
        # Convert MIDI note to frequency (A4 = 69 = 440Hz)
        freq = 440 * (2 ** ((midi_note - 69) / 12))

        # Create new note with default duration
        note = Note(
            frequency=freq,
            start_time=time_pos,
            duration=self.time_scale,  # Initial duration is one grid unit
            velocity=1.0,
            waveform='sine'
        )

        if self.current_group is None:
            self.create_default_group()

        self.current_group.notes.append(note)
        self.selected_note = note
        self.redraw()

    def on_canvas_drag(self, event):
        if self.selected_note:
            x = self.canvas.canvasx(event.x)
            duration = max(self.time_scale,
                         ((x // self.grid_size) * self.time_scale) -
                         self.selected_note.start_time)
            self.selected_note.duration = duration
            self.redraw()

    def on_canvas_release(self, event):
        self.selected_note = None

    def show_note_config(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        # Find clicked note
        time_pos = (x // self.grid_size) * self.time_scale
        for note in self.current_group.notes:
            if (note.start_time <= time_pos and
                note.start_time + note.duration > time_pos):
                self.open_note_config_dialog(note)
                break

    def open_note_config_dialog(self, note):
        dialog = tk.Toplevel(self)
        dialog.title("Note Configuration")

        # Waveform selection
        ttk.Label(dialog, text="Waveform:").grid(row=0, column=0, padx=5, pady=5)
        waveform_var = tk.StringVar(value=note.waveform)
        ttk.Combobox(dialog, textvariable=waveform_var,
                    values=['sine', 'square', 'triangle', 'saw'],
                    state='readonly').grid(row=0, column=1, padx=5, pady=5)

        # ADSR controls
        adsr_frame = ttk.LabelFrame(dialog, text="ADSR")
        adsr_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        adsr_vars = {}
        for i, (param, value) in enumerate(note.adsr.items()):
            ttk.Label(adsr_frame, text=param.title()).grid(row=i, column=0, padx=5)
            var = tk.DoubleVar(value=value)
            adsr_vars[param] = var
            ttk.Scale(adsr_frame, from_=0.01, to=1.0, variable=var,
                     orient='horizontal').grid(row=i, column=1, padx=5)

        # Effects controls
        effects_frame = ttk.LabelFrame(dialog, text="Effects")
        effects_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        effect_vars = {}
        for i, (effect, params) in enumerate(note.effects.items()):
            frame = ttk.LabelFrame(effects_frame, text=effect.title())
            frame.grid(row=i, column=0, columnspan=2, padx=5, pady=5)

            effect_vars[effect] = {}

            # Enable/disable checkbox
            enabled_var = tk.BooleanVar(value=params['enabled'])
            effect_vars[effect]['enabled'] = enabled_var
            ttk.Checkbutton(frame, text="Enabled",
                           variable=enabled_var).grid(row=0, column=0, padx=5)

            # Effect parameters
            for j, (param, value) in enumerate(params.items()):
                if param != 'enabled':
                    ttk.Label(frame, text=param.title()).grid(row=j+1, column=0, padx=5)
                    var = tk.DoubleVar(value=value)
                    effect_vars[effect][param] = var
                    ttk.Scale(frame, from_=0.01, to=1.0, variable=var,
                             orient='horizontal').grid(row=j+1, column=1, padx=5)

        def apply_config():
            note.waveform = waveform_var.get()
            note.adsr = {k: v.get() for k, v in adsr_vars.items()}
            note.effects = {
                effect: {
                    param: var.get()
                    for param, var in params.items()
                }
                for effect, params in effect_vars.items()
            }
            dialog.destroy()
            self.redraw()

        ttk.Button(dialog, text="Apply", command=apply_config).grid(
            row=3, column=0, columnspan=2, pady=10)

    def redraw(self):
        self.canvas.delete('all')
        self.timeline.delete('all')

        # Calculate width based on notes or minimum width
        min_width = self.canvas.winfo_width()
        if any(group.notes for group in self.groups):
            max_time = max(
                note.start_time + note.duration
                for group in self.groups
                for note in group.notes
            )
            width = max(
                min_width,
                (max_time / self.time_scale) * self.grid_size + 100
            )
        else:
            width = min_width

        height = self.canvas.winfo_height()

        # Draw vertical grid lines
        for x in range(0, int(width), self.grid_size):
            self.canvas.create_line(
                x, 0, x, height,
                fill='#333333',
                width=1,
                dash=(1, 2) if (x // self.grid_size) % 4 != 0 else None
            )

            # Draw time markers
            time = (x / self.grid_size) * self.time_scale
            if (x // self.grid_size) % 4 == 0:  # Major time markers
                self.timeline.create_text(
                    x, 15,
                    text=f"{time:.1f}s",
                    fill='white',
                    anchor='center'
                )

        # Draw horizontal grid lines (notes)
        for i in range(88):  # 88 piano keys
            y = i * self.grid_size

            # Calculate note name and frequency
            midi_note = 88 - i  # MIDI note number (A0 = 21 to C8 = 108)
            if midi_note % 12 in [1, 3, 6, 8, 10]:  # Black keys
                color = '#222222'
            else:
                color = '#333333'

            self.canvas.create_line(
                0, y, width, y,
                fill=color,
                width=1,
                dash=(1, 2) if midi_note % 12 != 0 else None
            )

            # Draw note names for C notes
            if midi_note % 12 == 0:
                octave = (midi_note // 12) - 1
                self.canvas.create_text(
                    5, y + self.grid_size/2,
                    text=f"C{octave}",
                    fill='white',
                    anchor='w'
                )

        # Draw notes for each group
        for group in self.groups:
            if group.visible:
                for note in group.notes:
                    x1 = note.start_time / self.time_scale * self.grid_size
                    x2 = (note.start_time + note.duration) / self.time_scale * self.grid_size

                    # Calculate y position based on frequency
                    midi_note = int(round(12 * np.log2(note.frequency/440) + 49))
                    y = (88 - midi_note) * self.grid_size

                    # Draw note rectangle
                    self.canvas.create_rectangle(
                        x1, y,
                        x2, y + self.grid_size - 1,
                        fill=group.color if not group.muted else '#666666',
                        outline='white' if note == self.selected_note else 'black',
                        width=2 if note == self.selected_note else 1
                    )

                    # Draw note effects indicators
                    if any(params['enabled'] for params in note.effects.values()):
                        self.canvas.create_line(
                            x1 + 4, y + 4,
                            x1 + 12, y + 4,
                            fill='yellow',
                            width=2
                        )

        # Draw playback position
        if self.is_playing:
            x = self.playing_position * self.grid_size
            self.canvas.create_line(
                x, 0, x, height,
                fill='#FF0000',
                width=2
            )
            self.timeline.create_line(
                x, 0, x, 30,
                fill='#FF0000',
                width=2
            )

        # Update scrollregion
        self.canvas.configure(scrollregion=(0, 0, width, 88 * self.grid_size))
        self.timeline.configure(scrollregion=(0, 0, width, 30))

    def update_roll(self):
        self.redraw()
        self.after(50, self.update_roll)
