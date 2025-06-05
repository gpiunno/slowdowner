import streamlit as st
import os
import numpy as np
import librosa
import sounddevice as sd
import threading
import time
from slowdowner.audio import load_audio, extract_audio_from_video, extract_time_window, slow_down_audio
import tempfile
import io


def initialize_session_state():
    """Initialize session state variables"""
    if 'audio_data' not in st.session_state:
        st.session_state.audio_data = None
    if 'sample_rate' not in st.session_state:
        st.session_state.sample_rate = None
    if 'audio_duration' not in st.session_state:
        st.session_state.audio_duration = 0
    if 'is_playing' not in st.session_state:
        st.session_state.is_playing = False
    if 'current_loop' not in st.session_state:
        st.session_state.current_loop = 0
    if 'playback_thread' not in st.session_state:
        st.session_state.playback_thread = None
    if 'processed_audio' not in st.session_state:
        st.session_state.processed_audio = None


def stop_playback():
    """Stop any ongoing playback"""
    st.session_state.is_playing = False
    try:
        sd.stop()
    except:
        pass


def play_audio_segment(audio_segment, sample_rate, num_loops):
    """Play audio segment in a separate thread"""
    try:
        for loop_num in range(1, num_loops + 1 if num_loops > 0 else float('inf')):
            if not st.session_state.is_playing:
                break
            
            st.session_state.current_loop = loop_num
            sd.play(audio_segment, sample_rate)
            sd.wait()
            
            # Small delay between loops
            time.sleep(0.1)
            
            # Break if finite loops
            if num_loops > 0 and loop_num >= num_loops:
                break
                
    except Exception as e:
        st.error(f"Playback error: {str(e)}")
    finally:
        st.session_state.is_playing = False


