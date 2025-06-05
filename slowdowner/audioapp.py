import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
# import numpy as np
# import librosa
import sounddevice as sd
from slowdowner.audio import load_audio, extract_audio_from_video, extract_time_window, slow_down_audio


class AudioSlowdownGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Slowdown Tool")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # Audio data
        self.audio_data = None
        self.sample_rate = None
        self.audio_duration = 0
        self.current_segment = None
        self.slowed_segment = None
        self.is_playing = False
        self.is_paused = False
        self.playback_thread = None
        self.current_loop = 0
        
        # Create the GUI
        self.create_widgets()
        
    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Audio Slowdown Tool", 
                               font=('Helvetica', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # File loading section
        file_frame = ttk.LabelFrame(main_frame, text="Audio File", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="📁 Load Audio", 
                  command=self.load_audio_file).grid(row=0, column=0, padx=(0, 10))
        
        self.file_label = ttk.Label(file_frame, text="No file loaded", 
                                   foreground='gray')
        self.file_label.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Time window section
        time_frame = ttk.LabelFrame(main_frame, text="Time Window", padding="10")
        time_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        time_frame.columnconfigure(1, weight=1)
        time_frame.columnconfigure(3, weight=1)
        
        ttk.Label(time_frame, text="Start Time (s):").grid(row=0, column=0, padx=(0, 5))
        self.start_time_var = tk.DoubleVar(value=0.0)
        self.start_entry = ttk.Entry(time_frame, textvariable=self.start_time_var, width=10)
        self.start_entry.grid(row=0, column=1, padx=(0, 20), sticky=(tk.W, tk.E))
        
        ttk.Label(time_frame, text="End Time (s):").grid(row=0, column=2, padx=(0, 5))
        self.end_time_var = tk.DoubleVar(value=5.0)
        self.end_entry = ttk.Entry(time_frame, textvariable=self.end_time_var, width=10)
        self.end_entry.grid(row=0, column=3, sticky=(tk.W, tk.E))
        
        # Time position slider
        slider_frame = ttk.Frame(time_frame)
        slider_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
        slider_frame.columnconfigure(0, weight=1)
        
        ttk.Label(slider_frame, text="Audio Position:").grid(row=0, column=0, sticky=tk.W)
        
        self.position_var = tk.DoubleVar()
        self.position_scale = ttk.Scale(slider_frame, from_=0, to=100, 
                                       variable=self.position_var, orient=tk.HORIZONTAL,
                                       command=self.on_position_change)
        self.position_scale.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.position_label = ttk.Label(slider_frame, text="0.0 / 0.0 s")
        self.position_label.grid(row=2, column=0, sticky=tk.W)
        
        # Playback controls section
        control_frame = ttk.LabelFrame(main_frame, text="Playback Controls", padding="10")
        control_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Speed control
        speed_frame = ttk.Frame(control_frame)
        speed_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        speed_frame.columnconfigure(1, weight=1)
        
        ttk.Label(speed_frame, text="Slowdown Factor:").grid(row=0, column=0, padx=(0, 10))
        self.speed_var = tk.DoubleVar(value=2.0)
        self.speed_entry = ttk.Entry(speed_frame, textvariable=self.speed_var, width=10)
        self.speed_entry.grid(row=0, column=1, sticky=tk.W)
        ttk.Label(speed_frame, text="(1.0 = normal speed, 2.0 = half speed)").grid(row=0, column=2, padx=(10, 0))
        
        # Loop control
        loop_frame = ttk.Frame(control_frame)
        loop_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        
        ttk.Label(loop_frame, text="Number of Loops:").grid(row=0, column=0, padx=(0, 10))
        self.loops_var = tk.IntVar(value=1)
        self.loops_entry = ttk.Entry(loop_frame, textvariable=self.loops_var, width=10)
        self.loops_entry.grid(row=0, column=1, sticky=tk.W)
        ttk.Label(loop_frame, text="(0 = infinite)").grid(row=0, column=2, padx=(10, 0))
        
        # Control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=(0, 10))
        
        self.play_button = ttk.Button(button_frame, text="▶️ Play", 
                                     command=self.play_audio, state='disabled')
        self.play_button.grid(row=0, column=0, padx=(0, 10))
        
        self.pause_button = ttk.Button(button_frame, text="⏸️ Pause", 
                                      command=self.pause_audio, state='disabled')
        self.pause_button.grid(row=0, column=1, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ Stop", 
                                     command=self.stop_audio, state='disabled')
        self.stop_button.grid(row=0, column=2)
        
        # Status section
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        self.status_label = ttk.Label(status_frame, text="Ready to load audio file")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, 
                                          maximum=100, length=300)
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Bind events
        self.start_time_var.trace('w', self.on_time_change)
        self.end_time_var.trace('w', self.on_time_change)
        
    def load_audio_file(self):
        """Load an audio or video file"""
        file_types = [
            ("Audio files", "*.wav *.mp3 *.flac *.aac *.ogg"),
            ("Video files", "*.mp4 *.mov *.avi *.mkv"),
            ("All files", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="Select Audio or Video File",
            filetypes=file_types
        )
        
        if file_path:
            try:
                self.status_label.config(text="Loading audio file...")
                self.root.update()
                
                # Load audio
                if file_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                    self.audio_data, self.sample_rate = extract_audio_from_video(file_path)
                else:
                    self.audio_data, self.sample_rate = load_audio(file_path)
                
                self.audio_duration = len(self.audio_data) / self.sample_rate
                
                # Update UI
                filename = os.path.basename(file_path)
                self.file_label.config(text=f"{filename} ({self.audio_duration:.1f}s)", 
                                     foreground='black')
                
                # Update time controls
                self.end_time_var.set(min(5.0, self.audio_duration))
                self.position_scale.config(to=self.audio_duration)
                self.update_position_label()
                
                # Enable controls
                self.play_button.config(state='normal')
                
                self.status_label.config(text=f"Audio loaded: {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load audio file:\n{str(e)}")
                self.status_label.config(text="Error loading file")
    
    def on_time_change(self, *args):
        """Handle time window changes"""
        if self.audio_data is not None:
            start_time = self.start_time_var.get()
            end_time = self.end_time_var.get()
            
            # Validate times
            if start_time < 0:
                self.start_time_var.set(0)
            elif start_time >= self.audio_duration:
                self.start_time_var.set(max(0, self.audio_duration - 1))
            
            if end_time <= start_time:
                self.end_time_var.set(start_time + 1)
            elif end_time > self.audio_duration:
                self.end_time_var.set(self.audio_duration)
    
    def on_position_change(self, value):
        """Handle position slider changes"""
        if self.audio_data is not None:
            position = float(value)
            self.start_time_var.set(position)
            self.update_position_label()
    
    def update_position_label(self):
        """Update the position label"""
        if self.audio_data is not None:
            current_pos = self.position_var.get()
            self.position_label.config(text=f"{current_pos:.1f} / {self.audio_duration:.1f} s")
    
    def prepare_audio_segment(self):
        """Prepare the audio segment for playback"""
        if self.audio_data is None:
            return False
        
        try:
            start_time = self.start_time_var.get()
            end_time = self.end_time_var.get()
            slowdown_factor = self.speed_var.get()
            
            # Extract time window
            self.current_segment = extract_time_window(
                self.audio_data, self.sample_rate, start_time, end_time
            )
            
            # Apply slowdown
            if slowdown_factor != 1.0:
                self.slowed_segment = slow_down_audio(self.current_segment, slowdown_factor)
            else:
                self.slowed_segment = self.current_segment
            
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to prepare audio:\n{str(e)}")
            return False
    
    def play_audio(self):
        """Start audio playback"""
        if not self.prepare_audio_segment():
            return
        
        if self.is_paused:
            # Resume playback
            self.is_paused = False
            self.status_label.config(text="Resuming playback...")
        else:
            # Start new playback
            self.is_playing = True
            self.current_loop = 0
            
            # Update UI
            self.play_button.config(state='disabled')
            self.pause_button.config(state='normal')
            self.stop_button.config(state='normal')
            
            # Start playback thread
            self.playback_thread = threading.Thread(target=self.playback_loop, daemon=True)
            self.playback_thread.start()
    
    def pause_audio(self):
        """Pause audio playback"""
        self.is_paused = True
        sd.stop()
        
        # Update UI
        self.play_button.config(state='normal')
        self.pause_button.config(state='disabled')
        self.status_label.config(text="Playback paused")
    
    def stop_audio(self):
        """Stop audio playback"""
        self.is_playing = False
        self.is_paused = False
        sd.stop()
        
        # Update UI
        self.play_button.config(state='normal')
        self.pause_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.progress_var.set(0)
        self.status_label.config(text="Playback stopped")
    
    def playback_loop(self):
        """Main playback loop running in separate thread"""
        max_loops = self.loops_var.get()
        infinite_loop = (max_loops == 0)
        
        try:
            while self.is_playing and (infinite_loop or self.current_loop < max_loops):
                if not self.is_paused:
                    self.current_loop += 1
                    
                    # Update status
                    if infinite_loop:
                        status_text = f"Playing loop {self.current_loop} (infinite)"
                    else:
                        status_text = f"Playing loop {self.current_loop} of {max_loops}"
                        progress = (self.current_loop / max_loops) * 100
                        self.progress_var.set(progress)
                    
                    self.status_label.config(text=status_text)
                    
                    # Play audio
                    sd.play(self.slowed_segment, self.sample_rate)
                    sd.wait()
                    
                    # Small delay between loops
                    if self.is_playing:
                        threading.Event().wait(0.1)
                else:
                    # Wait while paused
                    threading.Event().wait(0.1)
            
            # Playback finished
            if self.is_playing:
                self.root.after(0, self.stop_audio)
                self.root.after(0, lambda: self.status_label.config(text="Playback completed"))
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Playback Error", str(e)))
            self.root.after(0, self.stop_audio)


def start_app():
    root = tk.Tk()
    app = AudioSlowdownGUI(root)
    root.mainloop()