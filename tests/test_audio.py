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

def test_silence_detection_disabled():
    """Verify that when silence detection is disabled, even a long pause does not trigger slicing."""
    recorder = AudioRecorder(sample_rate=16000, channels=1)
    callback_mock = MagicMock()
    recorder.silence_detected_callback = callback_mock
    recorder.silence_threshold = 0.015
    
    recorder.start_recording(silence_detection_enabled=False)
    
    # 1.0s of silence (16000 samples)
    silent_data = np.zeros((16000, 1), dtype=np.float32)
    recorder._callback(silent_data, len(silent_data), {}, None)
    
    assert callback_mock.call_count == 0
    assert len(recorder.audio_buffers) == 1  # Still accumulated in main buffer

def test_silence_detection_slicing():
    """Verify that silence detection correctly slices and resets buffer on 1s of silence."""
    recorder = AudioRecorder(sample_rate=16000, channels=1)
    callback_mock = MagicMock()
    recorder.silence_detected_callback = callback_mock
    recorder.silence_threshold = 0.015
    
    recorder.start_recording(silence_detection_enabled=True)
    
    # 1. Provide active audio (RMS high) - should not trigger silence timer
    loud_data = np.ones((8000, 1), dtype=np.float32) * 0.1  # RMS > 0.015
    recorder._callback(loud_data, len(loud_data), {}, None)
    assert recorder.silence_timer_seconds == 0.0
    assert len(recorder.audio_buffers) == 1
    assert callback_mock.call_count == 0
    
    # 2. Provide 0.5 seconds of silence (8000 samples at 16000Hz)
    silent_data_1 = np.zeros((8000, 1), dtype=np.float32)
    recorder._callback(silent_data_1, len(silent_data_1), {}, None)
    assert recorder.silence_timer_seconds == 0.5
    assert len(recorder.audio_buffers) == 2
    assert callback_mock.call_count == 0
    
    # 3. Provide another 0.5 seconds of silence to cross the 1.0s mark
    silent_data_2 = np.zeros((8000, 1), dtype=np.float32)
    recorder._callback(silent_data_2, len(silent_data_2), {}, None)
    
    # The 1.0s silence should trigger a slice, clear the buffer, and call the callback
    assert recorder.silence_timer_seconds == 0.0
    assert len(recorder.audio_buffers) == 0  # Buffer cleared seamlessly
    assert callback_mock.call_count == 1
    
    # The callback should receive valid WAV bytes
    captured_wav = callback_mock.call_args[0][0]
    assert captured_wav.startswith(b"RIFF")

