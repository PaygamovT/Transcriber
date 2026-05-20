import pytest
import numpy as np
import sounddevice as sd
from unittest.mock import MagicMock, patch
from src.services.audio import AudioRecorder

def test_audio_recorder_initialization():
    """Test standard initialization and default attributes."""
    recorder = AudioRecorder(sample_rate=16000, channels=1)
    assert recorder.sample_rate == 16000
    assert recorder.channels == 1
    assert not recorder.is_recording
    assert recorder.stream is None
    assert len(recorder.audio_buffers) == 0

@patch("sounddevice.InputStream")
def test_audio_recording_lifecycle(mock_input_stream_class):
    """Test start, callback, and stop lifecycle of the recorder."""
    # Setup mock InputStream
    mock_stream = MagicMock()
    mock_input_stream_class.return_value = mock_stream
    
    recorder = AudioRecorder(sample_rate=16000, channels=1)
    
    # 1. Start recording
    recorder.start_recording()
    
    assert recorder.is_recording
    assert recorder.stream == mock_stream
    mock_input_stream_class.assert_called_once()
    mock_stream.start.assert_called_once()
    
    # 2. Simulate callback calls (receiving audio chunks)
    # The callback is passed as a parameter to sounddevice.InputStream constructor
    kwargs = mock_input_stream_class.call_args[1]
    callback_fn = kwargs["callback"]
    
    # Create sample dummy numpy array input data
    dummy_data_1 = np.array([[0.1], [0.2], [0.3]], dtype=np.float32)
    dummy_data_2 = np.array([[0.4], [0.5], [0.6]], dtype=np.float32)
    
    callback_fn(dummy_data_1, len(dummy_data_1), {}, None)
    callback_fn(dummy_data_2, len(dummy_data_2), {}, None)
    
    assert len(recorder.audio_buffers) == 2
    np.testing.assert_array_equal(recorder.audio_buffers[0], dummy_data_1)
    np.testing.assert_array_equal(recorder.audio_buffers[1], dummy_data_2)
    
    # 3. Stop recording and verify conversion to WAV
    wav_bytes = recorder.stop_recording()
    
    assert not recorder.is_recording
    assert recorder.stream is None
    mock_stream.stop.assert_called_once()
    mock_stream.close.assert_called_once()
    
    # Check that we received some non-empty bytes back (WAV file content)
    assert len(wav_bytes) > 0
    # A standard WAV file starts with the RIFF header
    assert wav_bytes.startswith(b"RIFF")

def test_stop_recording_when_not_recording():
    """Test that stop_recording returns empty bytes if not active."""
    recorder = AudioRecorder()
    assert recorder.stop_recording() == b""

def test_start_recording_already_recording():
    """Test that start_recording does nothing if already recording."""
    with patch("sounddevice.InputStream") as mock_stream_class:
        recorder = AudioRecorder()
        recorder.start_recording()
        
        # Call it again
        recorder.start_recording()
        
        # InputStream should only be instantiated once
        mock_stream_class.assert_called_once()

def test_convert_to_wav():
    """Test convert_to_wav correctly converts floating numpy values to PCM 16-bit WAV bytes."""
    recorder = AudioRecorder(sample_rate=8000, channels=2)
    
    # Create stereo data ranging from -1.0 to 1.0
    dummy_data = np.array([[-1.0, 1.0], [0.0, 0.0], [0.5, -0.5]], dtype=np.float32)
    wav_bytes = recorder.convert_to_wav(dummy_data)
    
    assert wav_bytes.startswith(b"RIFF")
    
    # We can parse the wav bytes using the built-in wave module to verify the settings
    import io
    import wave
    
    wav_io = io.BytesIO(wav_bytes)
    with wave.open(wav_io, "rb") as wav_file:
        assert wav_file.getnchannels() == 2
        assert wav_file.getsampwidth() == 2  # 16-bit
        assert wav_file.getframerate() == 8000
        assert wav_file.getnframes() == 3
