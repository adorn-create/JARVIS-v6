# JARVIS-v6 — Local Windows Desktop Assistant

JARVIS uses Ollama for local chat and screen analysis, SQLite conversation history, optional Whisper voice input, and approval-gated Windows UI controls. Prompts and screenshots are sent only to the local Ollama server configured on loopback.

## Install
1. Install the latest Ollama for Windows from [ollama.com/download](https://ollama.com/download). Use Ollama 0.7.0 or newer for the vision model.
2. Double-click `SETUP.bat`.
3. Setup offers separate opt-in pulls for the chat and vision models. Both require several GB of disk space; the vision model is about 6 GB.
4. Choose `Y` to install optional voice/wake-word and desktop-control packages when prompted.
5. Choose `Y` at the optional face-detection prompt to install OpenCV.
6. Setup launches JARVIS. Later, use `LAUNCH.bat`.

If you skip the model pulls, run these commands manually:

```powershell
ollama run hf.co/mradermacher/Qwen2.5-7B-Instruct-abliterated-GGUF:Q4_K_M
ollama pull qwen2.5vl:7b
```

The chat model is the Q4_K_M GGUF quantization of `huihui-ai/Qwen2.5-7B-Instruct-abliterated`; it is about 4.8 GB. `ollama run` opens an interactive prompt after downloading it; enter `/bye` to return to PowerShell. Setup's opt-in pull avoids opening that prompt.
The chat model runs through Ollama's local OpenAI-compatible API. The vision model is a separate local model because the chat model does not accept images.

## Settings

Relevant `.env` settings:

```ini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=hf.co/mradermacher/Qwen2.5-7B-Instruct-abliterated-GGUF:Q4_K_M
OLLAMA_VISION_MODEL=qwen2.5vl:7b
OLLAMA_REQUEST_TIMEOUT=600
JARVIS_STT_MODEL=small.en
JARVIS_STT_DEVICE=cpu
JARVIS_STT_COMPUTE=int8
JARVIS_MAX_TOOL_ROUNDS=8
JARVIS_WAKE_THRESHOLD=0.5
```

`OLLAMA_BASE_URL` is restricted to localhost so prompts and screenshots are not sent to a remote endpoint. Increase `OLLAMA_REQUEST_TIMEOUT` between 30 and 1800 seconds if model inference is slow.

## Features
- Local chat with the configured Ollama model and bounded tool calling
- Multi-step planning, progress updates, and explicit error reporting
- SQLite conversation history and user-approved saved preferences/tasks
- Search for older conversation context and saved memory; ask JARVIS to forget a saved item
- System performance dashboard and animated HUD status
- Allowlisted app launch, read-only filename search, web search, and website opening
- Local screenshot analysis with `qwen2.5vl:7b`
- Optional Windows UI Automation: list visible windows and named controls, enter text in non-password fields, and click named buttons
- UI actions require per-action approval; text entry is verified and clicks are followed by screen inspection
- Optional push-to-talk Whisper speech recognition and offline `pyttsx3` speech
- Optional “Hey JARVIS” wake word, microphone-level display, and speech interruption
- Optional local face-count detection, enabled only by its HUD toggle and confirmation

## Privacy and safety
- Chat prompts, saved memory, window information, and screen images are processed by the local Ollama server. Model files are downloaded from Ollama when you opt in to setup pulls.
- Voice audio is transcribed locally; the transcript is sent to the local Ollama server. Wake detection runs locally and is off until you explicitly enable it.
- Face detection runs locally and is off until you explicitly enable it. While enabled, the camera stays active and the HUD shows its status and detected face count. JARVIS detects counts only: it does not identify people, save frames or biometric data, or provide access control. Turn it off with the HUD toggle or close JARVIS.
- Web search sends the search query to DuckDuckGo; opening websites connects to the selected site.
- JARVIS only saves preferences/tasks when you explicitly ask it to remember them, then asks for confirmation. `/clear` in console mode clears conversation history but preserves saved memory.
- JARVIS asks before each UI click or text entry. It will not type into password or credential-related fields. Review the exact text before approving.
- There is no arbitrary shell-execution tool. App launching is allowlisted and file search is read-only.
- Keep `.env` private. Existing OpenRouter settings in an older `.env` are ignored by this build.

## Troubleshooting
- If JARVIS cannot connect, start the Ollama Windows app or run `ollama serve`, then check `ollama list`.
- If a model is missing, use the commands in Install. The Hugging Face model name must match `OLLAMA_MODEL`.
- If a Hugging Face pull fails with a `realm host` mismatch, update Ollama to the latest stable Windows release and retry. This is an Ollama registry redirect issue, not a JARVIS launcher issue ([Ollama issue #15661](https://github.com/ollama/ollama/issues/15661)).
- The first Whisper use downloads the selected speech model and may take a while.
- If optional voice packages fail on Python 3.14, install Python 3.12 and create a compatible environment.
- If setup reports that an existing virtual environment uses an unsupported Python version, rename `.venv` and rerun `SETUP.bat`; JARVIS requires Python 3.11 or 3.12.
- If an app does not expose accessible UI controls, JARVIS may be unable to inspect or operate it.


## Optional hand gesture recognition

Install the optional dependencies in the activated project environment:

```powershell
pip install -r requirements-gestures.txt
```

Launch JARVIS and press **GESTURES: OFF** to enable the camera after the confirmation prompt.
Recognition is local and displays labels only (OPEN PALM, FIST, PEACE, POINT, THUMBS UP,
NO HAND). Gestures do not execute computer actions or approve prompts. Turn it off
to release the camera. Hand recognition and face detection share the camera and are
not intended to run simultaneously.


## Local face unlock (optional)

Install face-unlock dependencies with `pip install -r requirements-face.txt`, then enroll using:

```powershell
.venv\Scripts\python.exe src\main.py --enroll-face
```

After enrollment, startup requires a local face match. Profile samples are stored in `%LOCALAPPDATA%\JARVIS\face_auth\face_samples.npz`. Delete that file to remove the enrollment. The feature uses OpenCV LBPH and is a convenience lock, not strong authentication; it can be spoofed by photos/video. Do not rely on it to protect sensitive data or replace Windows sign-in.

Gesture recognition dependencies can be installed with `pip install -r requirements-gestures.txt`.


## Local multi-user face unlock

Face unlock is an optional local convenience lock, not strong anti-spoof authentication. It uses OpenCV LBPH and can be fooled by photographs/video; do not use it as the only protection for sensitive data.

Install the face dependencies with `pip install -r requirements-face.txt`. Enroll the owner first using `python src/main.py --enroll-face` (camera enrollment window; press Q to cancel). After owner enrollment, every startup requires a recognized face. The owner can add a user with `python src/main.py --enroll-face Alice`; owner authentication is required before capture. List profiles with `python src/main.py --list-faces`; remove a non-owner profile with `python src/main.py --remove-face Alice` (owner authentication required). Profiles and face samples are stored locally under `%LOCALAPPDATA%\JARVIS\face_auth`.
