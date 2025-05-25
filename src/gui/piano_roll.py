import tkinter as tk
from tkinter import ttk
import numpy as np
from src.audio_engine.note_manager import NoteManager

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
        name_hash = hash(name)
        positive_hash = abs(name_hash)
        hex_hash = positive_hash % 0xFFFFFF

        r = (hex_hash & 0xFF0000) >> 16
        g = (hex_hash & 0x00FF00) >> 8
        b = hex_hash & 0x0000FF

        def adjust_component(c):
            return int(102 + (c * 102 / 255))

        r = adjust_component(r)
        g = adjust_component(g)
        b = adjust_component(b)

        return f'#{r:02x}{g:02x}{b:02x}'

class PianoKey(tk.Frame):
    """A piano key widget."""
    def __init__(self, parent, is_black=False, width=40, height=100):
        super().__init__(parent)
        self.configure(
            width=width,
            height=height,
            bg='black' if is_black else 'white',
            relief='solid',
            bd=1
        )

        # Make sure the frame doesn't resize
        self.pack_propagate(False)

        # Bind mouse events
        self.bind('<Button-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)

        # Track pressed state
        self.pressed = False
        self.is_black = is_black

    def _on_press(self, event):
        """Handle key press."""
        self.pressed = True
        self.configure(bg='#666666' if self.is_black else '#CCCCCC')
        self.event_generate('<<KeyPressed>>')

    def _on_release(self, event):
        """Handle key release."""
        self.pressed = False
        self.configure(bg='black' if self.is_black else 'white')
        self.event_generate('<<KeyReleased>>')

class PianoRoll(tk.Frame):
    def __init__(self, parent, synth):
        super().__init__(parent)
        self.synth = synth
        self.note_manager = NoteManager()
        self.groups = []
        self.grid_size = 32  # pixels per grid unit
        self.time_scale = 0.25  # seconds per grid unit
        self.scroll_pos = 0
        self.selected_note = None
        self.playing_position = 0
        self.is_playing = False
        self.current_group = None
        self.group_counter = 1

        # Add snapping settings
        self.snap_settings = {
            'enabled': True,
            'mode': 'grid',  # 'grid', 'triplet', 'free'
            'grid_division': 4,  # subdivisions per grid cell (4 = quarter notes)
            'magnetic_snap': True,  # snap to nearby notes
            'magnetic_threshold': 10,  # pixels
            'show_snap_lines': True,
        }

        # Create main container
        self.main_container = tk.Frame(self)
        self.main_container.pack(fill='both', expand=True)

        # Create control panel frame first
        self.control_panel = ttk.Frame(self.main_container)
        self.control_panel.pack(side='top', fill='x')

        # Setup the control panel (now contains all controls)
        self.setup_control_panel()

        # Create timeline at the top
        self.timeline = tk.Canvas(
            self.main_container,
            height=30,
            bg='#2C3E50',
            highlightthickness=0
        )
        self.timeline.pack(fill='x')

        # Create piano keyboard frame on the left
        self.piano_frame = tk.Frame(self.main_container, bg='#1E1E1E')
        self.piano_frame.pack(side='left', fill='y')

        # Create note roll canvas
        self.canvas = tk.Canvas(
            self.main_container,
            bg='#1E1E1E',
            highlightthickness=0
        )
        self.canvas.pack(side='left', fill='both', expand=True)

        # Create scrollbars
        self.v_scrollbar = ttk.Scrollbar(self.main_container, orient='vertical')
        self.v_scrollbar.pack(side='right', fill='y')

        self.h_scrollbar = ttk.Scrollbar(self, orient='horizontal')
        self.h_scrollbar.pack(side='bottom', fill='x')

        # Configure scrolling
        self.canvas.configure(
            xscrollcommand=self.h_scrollbar.set,
            yscrollcommand=self.v_scrollbar.set
        )
        self.timeline.configure(xscrollcommand=self.h_scrollbar.set)

        self.v_scrollbar.configure(command=self._on_vertical_scroll)
        self.h_scrollbar.configure(command=self._on_horizontal_scroll)

        # Create piano keys
        self.piano_keys = {}
        self.create_piano_keyboard()

        # Add state tracking for note manipulation
        self.dragging_note = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resize_mode = False
        self.selected_note = None
        self.last_click_time = 0
        self.active_notes = {}

        # Add pan and zoom state tracking
        self.panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.last_scroll_time = 0  # For handling scroll zoom acceleration

        # Bind additional controls
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        # Add right-click binding
        self.canvas.bind('<Button-3>', self.on_right_click)  # Right-click
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Button-2>', self.start_pan)
        self.canvas.bind('<ButtonRelease-2>', self.stop_pan)
        self.canvas.bind('<B2-Motion>', self.on_pan)
        self.canvas.bind('<MouseWheel>', self.on_mousewheel)  # Windows/macOS
        self.canvas.bind('<Button-4>', self.on_mousewheel)  # Linux scroll up
        self.canvas.bind('<Button-5>', self.on_mousewheel)  # Linux scroll down

        # Key bindings for note manipulation
        self.bind_all('<Control-z>', self.undo)
        self.bind_all('<Delete>', self.delete_selected_note)  # Delete key
        self.bind_all('<Control-y>', self.redo)
        self.bind_all('<Left>', self.move_selected_note_left)
        self.bind_all('<Right>', self.move_selected_note_right)
        self.bind_all('<Up>', self.move_selected_note_up)
        self.bind_all('<Down>', self.move_selected_note_down)
        self.bind_all('<Shift-Left>', self.adjust_note_duration)
        self.bind_all('<Shift-Right>', self.adjust_note_duration)

        # Initialize undo/redo stacks
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_steps = 50

        # Initialize first group
        self.create_default_group()

        # Initial draw
        self.redraw()

        # Start update loop
        self.update_roll()

    def setup_control_panel(self):
        """Set up the control panel with group, playback, and snap controls in a single row."""
        control_frame = ttk.Frame(self.control_panel)
        control_frame.pack(fill='x', padx=5, pady=2)

        # Group controls (left side)
        group_frame = ttk.LabelFrame(control_frame, text="Groups")
        group_frame.pack(side='left', padx=2)

        ttk.Button(group_frame, text="New Group",
                  command=self.create_new_group).pack(side='left', padx=2)
        self.group_list = ttk.Combobox(group_frame, state='readonly', width=15)
        self.group_list.pack(side='left', padx=2)
        self.group_list.bind('<<ComboboxSelected>>', self.on_group_selected)

        # Playback controls (center)
        playback_frame = ttk.LabelFrame(control_frame, text="Playback")
        playback_frame.pack(side='left', padx=2)

        ttk.Button(playback_frame, text="⏵", width=3,
                  command=self.toggle_playback).pack(side='left', padx=2)
        ttk.Button(playback_frame, text="⏹", width=3,
                  command=self.reset_playback).pack(side='left', padx=2)

        # Snap controls (right side)
        snap_frame = ttk.LabelFrame(control_frame, text="Snap Settings")
        snap_frame.pack(side='left', padx=2)

        # Snap enable toggle
        self.snap_enabled_var = tk.BooleanVar(value=self.snap_settings['enabled'])
        ttk.Checkbutton(snap_frame, text="Snap",
                       variable=self.snap_enabled_var,
                       command=self.toggle_snap).pack(side='left', padx=2)

        # Mode selector
        ttk.Label(snap_frame, text="Mode:").pack(side='left', padx=2)
        self.snap_mode = ttk.Combobox(
            snap_frame,
            values=['grid', 'triplet', 'free'],
            state='readonly',
            width=8
        )
        self.snap_mode.set(self.snap_settings['mode'])
        self.snap_mode.pack(side='left', padx=2)
        self.snap_mode.bind('<<ComboboxSelected>>', self.update_snap_mode)

        # Grid division
        ttk.Label(snap_frame, text="Division:").pack(side='left', padx=2)
        self.grid_div = ttk.Spinbox(
            snap_frame,
            from_=1,
            to=16,
            width=3,
            command=self.update_grid_division
        )
        self.grid_div.set(self.snap_settings['grid_division'])
        self.grid_div.pack(side='left', padx=2)

        # Magnetic snap
        self.magnetic_snap_var = tk.BooleanVar(value=self.snap_settings['magnetic_snap'])
        ttk.Checkbutton(snap_frame, text="Magnetic",
                       variable=self.magnetic_snap_var,
                       command=self.toggle_magnetic_snap).pack(side='left', padx=2)

        # Zoom controls (far right)
        zoom_frame = ttk.LabelFrame(control_frame, text="Zoom")
        zoom_frame.pack(side='left', padx=2)

        ttk.Button(zoom_frame, text="−", width=3,
                  command=self.zoom_out).pack(side='left', padx=2)
        ttk.Button(zoom_frame, text="+", width=3,
                  command=self.zoom_in).pack(side='left', padx=2)

    def create_piano_keyboard(self):
        """Create the piano keyboard that scales with the note roll."""
        for widget in self.piano_frame.winfo_children():
            widget.destroy()

        key_width = 40
        key_height = self.grid_size  # Match note height

        # Create 88 keys (standard piano range)
        for i in range(88):
            midi_note = 88 - i
            note_number = midi_note % 12
            is_black = note_number in [1, 3, 6, 8, 10]

            # Calculate frequency
            freq = 440 * (2 ** ((midi_note - 69) / 12))

            key = PianoKey(
                self.piano_frame,
                is_black=is_black,
                width=key_width,
                height=key_height
            )
            key.place(x=0, y=i * key_height)

            # Bind note playing events
            key.bind('<<KeyPressed>>', lambda e, f=freq: self.synth.play_note(f, True))
            key.bind('<<KeyReleased>>', lambda e, f=freq: self.synth.play_note(f, False))

            self.piano_keys[midi_note] = key

    def create_default_group(self):
        """Create a default note group."""
        group_name = f"Group {self.group_counter}"
        self.group_counter += 1
        group = NoteGroup(group_name)
        self.groups.append(group)
        self.current_group = group
        self.update_group_list()

    def create_new_group(self, name=None):
        """Create a new group with optional custom name."""
        if name is None:
            name = f"Group {self.group_counter}"
        self.group_counter += 1
        group = NoteGroup(name)
        self.groups.append(group)
        self.current_group = group
        self.update_group_list()
        return group

    def update_group_list(self):
        """Update the group selection dropdown."""
        names = [group.name for group in self.groups]
        self.group_list['values'] = names
        if self.current_group:
            self.group_list.set(self.current_group.name)

    def on_group_selected(self, event):
        """Handle group selection change."""
        selected = self.group_list.get()
        self.current_group = next(g for g in self.groups if g.name == selected)
        self.redraw()

    def _on_vertical_scroll(self, *args):
        """Handle vertical scrolling of both piano and canvas."""
        self.canvas.yview(*args)
        if args[0] == 'moveto':
            self.piano_frame.place_configure(y=-float(args[1]) * self.canvas.winfo_height())
        elif args[0] == 'scroll':
            delta = int(args[1]) * int(args[2])
            self.piano_frame.place_configure(y=self.piano_frame.winfo_y() - delta)

    def _on_horizontal_scroll(self, *args):
        """Synchronize horizontal scrolling between timeline and canvas."""
        self.canvas.xview(*args)
        self.timeline.xview(*args)

    def zoom_in(self, event=None):
        """Zoom in the grid view."""
        old_grid_size = self.grid_size
        self.grid_size = min(64, int(self.grid_size * 1.2))
        if old_grid_size != self.grid_size:
            self.create_piano_keyboard()
            self.redraw()

    def zoom_out(self, event=None):
        """Zoom out the grid view."""
        old_grid_size = self.grid_size
        self.grid_size = max(16, int(self.grid_size / 1.2))
        if old_grid_size != self.grid_size:
            self.create_piano_keyboard()
            self.redraw()

    def toggle_playback(self):
        """Toggle playback state."""
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_notes()

    def stop_all_notes(self):
        """Stop all currently playing notes."""
        for freq in self.active_notes:
            self.synth.play_note(freq, False)
        self.active_notes.clear()

    def reset_playback(self):
        """Reset playback position and stop all notes."""
        self.playing_position = 0
        self.stop_all_notes()
        self.is_playing = False
        self.redraw()

    def add_snap_controls(self):
        """Add snapping controls to the control panel."""
        snap_frame = ttk.LabelFrame(self.control_panel, text="Snap Settings")
        snap_frame.pack(side='left', padx=5)

        # Snap enable/disable
        self.snap_enabled_var = tk.BooleanVar(value=self.snap_settings['enabled'])
        snap_enabled = ttk.Checkbutton(
            snap_frame,
            text="Enable Snapping",
            variable=self.snap_enabled_var,
            command=self.toggle_snap
        )
        snap_enabled.pack(fill='x', padx=5, pady=2)

        # Snap mode selection
        mode_frame = ttk.Frame(snap_frame)
        mode_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(mode_frame, text="Mode:").pack(side='left')
        self.snap_mode = ttk.Combobox(
            mode_frame,
            values=['grid', 'triplet', 'free'],
            state='readonly',
            width=10
        )
        self.snap_mode.set(self.snap_settings['mode'])
        self.snap_mode.pack(side='left', padx=5)
        self.snap_mode.bind('<<ComboboxSelected>>', self.update_snap_mode)

        # Grid division
        div_frame = ttk.Frame(snap_frame)
        div_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(div_frame, text="Grid Division:").pack(side='left')
        self.grid_div = ttk.Spinbox(
            div_frame,
            from_=1,
            to=16,
            width=5,
            command=self.update_grid_division
        )
        self.grid_div.set(self.snap_settings['grid_division'])
        self.grid_div.pack(side='left', padx=5)

        # Magnetic snap
        self.magnetic_snap_var = tk.BooleanVar(value=self.snap_settings['magnetic_snap'])
        magnetic_snap = ttk.Checkbutton(
            snap_frame,
            text="Magnetic Snap",
            variable=self.magnetic_snap_var,
            command=self.toggle_magnetic_snap
        )
        magnetic_snap.pack(fill='x', padx=5, pady=2)

    def toggle_snap(self):
        """Toggle snapping on/off."""
        self.snap_settings['enabled'] = not self.snap_settings['enabled']

    def update_snap_mode(self, event=None):
        """Update the snapping mode."""
        self.snap_settings['mode'] = self.snap_mode.get()
        self.redraw()

    def update_grid_division(self):
        """Update the grid division value."""
        try:
            value = int(self.grid_div.get())
            self.snap_settings['grid_division'] = max(1, min(16, value))
            self.redraw()
        except ValueError:
            pass

    def toggle_magnetic_snap(self):
        """Toggle magnetic snapping to nearby notes."""
        self.snap_settings['magnetic_snap'] = not self.snap_settings['magnetic_snap']

    def get_snap_position(self, x, y):
        """Get the snapped position for x and y coordinates."""
        if not self.snap_settings['enabled']:
            return x, y

        # Convert coordinates to time and note values
        time_value = (x / self.grid_size) * self.time_scale
        midi_note = 88 - int(y / self.grid_size)

        # Handle different snap modes
        if self.snap_settings['mode'] == 'grid':
            # Snap to grid divisions
            division_time = self.time_scale / self.snap_settings['grid_division']
            snapped_time = round(time_value / division_time) * division_time
            snapped_x = int((snapped_time / self.time_scale) * self.grid_size)

        elif self.snap_settings['mode'] == 'triplet':
            # Snap to triplet divisions (divide grid into three parts)
            triplet_time = self.time_scale / 3
            snapped_time = round(time_value / triplet_time) * triplet_time
            snapped_x = int((snapped_time / self.time_scale) * self.grid_size)

        else:  # free mode
            snapped_x = x

        # Snap Y to exact semitone positions
        snapped_y = int(round(y / self.grid_size) * self.grid_size)

        # Apply magnetic snapping if enabled
        if self.snap_settings['magnetic_snap'] and self.dragging_note:
            threshold_pixels = self.snap_settings['magnetic_threshold']
            closest_snap = None
            min_distance = float('inf')

            for group in self.groups:
                for note in group.notes:
                    if note == self.dragging_note:
                        continue

                    # Get note edges in pixels
                    note_start_x = int((note.start_time / self.time_scale) * self.grid_size)
                    note_end_x = int(((note.start_time + note.duration) / self.time_scale) * self.grid_size)
                    note_y = int((88 - round(12 * np.log2(note.frequency/440) + 69)) * self.grid_size)

                    # Only check notes in the same row or adjacent rows
                    if abs(note_y - snapped_y) <= self.grid_size:
                        # Check start edge
                        if abs(note_start_x - snapped_x) < threshold_pixels:
                            dist = abs(note_start_x - snapped_x)
                            if dist < min_distance:
                                min_distance = dist
                                closest_snap = note_start_x

                        # Check end edge
                        if abs(note_end_x - snapped_x) < threshold_pixels:
                            dist = abs(note_end_x - snapped_x)
                            if dist < min_distance:
                                min_distance = dist
                                closest_snap = note_end_x

            if closest_snap is not None:
                snapped_x = closest_snap

        return snapped_x, snapped_y

    def adjust_note_duration(self, event):
        """Adjust note duration with Shift+Left/Right."""
        if not self.selected_note:
            return

        if event.keysym == 'Left':
            self.selected_note.duration = max(
                self.time_scale,
                self.selected_note.duration - self.time_scale
            )
        else:  # Right
            self.selected_note.duration += self.time_scale

        self.save_state()
        self.redraw()

    def play_notes(self):
        """Play notes at current position."""
        if not self.is_playing:
            return

        current_time = self.playing_position * self.time_scale
        next_time = (self.playing_position + 1) * self.time_scale

        # Stop notes that should end
        notes_to_stop = []
        for freq, note in self.active_notes.items():
            if note.start_time + note.duration <= current_time:
                self.synth.play_note(freq, False)
                notes_to_stop.append(freq)

        # Remove stopped notes from active notes
        for freq in notes_to_stop:
            del self.active_notes[freq]

        # Play new notes
        for group in self.groups:
            if group.visible and not group.muted:
                for note in group.notes:
                    # Check if note should start playing
                    if (note.start_time <= current_time < note.start_time + note.duration and
                        note.frequency not in self.active_notes):
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
                        self.active_notes[note.frequency] = note

        self.playing_position += 1
        self.redraw()
        self.after(int(self.time_scale * 1000), self.play_notes)

    def on_canvas_click(self, event):
        """Handle canvas click event."""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        # Get snapped position
        snapped_x, snapped_y = self.get_snap_position(x, y)
        time_pos = (snapped_x / self.grid_size) * self.time_scale
        midi_note = 88 - int(snapped_y / self.grid_size)

        # Check for double click
        current_time = event.time
        if current_time - self.last_click_time < 300:
            self.select_note_at(x, y)
            self.last_click_time = 0
            return
        self.last_click_time = current_time

        # Check if clicking on an existing note
        clicked_note = self.find_note_at(x, y)
        if clicked_note:
            self.dragging_note = clicked_note
            self.drag_start_x = snapped_x
            self.drag_start_y = snapped_y

            # Check for resize mode
            note_end_x = int(((clicked_note.start_time + clicked_note.duration) /
                        self.time_scale) * self.grid_size)
            self.resize_mode = abs(x - note_end_x) < 10
            self.selected_note = clicked_note
        else:
            # Create new note at snapped position
            if 0 <= midi_note <= 127:
                freq = 440 * (2 ** ((midi_note - 69) / 12))
                note = Note(
                    frequency=freq,
                    start_time=time_pos,
                    duration=self.time_scale,
                    velocity=1.0,
                    waveform='sine',
                    adsr={'attack': 0.1, 'decay': 0.1, 'sustain': 0.7, 'release': 0.2},
                    effects={
                        'tremolo': {'enabled': False, 'rate': 5, 'depth': 0.3},
                        'delay': {'enabled': False, 'time': 0.1, 'feedback': 0.3},
                        'reverb': {'enabled': False, 'size': 0.3}
                    }
                )

                if self.current_group is None:
                    self.create_default_group()

                self.current_group.notes.append(note)
                self.selected_note = note
                self.dragging_note = note
                self.resize_mode = True
                self.save_state()

        self.redraw()

    def on_drag(self, event):
        """Handle dragging of notes."""
        if not self.dragging_note:
            return

        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        # Get snapped position
        snapped_x, snapped_y = self.get_snap_position(x, y)

        if self.resize_mode:
            # Calculate new duration based on snapped position
            note_start_x = int((self.dragging_note.start_time / self.time_scale) * self.grid_size)
            new_duration = max(
                self.time_scale,
                ((snapped_x - note_start_x) / self.grid_size) * self.time_scale
            )
            self.dragging_note.duration = new_duration
        else:
            # Calculate movement delta
            dx = snapped_x - self.drag_start_x
            dy = snapped_y - self.drag_start_y

            # Update note position
            new_time = max(0, (snapped_x / self.grid_size) * self.time_scale)
            new_midi = 88 - int(snapped_y / self.grid_size)

            if 0 <= new_midi <= 127:  # Ensure valid MIDI note range
                self.dragging_note.start_time = new_time
                self.dragging_note.frequency = 440 * (2 ** ((new_midi - 69) / 12))

                # Update drag start position
                self.drag_start_x = snapped_x
                self.drag_start_y = snapped_y

        self.redraw()

    def save_state(self):
        """Save current state for undo."""
        # Create a snapshot of current notes
        state = []
        for group in self.groups:
            group_state = []
            for note in group.notes:
                group_state.append({
                    'frequency': note.frequency,
                    'start_time': note.start_time,
                    'duration': note.duration,
                    'velocity': note.velocity,
                    'waveform': note.waveform,
                    'adsr': note.adsr.copy(),
                    'effects': {k: v.copy() for k, v in note.effects.items()}
                })
            state.append(group_state)

        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def on_right_click(self, event):
        """Handle right-click context menu."""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        note = self.find_note_at(x, y)
        if note:
            self.selected_note = note
            self.show_note_context_menu(event)

    def start_pan(self, event):
        """Start panning with middle mouse button."""
        self.panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.canvas.config(cursor='fleur')  # Change cursor to hand/grab

    def on_pan(self, event):
        """Handle panning motion."""
        if not self.panning:
            return

        dx = self.pan_start_x - event.x
        dy = self.pan_start_y - event.y

        # Get current scroll positions
        x_view = self.canvas.xview()
        y_view = self.canvas.yview()

        # Calculate movement based on canvas size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Move view
        self.canvas.xview_moveto(x_view[0] + dx/canvas_width)
        self.canvas.yview_moveto(y_view[0] + dy/canvas_height)

        # Update start position
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def stop_pan(self, event):
        """Stop panning."""
        self.panning = False
        self.canvas.config(cursor='')  # Reset cursor

    def on_mousewheel(self, event):
        """Handle mousewheel for zooming and scrolling."""
        if event.state & 4:  # Control key is pressed (zoom)
            # Get current time to handle acceleration
            current_time = event.time
            if current_time - self.last_scroll_time < 50:  # 50ms threshold
                zoom_factor = 1.2  # Faster zoom when scrolling quickly
            else:
                zoom_factor = 1.1  # Normal zoom speed
            self.last_scroll_time = current_time

            # Get mouse position for zoom focus
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)

            # Determine zoom direction
            if event.delta > 0 or event.num == 4:  # Zoom in
                self.zoom_at_point(x, y, zoom_factor)
            else:  # Zoom out
                self.zoom_at_point(x, y, 1/zoom_factor)
        else:  # Normal scroll
            if event.state & 1:  # Shift is pressed (horizontal scroll)
                if event.delta > 0 or event.num == 4:
                    self.canvas.xview_scroll(-1, 'units')
                else:
                    self.canvas.xview_scroll(1, 'units')
            else:  # Vertical scroll
                if event.delta > 0 or event.num == 4:
                    self.canvas.yview_scroll(-1, 'units')
                else:
                    self.canvas.yview_scroll(1, 'units')

    def zoom_at_point(self, x, y, factor):
        """Zoom centered on a specific point."""
        # Store old grid size
        old_grid_size = self.grid_size

        # Calculate new grid size (ensure integer values)
        new_grid_size = int(min(64, max(16, self.grid_size * factor)))

        if new_grid_size != old_grid_size:
            # Calculate zoom center in grid coordinates
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            # Convert viewport coordinates to canvas coordinates
            canvas_x = x + self.canvas.canvasx(0)
            canvas_y = y + self.canvas.canvasy(0)

            # Calculate the scaling factors
            scale_x = new_grid_size / old_grid_size
            scale_y = new_grid_size / old_grid_size

            # Update grid size
            self.grid_size = new_grid_size

            # Update piano keyboard
            self.create_piano_keyboard()

            # Calculate new scroll position
            new_x = canvas_x * scale_x - x
            new_y = canvas_y * scale_y - y

            # Update scroll position
            self.canvas.xview_moveto(new_x / (canvas_width * scale_x))
            self.canvas.yview_moveto(new_y / (canvas_height * scale_y))

            self.redraw()

    def move_selected_note(self, dx=0, dy=0):
        """Move selected note by grid units."""
        if self.selected_note:
            # Calculate time and pitch changes
            time_delta = dx * self.time_scale
            new_time = max(0, self.selected_note.start_time + time_delta)

            # Calculate new frequency from semitone change
            if dy != 0:
                midi_note = round(12 * np.log2(self.selected_note.frequency/440) + 69)
                new_midi = midi_note + dy
                new_freq = 440 * (2 ** ((new_midi - 69) / 12))
                self.selected_note.frequency = new_freq

            self.selected_note.start_time = new_time
            self.save_state()  # Save for undo
            self.redraw()

    def move_selected_note_left(self, event):
        """Move selected note left one grid unit."""
        self.move_selected_note(dx=-1)

    def move_selected_note_right(self, event):
        """Move selected note right one grid unit."""
        self.move_selected_note(dx=1)

    def move_selected_note_up(self, event):
        """Move selected note up one semitone."""
        self.move_selected_note(dy=1)

    def move_selected_note_down(self, event):
        """Move selected note down one semitone."""
        self.move_selected_note(dy=-1)

    def on_release(self, event):
        """Handle end of drag operation."""
        self.dragging_note = None
        self.resize_mode = False
        # Stop any notes that were being played
        self.stop_all_notes()

    def select_note_at(self, x, y):
        """Select a note at the given position."""
        note = self.find_note_at(x, y)
        if note:
            self.selected_note = note
            self.redraw()

    def undo(self, event=None):
        """Undo last action."""
        if not self.undo_stack:
            return

        # Save current state to redo stack
        current_state = []
        for group in self.groups:
            group_state = []
            for note in group.notes:
                group_state.append({
                    'frequency': note.frequency,
                    'start_time': note.start_time,
                    'duration': note.duration,
                    'velocity': note.velocity,
                    'waveform': note.waveform,
                    'adsr': note.adsr.copy(),
                    'effects': {k: v.copy() for k, v in note.effects.items()}
                })
            current_state.append(group_state)
        self.redo_stack.append(current_state)

        # Restore previous state
        state = self.undo_stack.pop()
        self.restore_state(state)

    def redo(self, event=None):
        """Redo last undone action."""
        if not self.redo_stack:
            return

        # Save current state to undo stack
        current_state = []
        for group in self.groups:
            group_state = []
            for note in group.notes:
                group_state.append({
                    'frequency': note.frequency,
                    'start_time': note.start_time,
                    'duration': note.duration,
                    'velocity': note.velocity,
                    'waveform': note.waveform,
                    'adsr': note.adsr.copy(),
                    'effects': {k: v.copy() for k, v in note.effects.items()}
                })
            current_state.append(group_state)
        self.undo_stack.append(current_state)

        # Restore redo state
        state = self.redo_stack.pop()
        self.restore_state(state)

    def restore_state(self, state):
        """Restore piano roll to a saved state."""
        # Clear current notes
        for group in self.groups:
            group.notes.clear()

        # Restore notes from state
        for group_idx, group_state in enumerate(state):
            if group_idx >= len(self.groups):
                self.create_new_group()
            for note_data in group_state:
                note = Note(
                    frequency=note_data['frequency'],
                    start_time=note_data['start_time'],
                    duration=note_data['duration'],
                    velocity=note_data['velocity'],
                    waveform=note_data['waveform'],
                    adsr=note_data['adsr'],
                    effects=note_data['effects']
                )
                self.groups[group_idx].notes.append(note)

        self.redraw()

    def find_note_at(self, x, y):
        """Find a note at the given canvas coordinates."""
        time_pos = (x / self.grid_size) * self.time_scale
        midi_note = 88 - int(y / self.grid_size)

        # Add some tolerance for clicking
        time_tolerance = self.time_scale / 4  # 1/4 grid cell tolerance

        for group in self.groups:
            for note in group.notes:
                note_midi = round(12 * np.log2(note.frequency/440) + 69)
                note_start = note.start_time
                note_end = note.start_time + note.duration

                if (abs(note_midi - midi_note) <= 1 and  # Within one semitone
                    note_start - time_tolerance <= time_pos <= note_end + time_tolerance):
                    return note
        return None

    def delete_selected_note(self, event=None):
        """Delete the selected note."""
        if self.selected_note:
            for group in self.groups:
                if self.selected_note in group.notes:
                    group.notes.remove(self.selected_note)
                    self.selected_note = None
                    self.redraw()
                    break

    def show_note_context_menu(self, event):
        """Show context menu for note."""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Delete", command=self.delete_selected_note)
        menu.add_command(label="Properties", command=lambda: self.show_note_config(event))
        menu.post(event.x_root, event.y_root)

    def show_note_config(self, event):
        """Show note configuration dialog."""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        time_pos = (x // self.grid_size) * self.time_scale
        for note in self.current_group.notes:
            if (note.start_time <= time_pos and
                note.start_time + note.duration > time_pos):
                self.open_note_config_dialog(note)
                break

    def open_note_config_dialog(self, note):
        """Open dialog for configuring note parameters."""
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
        """Redraw the entire piano roll."""
        self.canvas.delete('all')
        self.timeline.delete('all')

        # Calculate dimensions
        min_width = self.canvas.winfo_width()
        if any(group.notes for group in self.groups):
            max_time = max(
                (note.start_time + note.duration
                for group in self.groups
                for note in group.notes),
                default=4
            )
            width = max(
                min_width,
                int((max_time / self.time_scale) * self.grid_size + self.grid_size * 4)
            )
        else:
            width = max(min_width, 800)

        height = 88 * self.grid_size  # 88 piano keys

        # Draw grid
        self._draw_grid(width, height)

        # Draw playback position line
        if self.is_playing:
            play_x = int((self.playing_position * self.time_scale / self.time_scale) * self.grid_size)
            self.canvas.create_line(
                play_x, 0, play_x, height,
                fill='#00FF00',
                width=2,
                dash=(4, 4)
            )

        # Draw notes with grid alignment
        subdivision = (self.snap_settings['grid_division']
                    if self.snap_settings['mode'] == 'grid'
                    else 3 if self.snap_settings['mode'] == 'triplet'
                    else 1)
        grid_unit = self.grid_size / subdivision

        for group in self.groups:
            if group.visible:
                for note in group.notes:
                    # Align note position to grid
                    x1 = int((note.start_time / self.time_scale) * self.grid_size + grid_unit/2)
                    x2 = int(((note.start_time + note.duration) / self.time_scale) * self.grid_size + grid_unit/2)

                    # Calculate y position from frequency with grid alignment
                    midi_note = round(12 * np.log2(note.frequency/440) + 69)
                    y = (88 - midi_note) * self.grid_size + self.grid_size/2

                    # Draw note rectangle
                    fill_color = '#666666' if group.muted else group.color
                    outline_color = 'white' if note == self.selected_note else '#000000'
                    outline_width = 2 if note == self.selected_note else 1

                    # Create note rectangle with rounded corners
                    self._create_rounded_rectangle(
                        x1, y - self.grid_size/2,  # Adjust y position for center alignment
                        x2, y + self.grid_size/2,  # Adjust y position for center alignment
                        fill=fill_color,
                        outline=outline_color,
                        width=outline_width,
                        radius=4
                    )

                    # Add gradient effect
                    if not group.muted:
                        highlight_y = y - self.grid_size/4  # Adjust for centered alignment
                        highlight_height = self.grid_size/2
                        self._create_rounded_rectangle(
                            x1 + 2, highlight_y,
                            x2 - 2, highlight_y + highlight_height,
                            fill=self._lighten_color(group.color),
                            outline='',
                            radius=2,
                            stipple='gray25'
                        )

    def _create_rounded_rectangle(self, x1, y1, x2, y2, radius=5, **kwargs):
        """Create a rounded rectangle on the canvas."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]

        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_grid(self, width, height):
        """Draw the grid lines and time markers."""
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
        """Draw all notes on the canvas."""
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
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)

        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))

        return f'#{r:02x}{g:02x}{b:02x}'

    def update_roll(self):
        """Update the piano roll display."""
        self.redraw()
        self.after(50, self.update_roll)
