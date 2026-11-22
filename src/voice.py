"""Optional Whisper speech input, offline TTS, and wake-word detection."""
import logging
import os
import threading

LOG = logging.getLogger("jarvis.voice")


class VoiceEngine:
    def __init__(self, model_size=None):
        self.model_size = model_size or os.getenv("JARVIS_STT_MODEL", "small.en")
        self._whisper = None
        self._tts = None
        self._tts_lock = threading.Lock()
        self._stop_speaking = threading.Event()

    def _load_stt(self):
        if self._whisper is None:
            from faster_whisper import WhisperModel

            self._whisper = WhisperModel(
                self.model_size,
                device=os.getenv("JARVIS_STT_DEVICE", "cpu"),
                compute_type=os.getenv("JARVIS_STT_COMPUTE", "int8"),
            )
        return self._whisper

    def record_and_transcribe(
        self, max_seconds=18, sample_rate=16000, on_level=None
    ):
        import numpy as np
        import sounddevice as sd

        device = sd.query_devices(kind="input")
        print(
            f"[JARVIS mic] Input: {device.get('name', 'Default microphone')}. "
            "Speak after listening prompt."
        )
        chunk_seconds = 0.2
        frames = int(sample_rate * chunk_seconds)
        ambient = []
        chunks = []
        started = False
        silence = 0
        threshold = 0.008
        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=frames,
        ) as stream:
            for _ in range(4):
                data, _ = stream.read(frames)
                ambient.append(float(np.sqrt(np.mean(np.square(data)) + 1e-9)))
            threshold = max(0.008, float(np.median(ambient)) * 2.8)
            print("[JARVIS mic] Listening...")
            for index in range(int(max_seconds / chunk_seconds)):
                data, _ = stream.read(frames)
                data = np.asarray(data, dtype=np.float32).reshape(-1)
                rms = float(np.sqrt(np.mean(np.square(data)) + 1e-9))
                if on_level:
                    on_level(min(1.0, rms * 8))
                if not started:
                    if rms >= threshold:
                        started = True
                        chunks.append(data)
                        silence = 0
                    elif index >= 25:
                        break
                else:
                    chunks.append(data)
                    silence = silence + 1 if rms < threshold else 0
                    if silence >= 7 and len(chunks) >= 3:
                        break
        if on_level:
            on_level(0)
        if not started:
            print("[JARVIS mic] No speech detected. Check input device/volume.")
            return ""
        model = self._load_stt()
        segments, info = model.transcribe(
            np.concatenate(chunks),
            language="en",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt="Natural conversational English. JARVIS is an AI assistant.",
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        print(f"[JARVIS STT] Language={info.language} Transcript={text}")
        return text

    def speak(self, text, on_complete=None):
        import pyttsx3

        try:
            with self._tts_lock:
                self._stop_speaking.clear()
                if self._tts is None:
                    self._tts = pyttsx3.init()
                    self._tts.setProperty("rate", 180)
                for chunk in _speech_chunks(text):
                    if self._stop_speaking.is_set():
                        break
                    self._tts.say(chunk)
                    self._tts.runAndWait()
        finally:
            if on_complete:
                on_complete()

    def stop(self):
        self._stop_speaking.set()
        if self._tts is None:
            return True
        try:
            self._tts.stop()
            return True
        except Exception:
            LOG.exception("TTS engine could not be interrupted")
            return False


def _speech_chunks(text, max_length=280):
    remaining = str(text).strip()
    chunks = []
    while len(remaining) > max_length:
        split_at = remaining.rfind(" ", 0, max_length)
        if split_at < 1:
            split_at = max_length
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


class WakeWordListener:
    def __init__(self, on_wake, on_status, on_level, on_error):
        self._on_wake = on_wake
        self._on_status = on_status
        self._on_level = on_level
        self._on_error = on_error
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self, wait=False, timeout=5.0):
        self._stop_event.set()
        thread = self._thread
        if wait and thread and thread is not threading.current_thread():
            thread.join(timeout=max(0.0, float(timeout)))
        return not (thread and thread.is_alive())

    def _listen(self):
        try:
            import numpy as np
            import sounddevice as sd
            from openwakeword.model import Model
            from openwakeword.utils import download_models

            self._on_status("WAKE WORD • LOADING LOCAL MODEL")
            download_models(model_names=["hey_jarvis"])
            if self._stop_event.is_set():
                return
            model = Model(
                wakeword_models=["hey jarvis"],
                inference_framework="onnx",
            )
            threshold = float(os.getenv("JARVIS_WAKE_THRESHOLD", "0.5"))
            if not 0.1 <= threshold <= 0.99:
                raise ValueError("JARVIS_WAKE_THRESHOLD must be between 0.1 and 0.99.")
            self._on_status("WAKE WORD ON • MICROPHONE ACTIVE")
            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="int16",
                blocksize=1280,
            ) as stream:
                frame_count = 0
                while not self._stop_event.is_set():
                    audio, _ = stream.read(1280)
                    audio = np.asarray(audio, dtype=np.int16).reshape(-1)
                    frame_count += 1
                    if frame_count % 5 == 0:
                        level = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
                        self._on_level(min(1.0, level / 8000))
                    predictions = model.predict(audio)
                    score = max(
                        (
                            value
                            for name, value in predictions.items()
                            if "hey_jarvis" in name.replace(" ", "_").lower()
                        ),
                        default=0,
                    )
                    if score >= threshold:
                        self._stop_event.set()
                        self._on_level(0)
                        self._on_status("WAKE WORD • ACTIVATED")
                        self._on_wake()
                        return
        except Exception as exc:
            if not self._stop_event.is_set():
                self._stop_event.set()
                self._on_error(str(exc))
        finally:
            self._on_level(0)
