import io
import wave
import logging
import os
import numpy as np
import sounddevice as sd
from typing import Optional

# Setup logging
logger = logging.getLogger("transcriber.audio")
log_level_env = os.environ.get("LOG_LEVEL", "DEBUG").upper()
# Set log level based on environment or default to DEBUG for verbose logging
logger.setLevel(getattr(logging, log_level_env, logging.DEBUG))

class AudioRecorder:
    """Service to record audio from the microphone using sounddevice and numpy."""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        logger.debug("AudioRecorder.__init__ entering")
        self.sample_rate = sample_rate
        self.channels = channels
        self.stream: Optional[sd.InputStream] = None
        self.audio_buffers = []
        self.is_recording = False
        
        # Silence Detection & Auto-Slicing parameters
        self.silence_threshold = 0.015
        self.silence_timer_seconds = 0.0
        self.silence_detected_callback = None
        self.voice_detected = False
        
        logger.debug(f"AudioRecorder initialized with sample_rate={self.sample_rate}, channels={self.channels}")
        logger.debug("AudioRecorder.__init__ exiting successfully")
 
    def _callback(self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags) -> None:
        """Callback function called by sounddevice InputStream for each block of audio."""
        if status:
            logger.warning(f"InputStream callback status warning: {status}")
        if self.is_recording:
            # Append a copy of the input data block to avoid issues with buffer overwriting
            self.audio_buffers.append(indata.copy())
            
            # Continuous Silence Detection & Auto-Slicing
            if getattr(self, "silence_detection_enabled", False) and self.silence_detected_callback:
                if indata.size > 0:
                    rms = np.sqrt(np.mean(indata**2))
                else:
                    rms = 0.0
                
                block_duration = frames / self.sample_rate
                if rms >= self.silence_threshold:
                    self.voice_detected = True
                    self.silence_timer_seconds = 0.0
                else:
                    self.silence_timer_seconds += block_duration
                    if self.silence_timer_seconds >= 1.0:
                        if self.voice_detected and self.audio_buffers:
                            # Slice segment (concatenate all buffers up to now)
                            logger.debug("Silence threshold reached 1.0s. Slicing audio segment.")
                            recording_data = np.concatenate(self.audio_buffers, axis=0)
                            
                            # Clear buffer seamlessly
                            self.audio_buffers = []
                            self.voice_detected = False
                            
                            # Convert to WAV and trigger callback
                            try:
                                wav_bytes = self.convert_to_wav(recording_data)
                                if len(wav_bytes) > 0:
                                    self.silence_detected_callback(wav_bytes)
                            except Exception as e:
                                logger.error(f"Error in silence detected callback processing: {e}", exc_info=True)
                        else:
                            # Discard empty silence buffer to prevent memory growth
                            self.audio_buffers = []
                            
                        self.silence_timer_seconds = 0.0
 
    def start_recording(self, silence_detection_enabled: bool = False) -> None:
        """Starts the audio recording session."""
        logger.debug(f"AudioRecorder.start_recording entering, silence_detection_enabled={silence_detection_enabled}")
        if self.is_recording:
            logger.warning("Recording is already in progress")
            return
            
        self.audio_buffers = []
        self.is_recording = True
        self.silence_detection_enabled = silence_detection_enabled
        self.silence_timer_seconds = 0.0
        self.voice_detected = False
        
        try:
            logger.debug("Initializing sounddevice InputStream")
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                callback=self._callback
            )
            self.stream.start()
            logger.info("Audio recording successfully started")
        except Exception as e:
            self.is_recording = False
            self.stream = None
            logger.error(f"Failed to start audio recording stream: {e}", exc_info=True)
            raise
            
        logger.debug("AudioRecorder.start_recording exiting")

    def stop_recording(self) -> bytes:
        """Stops the audio recording session and returns the captured audio as WAV bytes.
        
        Returns:
            bytes: The WAV formatted audio data in-memory.
        """
        logger.debug("AudioRecorder.stop_recording entering")
        if not self.is_recording:
            logger.warning("Recording was not in progress")
            return b""
            
        self.is_recording = False
        
        if self.stream:
            try:
                logger.debug("Stopping and closing InputStream")
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error while closing InputStream: {e}", exc_info=True)
            self.stream = None
            
        if not self.audio_buffers:
            logger.warning("No audio data was captured")
            return b""
            
        # Concatenate all recorded buffers
        logger.debug("Concatenating recorded audio buffers")
        recording_data = np.concatenate(self.audio_buffers, axis=0)
        
        # Calculate samples captured and duration
        samples_captured = len(recording_data)
        duration = samples_captured / self.sample_rate
        memory_size = recording_data.nbytes
        logger.info(f"Recorded {samples_captured} samples ({duration:.2f}s). Buffer size: {memory_size} bytes")
        
        # Convert raw float32 array to WAV bytes in-memory
        wav_bytes = self.convert_to_wav(recording_data)
        logger.debug("AudioRecorder.stop_recording exiting successfully")
        return wav_bytes

    def convert_to_wav(self, recording_data: np.ndarray) -> bytes:
        """Converts raw float32 numpy array to WAV bytes.
        
        WAV files require 16-bit integer PCM format normally for best compatibility.
        """
        logger.debug("AudioRecorder.convert_to_wav entering")
        
        # Normalize and convert float32 (range -1.0 to 1.0) to 16-bit PCM (range -32768 to 32767)
        # Avoid overflow by clipping first
        clipped = np.clip(recording_data, -1.0, 1.0)
        pcm_data = (clipped * 32767).astype(np.int16)
        
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_data.tobytes())
            
        wav_bytes = wav_io.getvalue()
        logger.debug(f"Converted to WAV bytes, total WAV size: {len(wav_bytes)} bytes")
        logger.debug("AudioRecorder.convert_to_wav exiting")
        return wav_bytes
