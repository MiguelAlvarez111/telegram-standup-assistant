# Diarization / advanced transcription notes

## Runtime

Preferred advanced runtime lives in:
- `skills/telegram-standup-workflow/.venv311-diarization`

It was created with a local uv-managed Python 3.11 because the main environment Python 3.14 was incompatible with WhisperX stack requirements.

## Preferred path

When the advanced environment is available, prefer `scripts/transcribe_with_whisperx.py` over the basic faster-whisper path.

## Current status

- WhisperX transcription + alignment works.
- This already improves transcript quality and catches cues like `Vamos con Kelly` and `Hola, soy Angie`.
- Full speaker diarization attribution can be improved further, but this path is already a stronger base than the original transcript-only flow.