def main():
    st.set_page_config(
        page_title="Audio Slowdown Tool",
        page_icon="🎵",
        layout="wide"
    )
    
    initialize_session_state()
    
    # Header
    st.title("🎵 Audio Slowdown Tool")
    st.markdown("Load audio files, select time windows, and play them back at different speeds!")
    
    # Sidebar for controls
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # File upload
        st.subheader("📁 Load Audio File")
        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=['wav', 'mp3', 'flac', 'aac', 'ogg', 'mp4', 'mov', 'avi', 'mkv'],
            help="Upload audio or video files"
        )
        
        if uploaded_file is not None:
            try:
                with st.spinner("Loading audio file..."):
                    # Save uploaded file temporarily
                    with tempfile.NamedTemporaryFile(delete=False, 
                                                   suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_path = tmp_file.name
                    
                    # Load audio based on file type
                    if uploaded_file.name.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                        audio_data, sample_rate = extract_audio_from_video(tmp_path)
                    else:
                        audio_data, sample_rate = load_audio(tmp_path)
                    
                    # Clean up temp file
                    os.unlink(tmp_path)
                    
                    # Store in session state
                    st.session_state.audio_data = audio_data
                    st.session_state.sample_rate = sample_rate
                    st.session_state.audio_duration = len(audio_data) / sample_rate
                    
                    st.success(f"✅ Loaded: {uploaded_file.name}")
                    st.info(f"Duration: {st.session_state.audio_duration:.2f} seconds")
                    
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")
        
        # Audio controls (only show if audio is loaded)
        if st.session_state.audio_data is not None:
            st.subheader("⏰ Time Window")
            
            # Time inputs with validation
            col1, col2 = st.columns(2)
            with col1:
                start_time = st.number_input(
                    "Start (s)", 
                    min_value=0.0, 
                    max_value=max(0.0, st.session_state.audio_duration - 0.1),
                    value=0.0,
                    step=0.1,
                    format="%.1f"
                )
            
            with col2:
                end_time = st.number_input(
                    "End (s)", 
                    min_value=start_time + 0.1, 
                    max_value=st.session_state.audio_duration,
                    value=min(5.0, st.session_state.audio_duration),
                    step=0.1,
                    format="%.1f"
                )
            
            # Position slider
            st.write("**Audio Position**")
            position = st.slider(
                "Drag to set start position",
                min_value=0.0,
                max_value=max(0.0, st.session_state.audio_duration - 0.1),
                value=start_time,
                step=0.1,
                format="%.1f s"
            )
            
            # Update start time if slider moved
            if abs(position - start_time) > 0.05:
                start_time = position
                st.rerun()
            
            st.subheader("🎛️ Playback Settings")
            
            # Speed control
            slowdown_factor = st.number_input(
                "Slowdown Factor",
                min_value=0.1,
                max_value=10.0,
                value=2.0,
                step=0.1,
                help="1.0 = normal speed, 2.0 = half speed, 0.5 = double speed"
            )
            
            # Loop control
            num_loops = st.number_input(
                "Number of Loops",
                min_value=0,
                max_value=1000,
                value=1,
                step=1,
                help="0 = infinite loops"
            )
            
            # Process audio button
            if st.button("🔄 Process Audio", type="primary"):
                try:
                    with st.spinner("Processing audio..."):
                        # Extract time window
                        audio_segment = extract_time_window(
                            st.session_state.audio_data,
                            st.session_state.sample_rate,
                            start_time,
                            end_time
                        )
                        
                        # Apply slowdown
                        if slowdown_factor != 1.0:
                            processed_segment = slow_down_audio(audio_segment, slowdown_factor)
                        else:
                            processed_segment = audio_segment
                        
                        st.session_state.processed_audio = processed_segment
                        st.success("✅ Audio processed successfully!")
                        
                except Exception as e:
                    st.error(f"Processing error: {str(e)}")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.session_state.audio_data is not None:
            st.subheader("🎵 Audio Information")
            
            # Display audio info
            info_col1, info_col2, info_col3 = st.columns(3)
            with info_col1:
                st.metric("Duration", f"{st.session_state.audio_duration:.2f} s")
            with info_col2:
                st.metric("Sample Rate", f"{st.session_state.sample_rate} Hz")
            with info_col3:
                if st.session_state.processed_audio is not None:
                    processed_duration = len(st.session_state.processed_audio) / st.session_state.sample_rate
                    st.metric("Processed Length", f"{processed_duration:.2f} s")
            
            # Waveform visualization (simplified)
            if st.session_state.processed_audio is not None:
                st.subheader("📊 Processed Audio Waveform")
                
                # Downsample for visualization
                downsample_factor = max(1, len(st.session_state.processed_audio) // 1000)
                viz_audio = st.session_state.processed_audio[::downsample_factor]
                
                st.line_chart(viz_audio[:1000])  # Limit to first 1000 samples for performance
        else:
            st.info("👆 Upload an audio file in the sidebar to get started!")
    
    with col2:
        if st.session_state.processed_audio is not None:
            st.subheader("🎮 Playback Controls")
            
            # Control buttons
            col_play, col_stop = st.columns(2)
            
            with col_play:
                if not st.session_state.is_playing:
                    if st.button("▶️ Play", type="primary", use_container_width=True):
                        st.session_state.is_playing = True
                        st.session_state.current_loop = 0
                        
                        # Start playback in thread
                        playback_thread = threading.Thread(
                            target=play_audio_segment,
                            args=(st.session_state.processed_audio, st.session_state.sample_rate, num_loops),
                            daemon=True
                        )
                        playback_thread.start()
                        st.rerun()
                else:
                    st.button("⏸️ Playing...", disabled=True, use_container_width=True)
            
            with col_stop:
                if st.button("⏹️ Stop", use_container_width=True):
                    stop_playback()
                    st.rerun()
            
            # Status display
            if st.session_state.is_playing:
                if num_loops == 0:
                    st.success(f"🔄 Playing loop {st.session_state.current_loop} (infinite)")
                else:
                    progress = min(st.session_state.current_loop / num_loops, 1.0) if num_loops > 0 else 0
                    st.success(f"🔄 Playing loop {st.session_state.current_loop} of {num_loops}")
                    st.progress(progress)
            elif st.session_state.processed_audio is not None:
                st.info("⏹️ Ready to play")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        **Tips:**
        - 🎵 Supports audio formats: WAV, MP3, FLAC, AAC, OGG
        - 🎬 Supports video formats: MP4, MOV, AVI, MKV (extracts audio)
        - ⚡ Process audio first, then use playback controls
        - 🔄 Set loops to 0 for infinite playback
        - ⏹️ Use Stop button to halt infinite loops
        """
    )


if __name__ == "__main__":
    main()