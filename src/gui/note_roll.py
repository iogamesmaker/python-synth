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
    def __init__(self, name, color=None):
        self.name = name
        self.color = color if color else self._generate_color_from_name(name)
        self.notes = []
        self.visible = True
        self.muted = False
        self.solo = False

    def _generate_color_from_name(self, name):
        """Generate a deterministic color based on the group name."""
        # Get hash of the name
        name_hash = hash(name)

        # Convert hash to positive number and get last 6 digits for RGB
        positive_hash = abs(name_hash)
        hex_hash = positive_hash % 0xFFFFFF

        # Extract RGB components
        r = (hex_hash & 0xFF0000) >> 16
        g = (hex_hash & 0x00FF00) >> 8
        b = hex_hash & 0x0000FF

        # Ensure good contrast and vibrance
        # Adjust brightness to be between 0.4 and 0.8 of max value
        def adjust_component(c):
            return int(102 + (c * 102 / 255))  # Maps 0-255 to 102-204

        r = adjust_component(r)
        g = adjust_component(g)
        b = adjust_component(b)

        # Convert to hex color string
        return f'#{r:02x}{g:02x}{b:02x}'

    def set_name(self, new_name):
        """Update the name and regenerate the color."""
        self.name = new_name
        if not self.color:  # Only regenerate if color wasn't explicitly set
            self.color = self._generate_color_from_name(new_name)

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

        # Create timeline canvas first
        self.timeline = tk.Canvas(
            self,
            height=30,
            bg='#2C3E50',
            highlightthickness=0
        )
        self.timeline.pack(side='top', fill='x')

        # Create main canvas
        self.canvas = tk.Canvas(
            self,
            bg='#1E1E1E',
            highlightthickness=0
        )
        self.canvas.pack(side='left', fill='both', expand=True)

        # Create scrollbars
        self.v_scrollbar = ttk.Scrollbar(self, orient='vertical')
        self.v_scrollbar.pack(side='right', fill='y')

        self.h_scrollbar = ttk.Scrollbar(self, orient='horizontal')
        self.h_scrollbar.pack(side='bottom', fill='x')

        # Configure scrolling
        self.canvas.configure(
            xscrollcommand=self.h_scrollbar.set,
            yscrollcommand=self.v_scrollbar.set
        )
        self.timeline.configure(xscrollcommand=self.h_scrollbar.set)

        self.v_scrollbar.configure(command=self.canvas.yview)
        self.h_scrollbar.configure(command=self.on_horizontal_scroll)

        # Bind events
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Button-3>', self.show_note_config)

        # Initialize group counter
        self.group_counter = 1

        # Initialize first group
        self.create_default_group()

        # Initial draw
        self.redraw()

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
        """Create a default note group with an automatically generated name."""
        group_name = f"Group {self.group_counter}"
        self.group_counter += 1
        group = NoteGroup(group_name)  # Color will be generated from name
        self.groups.append(group)
        self.current_group = group

    def create_new_group(self, name=None):
        """Create a new group with optional custom name."""
        if name is None:
            name = f"Group {self.group_counter}"
        self.group_counter += 1

        group = NoteGroup(name)
        self.groups.append(group)
        self.current_group = group
        return group

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
        """Zoom in the grid view."""
        self.grid_size = min(64, int(self.grid_size * 1.2))
        self.redraw()

    def zoom_out(self):
        """Zoom out the grid view."""
        self.grid_size = max(16, int(self.grid_size / 1.2))
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

    def on_drag(self, event):
        """Handle note duration adjustment"""
        if self.selected_note:
            x = self.canvas.canvasx(event.x)
            time_pos = (x / self.grid_size) * self.time_scale
            duration = max(self.time_scale, time_pos - self.selected_note.start_time)
            self.selected_note.duration = duration
            self.redraw()

    def on_release(self, event):
        """Handle end of drag operation"""
        # Optional: Add any cleanup or finalization here
        pass


    def on_canvas_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        # Convert to time and frequency
        time_pos = (x / self.grid_size) * self.time_scale
        midi_note = 88 - int(y / self.grid_size)  # Convert y position to MIDI note
        freq = 440 * (2 ** ((midi_note - 69) / 12))  # Convert MIDI note to frequency

        note = Note(
            frequency=freq,
            start_time=time_pos,
            duration=self.time_scale  # Initial duration is one grid unit
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

    def on_horizontal_scroll(self, *args):
        """Synchronize horizontal scrolling between timeline and main canvas"""
        self.canvas.xview(*args)
        self.timeline.xview(*args)

    def redraw(self):
        self.canvas.delete('all')
        self.timeline.delete('all')

        # Calculate width based on notes or minimum width
        min_width = self.canvas.winfo_width()
        if any(group.notes for group in self.groups):
            max_time = max(
                (note.start_time + note.duration
                 for group in self.groups
                 for note in group.notes),
                default=4  # Default to 4 seconds if no notes
            )
            width = max(
                min_width,
                int((max_time / self.time_scale) * self.grid_size + 100)
            )
        else:
            width = max(min_width, 800)  # Minimum width of 800px

        height = 88 * self.grid_size  # 88 piano keys

        # Draw grid
        self._draw_grid(width, height)

        # Draw notes
        self._draw_notes(width, height)

        # Update scroll region
        self.canvas.configure(scrollregion=(0, 0, width, height))
        self.timeline.configure(scrollregion=(0, 0, width, 30))

    def _draw_grid(self, width, height):
        # Draw vertical grid lines
        for x in range(0, width, self.grid_size):
            is_major = (x // self.grid_size) % 4 == 0
            color = '#444444' if is_major else '#333333'

            self.canvas.create_line(
                x, 0, x, height,
                fill=color,
                width=1,
                dash=None if is_major else (1, 2)
            )

            if is_major:
                time = (x / self.grid_size) * self.time_scale
                self.timeline.create_text(
                    x, 15,
                    text=f"{time:.1f}s",
                    fill='white',
                    anchor='center'
                )

        # Draw horizontal grid lines
        for i in range(88):
            y = i * self.grid_size
            midi_note = 88 - i
            note_number = midi_note % 12
            is_black = note_number in [1, 3, 6, 8, 10]
            is_c = note_number == 0

            color = '#444444' if is_c else '#333333' if not is_black else '#222222'

            self.canvas.create_line(
                0, y, width, y,
                fill=color,
                width=1,
                dash=None if is_c else (1, 2)
            )

            if is_c:
                octave = (midi_note // 12) - 1
                self.canvas.create_text(
                    5, y + self.grid_size/2,
                    text=f"C{octave}",
                    fill='white',
                    anchor='w'
                )

    def _draw_notes(self, width, height):
        for group in self.groups:
            if group.visible:
                for note in group.notes:
                    x1 = int((note.start_time / self.time_scale) * self.grid_size)
                    x2 = int(((note.start_time + note.duration) / self.time_scale) * self.grid_size)

                    midi_note = int(round(12 * np.log2(note.frequency/440) + 69))
                    y = (88 - midi_note) * self.grid_size

                    # Draw note rectangle with group color
                    fill_color = '#666666' if group.muted else group.color
                    self.canvas.create_rectangle(
                        x1, y,
                        x2, y + self.grid_size - 1,
                        fill=fill_color,
                        outline='white' if note == self.selected_note else '#000000',
                        width=2 if note == self.selected_note else 1
                    )

                    # Add subtle gradient effect
                    if not group.muted:
                        highlight_y = y + 2
                        highlight_height = (self.grid_size - 4) // 2
                        self.canvas.create_rectangle(
                            x1 + 2, highlight_y,
                            x2 - 2, highlight_y + highlight_height,
                            fill=self._lighten_color(group.color),
                            outline='',
                            stipple='gray25'
                        )

    def _lighten_color(self, color):
        """Create a lighter version of a color for gradient effect."""
        # Convert hex to RGB
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)

        # Lighten by 20%
        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))

        return f'#{r:02x}{g:02x}{b:02x}'

    def update_roll(self):
        self.redraw()
        self.after(50, self.update_roll)
