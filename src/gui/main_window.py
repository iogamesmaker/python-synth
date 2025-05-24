import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import datetime
from pathlib import Path
from src.gui.keyboard import PianoKeyboard
from src.gui.note_roll import NoteRoll
from src.audio_engine.synthesizer import Synthesizer

class SynthesizerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Configure main window
        self.title("Python Synthesizer")
        self.geometry("1200x800")
        self.configure(bg='#2C3E50')

        # Initialize variables
        self.project_path = None
        self.project_modified = False
        self.is_playing = False
        self.is_recording = False

        # Initialize audio components
        self.synth = Synthesizer()
        self.synth.start_stream()

        # Create main container
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill='both', expand=True)

        # Create main paned window for note roll and keyboard
        self.main_paned = ttk.PanedWindow(self.main_frame, orient='vertical')
        self.main_paned.pack(fill='both', expand=True)

        # Create horizontal paned window for controls and note roll
        self.horizontal_paned = ttk.PanedWindow(self.main_paned, orient='horizontal')
        self.main_paned.add(self.horizontal_paned, weight=3)

        # Create note roll FIRST
        self.note_roll = NoteRoll(self.horizontal_paned, self.synth)
        self.horizontal_paned.add(self.note_roll, weight=3)

        # Create keyboard
        self.keyboard = PianoKeyboard(self.main_paned, self.play_note)
        self.main_paned.add(self.keyboard, weight=1)

        # Now create the rest of the UI
        self.create_menu()
        self.create_toolbar()
        self.create_control_panel()
        self.create_status_bar()

        # Set window minimum size
        self.minsize(1200, 800)

        # Bind events
        self.bind_events()

        # Start status update timer
        self.update_status()

    def create_menu(self):
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Project", command=self.new_project)
        file_menu.add_command(label="Open Project...", command=self.open_project)
        file_menu.add_command(label="Save", command=self.save_project)
        file_menu.add_command(label="Save As...", command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export Audio...", command=self.export_audio)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)

        # Edit menu
        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo)
        edit_menu.add_command(label="Redo", command=self.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Preferences...", command=self.show_preferences)

        # View menu
        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Zoom In", command=lambda: self.note_roll.zoom_in())
        view_menu.add_command(label="Zoom Out", command=lambda: self.note_roll.zoom_out())
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Show Control Panel",
                                command=self.toggle_control_panel)

        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self.show_documentation)
        help_menu.add_command(label="About", command=self.show_about)

    def create_toolbar(self):
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill='x', padx=5, pady=2)

        # Transport controls
        ttk.Button(toolbar, text="⏮", width=3,
                  command=self.reset_playback).pack(side='left', padx=2)
        ttk.Button(toolbar, text="⏯", width=3,
                  command=self.toggle_playback).pack(side='left', padx=2)
        ttk.Button(toolbar, text="⏹", width=3,
                  command=self.stop_playback).pack(side='left', padx=2)
        ttk.Button(toolbar, text="⏺", width=3,
                  command=self.toggle_recording).pack(side='left', padx=2)

        # Separator
        ttk.Separator(toolbar, orient='vertical').pack(side='left',
                                                     fill='y', padx=5, pady=2)

        # Time display
        self.time_display = ttk.Label(toolbar, text="00:00:00.000")
        self.time_display.pack(side='left', padx=5)

        # BPM control
        ttk.Label(toolbar, text="BPM:").pack(side='left', padx=5)
        self.bpm_var = tk.StringVar(value="120")
        ttk.Entry(toolbar, textvariable=self.bpm_var,
                 width=5).pack(side='left', padx=2)

        # Separator
        ttk.Separator(toolbar, orient='vertical').pack(side='left',
                                                     fill='y', padx=5, pady=2)

        # Master volume
        ttk.Label(toolbar, text="Master:").pack(side='left', padx=5)
        self.master_volume = ttk.Scale(toolbar, from_=0, to=100,
                                     orient='horizontal', length=100,
                                     command=self.update_master_volume)
        self.master_volume.set(50)
        self.master_volume.pack(side='left', padx=2)

    def create_control_panel(self):
        self.control_panel = ttk.Frame(self.horizontal_paned)
        self.horizontal_paned.add(self.control_panel, weight=1)

        # Synth controls
        synth_frame = ttk.LabelFrame(self.control_panel, text="Synthesizer")
        synth_frame.pack(fill='x', padx=5, pady=5)

        # Waveform selection
        ttk.Label(synth_frame, text="Waveform:").pack(padx=5, pady=2)
        self.waveform_var = tk.StringVar(value='sine')
        waveforms = ['sine', 'square', 'triangle', 'saw']
        for wf in waveforms:
            ttk.Radiobutton(synth_frame, text=wf.title(),
                          variable=self.waveform_var,
                          value=wf,
                          command=self.update_waveform).pack(padx=5, pady=1)

        # ADSR controls
        adsr_frame = ttk.LabelFrame(self.control_panel, text="ADSR Envelope")
        adsr_frame.pack(fill='x', padx=5, pady=5)

        self.adsr_vars = {}
        for param in ['Attack', 'Decay', 'Sustain', 'Release']:
            frame = ttk.Frame(adsr_frame)
            frame.pack(fill='x', padx=5, pady=2)

            ttk.Label(frame, text=param).pack(side='left')
            var = tk.DoubleVar(value=0.1)
            self.adsr_vars[param.lower()] = var

            scale = ttk.Scale(frame, from_=0.01, to=1.0,
                            variable=var,
                            command=self.update_adsr,
                            orient='horizontal')
            scale.pack(side='left', fill='x', expand=True, padx=5)

        # Effects frame
        effects_frame = ttk.LabelFrame(self.control_panel, text="Effects")
        effects_frame.pack(fill='x', padx=5, pady=5)

        # Effect controls
        self.effect_vars = {}

        # Tremolo
        tremolo_frame = ttk.LabelFrame(effects_frame, text="Tremolo")
        tremolo_frame.pack(fill='x', padx=5, pady=2)

        self.effect_vars['tremolo'] = {
            'enabled': tk.BooleanVar(value=False)
        }
        ttk.Checkbutton(tremolo_frame, text="Enable",
                       variable=self.effect_vars['tremolo']['enabled'],
                       command=lambda: self.toggle_effect('tremolo')).pack(padx=5, pady=2)

        for param in ['Rate', 'Depth']:
            frame = ttk.Frame(tremolo_frame)
            frame.pack(fill='x', padx=5, pady=2)

            ttk.Label(frame, text=param).pack(side='left')
            var = tk.DoubleVar(value=0.5)
            self.effect_vars['tremolo'][param.lower()] = var

            scale = ttk.Scale(frame, from_=0.01, to=1.0,
                            variable=var,
                            command=lambda v, p=param.lower():
                                self.update_effect_param('tremolo', p, v),
                            orient='horizontal')
            scale.pack(side='left', fill='x', expand=True, padx=5)

        # Save/Load Presets
        preset_frame = ttk.LabelFrame(self.control_panel, text="Presets")
        preset_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(preset_frame, text="Save Preset",
                  command=self.save_preset).pack(fill='x', padx=5, pady=2)
        ttk.Button(preset_frame, text="Load Preset",
                  command=self.load_preset).pack(fill='x', padx=5, pady=2)

    def create_status_bar(self):
        self.status_bar = ttk.Frame(self.main_frame)
        self.status_bar.pack(fill='x', side='bottom')

        # Project info
        self.project_label = ttk.Label(self.status_bar, text="No project loaded")
        self.project_label.pack(side='left', padx=5)

        # Separator
        ttk.Separator(self.status_bar, orient='vertical').pack(side='left',
                                                             fill='y', padx=5)

        # Audio info
        self.audio_label = ttk.Label(self.status_bar,
                                   text="44.1kHz | 32-bit float")
        self.audio_label.pack(side='left', padx=5)

        # CPU usage
        self.cpu_label = ttk.Label(self.status_bar, text="CPU: 0%")
        self.cpu_label.pack(side='right', padx=5)

        # Active voices
        self.voices_label = ttk.Label(self.status_bar, text="Voices: 0")
        self.voices_label.pack(side='right', padx=5)

    def bind_events(self):
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind('<Control-s>', lambda e: self.save_project())
        self.bind('<Control-o>', lambda e: self.open_project())
        self.bind('<Control-n>', lambda e: self.new_project())
        self.bind('<Control-z>', lambda e: self.undo())
        self.bind('<Control-y>', lambda e: self.redo())

    def update_status(self):
        # Update time display
        if self.note_roll.is_playing:
            time_pos = self.note_roll.playing_position * self.note_roll.time_scale
            self.time_display.config(
                text=f"{int(time_pos//60):02d}:{int(time_pos%60):02d}:"
                     f"{int((time_pos%1)*1000):03d}")

        # Update voice count
        voice_count = self.synth.get_active_voices()
        self.voices_label.config(text=f"Voices: {voice_count}")

        # Schedule next update
        self.after(50, self.update_status)

    def play_note(self, frequency, state):
        """Handle note events from the keyboard."""
        self.synth.play_note(frequency, state)

    def update_waveform(self):
        """Update synth waveform type."""
        self.synth.set_waveform(self.waveform_var.get())

    def update_adsr(self, _=None):
        """Update ADSR envelope parameters."""
        self.synth.set_adsr(
            self.adsr_vars['attack'].get(),
            self.adsr_vars['decay'].get(),
            self.adsr_vars['sustain'].get(),
            self.adsr_vars['release'].get()
        )

    def toggle_effect(self, effect):
        """Toggle effect on/off."""
        self.synth.toggle_effect(effect,
                               self.effect_vars[effect]['enabled'].get())

    def update_effect_param(self, effect, param, value):
        """Update effect parameters."""
        self.synth.set_effect_param(f"{effect}_{param}", float(value))

    def update_master_volume(self, value):
        """Update master volume."""
        self.synth.set_volume(float(value) / 100)

    def new_project(self):
        """Create a new project."""
        if self.project_modified:
            if not messagebox.askyesno("New Project",
                                     "Current project has unsaved changes. Continue?"):
                return

        self.project_path = None
        self.project_modified = False
        self.note_roll.reset()
        self.update_title()

    def open_project(self):
        """Open a project file."""
        if self.project_modified:
            if not messagebox.askyesno("Open Project",
                                     "Current project has unsaved changes. Continue?"):
                return

        filepath = filedialog.askopenfilename(
            defaultextension=".synth",
            filetypes=[("Synthesizer Project", "*.synth"), ("All Files", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                self.note_roll.load_from_data(data)
                self.project_path = filepath
                self.project_modified = False
                self.update_title()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open project: {e}")

    def save_project(self):
        """Save the current project."""
        if not self.project_path:
            return self.save_project_as()

        try:
            data = self.note_roll.save_to_data()
            with open(self.project_path, 'w') as f:
                json.dump(data, f)
            self.project_modified = False
            self.update_title()
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project: {e}")
            return False

    def save_project_as(self):
        """Save the project to a new file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".synth",
            filetypes=[("Synthesizer Project", "*.synth"), ("All Files", "*.*")]
        )

        if filepath:
            self.project_path = filepath
            return self.save_project()
        return False

    def export_audio(self):
        """Export the project as an audio file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("Wave Audio", "*.wav"), ("All Files", "*.*")]
        )

        if filepath:
            try:
                self.note_roll.export_audio(filepath)
                messagebox.showinfo("Export Complete",
                                  "Audio file exported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export audio: {e}")

    def save_preset(self):
        """Save current synth settings as a preset."""
        name = tk.simpledialog.askstring("Save Preset",
                                       "Enter preset name:")
        if name:
            preset = {
                'waveform': self.waveform_var.get(),
                'adsr': {k: v.get() for k, v in self.adsr_vars.items()},
                'effects': {k: {p: v.get() for p, v in params.items()}
                          for k, params in self.effect_vars.items()}
            }

            # Save to presets directory
            preset_dir = Path.home() / ".synth_presets"
            preset_dir.mkdir(exist_ok=True)

            with open(preset_dir / f"{name}.json", 'w') as f:
                json.dump(preset, f)

    def load_preset(self):
        """Load a saved preset."""
        preset_dir = Path.home() / ".synth_presets"
        if not preset_dir.exists():
            messagebox.showinfo("No Presets",
                              "No saved presets found.")
            return

        presets = list(preset_dir.glob("*.json"))
        if not presets:
            messagebox.showinfo("No Presets",
                              "No saved presets found.")
            return

        # Show preset selection dialog
        dialog = tk.Toplevel(self)
        dialog.title("Load Preset")
        dialog.transient(self)
        dialog.grab_set()

        listbox = tk.Listbox(dialog, width=40)
        listbox.pack(padx=5, pady=5)

        for preset in presets:
            listbox.insert(tk.END, preset.stem)

        def load_selected():
            selection = listbox.curselection()
            if selection:
                preset_path = presets[selection[0]]
                try:
                    with open(preset_path, 'r') as f:
                        preset = json.load(f)

                    # Apply preset
                    self.waveform_var.set(preset['waveform'])
                    self.update_waveform()

                    for k, v in preset['adsr'].items():
                        self.adsr_vars[k].set(v)
                    self.update_adsr()

                    for effect, params in preset['effects'].items():
                        for param, value in params.items():
                            self.effect_vars[effect][param].set(value)
                        self.toggle_effect(effect)

                    dialog.destroy()
                except Exception as e:
                    messagebox.showerror("Error",
                                       f"Failed to load preset: {e}")

        ttk.Button(dialog, text="Load",
                  command=load_selected).pack(pady=5)

    def show_preferences(self):
        """Show preferences dialog."""
        dialog = tk.Toplevel(self)
        dialog.title("Preferences")
        dialog.transient(self)
        dialog.grab_set()

        # Audio settings
        audio_frame = ttk.LabelFrame(dialog, text="Audio")
        audio_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(audio_frame, text="Sample Rate:").grid(row=0, column=0, padx=5, pady=2)
        sample_rate = ttk.Combobox(audio_frame, values=['44100', '48000', '96000'])
        sample_rate.set('44100')
        sample_rate.grid(row=0, column=1, padx=5, pady=2)

        # Interface settings
        ui_frame = ttk.LabelFrame(dialog, text="Interface")
        ui_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(ui_frame, text="Theme:").grid(row=0, column=0, padx=5, pady=2)
        theme = ttk.Combobox(ui_frame, values=['Dark', 'Light'])
        theme.set('Dark')
        theme.grid(row=0, column=1, padx=5, pady=2)

        ttk.Button(dialog, text="Apply",
                  command=dialog.destroy).pack(pady=5)

    def show_documentation(self):
        """Show documentation window."""
        dialog = tk.Toplevel(self)
        dialog.title("Documentation")
        dialog.geometry("600x400")

        text = tk.Text(dialog, wrap=tk.WORD, padx=5, pady=5)
        text.pack(fill='both', expand=True)

        # Load and display documentation
        text.insert('1.0', """Python Synthesizer Documentation

        Keyboard Controls:
        - Use computer keyboard or click piano keys to play notes
        - Use scroll wheel to zoom in/out
        - Use Ctrl+S to save project
        - Use Ctrl+O to open project
        - Use Ctrl+Z to undo
        - Use Ctrl+Y to redo

        Note Roll:
        - Click and drag to create notes
        - Right-click notes to edit properties
        - Use groups to organize notes
        - Play/Stop to hear your sequence

        Effects:
        - Enable/disable effects using checkboxes
        - Adjust effect parameters using sliders
        - Save your favorite settings as presets
        """)
        text.config(state='disabled')

    def show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About Python Synthesizer",
            "Python Synthesizer v1.0\n\n"
            "A feature-rich software synthesizer with piano roll editor.\n\n"
            "Created by: iogamesmaker\n"
            "Date: 2025-05-24"
        )

    def toggle_control_panel(self):
        """Toggle control panel visibility."""
        if self.control_panel.winfo_viewable():
            self.horizontal_paned.forget(self.control_panel)
        else:
            self.horizontal_paned.add(self.control_panel, weight=1)

    def reset_playback(self):
        """Reset playback position."""
        self.note_roll.reset_playback()
        self.is_playing = False

    def toggle_playback(self):
        """Toggle playback state."""
        self.is_playing = not self.is_playing
        self.note_roll.toggle_playback()

    def stop_playback(self):
        """Stop playback and reset position."""
        self.is_playing = False
        self.note_roll.reset_playback()

    def toggle_recording(self):
        """Toggle recording state."""
        self.is_recording = not self.is_recording
        # TODO: Implement recording functionality

    def update_title(self):
        """Update window title with project info."""
        title = "Python Synthesizer"
        if self.project_path:
            title += f" - {Path(self.project_path).name}"
        if self.project_modified:
            title += " *"
        self.title(title)

    def undo(self):
        """Undo last action."""
        # TODO: Implement undo functionality
        pass

    def redo(self):
        """Redo last undone action."""
        # TODO: Implement redo functionality
        pass

    def on_closing(self):
        """Handle window closing."""
        if self.project_modified:
            if messagebox.askyesno("Quit",
                                 "Current project has unsaved changes. Save before quitting?"):
                if not self.save_project():
                    return

        self.synth.stop_stream()
        self.destroy()

if __name__ == "__main__":
    app = SynthesizerApp()
    app.mainloop()
