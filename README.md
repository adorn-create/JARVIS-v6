# JARVIS-v6 — Organized Windows Desktop Assistant

JARVIS combines OpenRouter chat, a desktop HUD, SQLite conversation history, optional Whisper voice input, screen analysis, and approval-gated Windows UI controls.

## Install
1. Extract this folder to a convenient location.
2. Double-click `SETUP.bat`.
3. Enter your **new** OpenRouter API key when prompted (input is hidden).
4. Choose `Y` to install optional voice packages (Whisper, offline speech, and wake-word detection).
5. Choose `Y` to install optional Windows desktop-control support.
6. Setup launches JARVIS. Later, use `LAUNCH.bat`.

When creating a new environment, setup prefers Python 3.12 and falls back to 3.11. An existing `.venv` is preserved; setup does not replace it.
The optional wake-word model downloads the first time you enable wake-word listening. Wake-word detection is off by default.

## Features
- OpenRouter chat with a configurable reasoning model (`OPENROUTER_MODEL` in `.env`; new installs default to `openai/gpt-4.1-mini`)
- Multi-step planning, bounded tool execution, progress updates, and explicit error reporting
- SQLite conversation history and user-approved saved preferences/tasks
- Search for older conversation context and saved memory; ask JARVIS to forget a saved item to remove it
- System performance dashboard and animated HUD status
- Allowlisted app launch, read-only filename search, web search, and website opening
- Screen analysis through the configured vision model
- Optional Windows UI Automation: list visible windows and named controls, enter text in non-password fields, and click named buttons
- UI actions require per-action approval; text entry is verified against the target control and clicks are followed by screen inspection
- Optional push-to-talk Whisper speech recognition and offline `pyttsx3` speech
- Optional “Hey JARVIS” wake word, microphone-level display, and speech interruption

## Settings

Relevant `.env` settings:

```ini
OPENROUTER_MODEL=openai/gpt-4.1-mini
OPENROUTER_VISION_MODEL=openai/gpt-4o-mini
JARVIS_STT_MODEL=small.en
JARVIS_STT_DEVICE=cpu
JARVIS_STT_COMPUTE=int8
JARVIS_MAX_TOOL_ROUNDS=8
JARVIS_WAKE_THRESHOLD=0.5
```

Set `OPENROUTER_MODEL` to a model available to your OpenRouter account. `JARVIS_WAKE_THRESHOLD` accepts values from `0.1` to `0.99`; the default is `0.5`.

## Privacy and safety
- The model has no arbitrary shell-execution tool. App launching is allowlisted and file search is read-only.
- JARVIS only saves preferences/tasks when you explicitly ask it to remember them, then asks for confirmation. Use `/clear` in console mode to clear conversation history; saved memory remains until you ask JARVIS to forget it.
- Enabling wake-word listening requires confirmation. Wake detection runs locally; audio is not saved or sent for wake detection. The microphone remains active until you turn wake word off.
- After wake activation or push-to-talk, Whisper transcribes locally; the transcript is sent to OpenRouter.
- Screen screenshots, window titles, and UI element labels may be sent to OpenRouter for analysis. Text you ask JARVIS to enter is also sent to OpenRouter. Close private windows and review the exact text in the approval prompt.
- JARVIS asks before each UI click or text entry. It will not type into password fields. Do not approve actions you do not recognize.
- Keep `.env` private. Never upload it or include API keys in screenshots. Revoke any key previously exposed.

## Troubleshooting
- If voice dependencies fail on Python 3.14, install Python 3.12 from python.org, then rerun setup.
- OpenRouter errors: verify the key, credits, and model access in your account.
- Microphone: check Windows Settings → System → Sound → Input and Privacy & security → Microphone.
- If an app does not expose accessible UI controls, JARVIS may be unable to inspect or operate it.
- The first Whisper use downloads the selected speech model and may take a while.
