---
name: telegram-standup-workflow
description: Process work standup audio sent through Telegram into a structured Spanish summary and email draft, then auto-send the email. Use when Miguel sends an audio and says `standup`, asks to process a standup, or wants a summary email from a team standup recording. This is a zero-touch pipeline -- no confirmation needed.
---

# Telegram Standup Workflow

Use this skill when Miguel sends a work audio with the trigger `standup` or asks to process a standup recording.

## Core rule

If Miguel sends audio and says `standup`, do **not** explain what a standup is. Do **not** show a summary in chat. Do **not** ask what to do next. Just execute the full pipeline and send the email.

## Zero-Touch Workflow

This is a fully automated pipeline. Every step runs without user interaction.

1. Run `scripts/run_standup_workflow.py` with `--send` to transcribe, summarize, build the email, and send it in one shot.
2. The script handles everything: WhisperX transcription, entity normalization, LLM summarization, MML email building, and SMTP delivery.
3. If the script exits with code 0, the email was sent. Reply with the success confirmation (see Telegram Response below).
4. If the script exits with a non-zero code, reply with the **exact raw stderr traceback**. Nothing else.

## CRITICAL EXECUTION RULE (NO BACKGROUND PROMISES)

- You MUST execute `run_standup_workflow.py` **synchronously**.
- DO NOT simulate or promise background execution.
- DO NOT send filler messages like "I am processing it, I will let you know when it is done."
- You must wait for the script to finish and reply in the **exact same turn**.
- Never promise future deliveries. Only output actual results.

## Preferred execution path

```bash
python3 skills/telegram-standup-workflow/scripts/run_standup_workflow.py \
  --audio <audio_path> \
  --date '<YYYY-MM-DD>' \
  --output-prefix integrations/email/standup-YYYY-MM-DD \
  --send \
  --gmail-user dando.zentido111@gmail.com \
  --gmail-app-password <app_password>
```

**ABSOLUTE COMMAND RULE:** You MUST execute the script using exactly `python3 skills/telegram-standup-workflow/scripts/run_standup_workflow.py [args]`. You are STRICTLY FORBIDDEN from creating virtual environments, using `sh -c`, activating `.venv` folders, or modifying the system environment. The script is already self-contained and hardcoded to resolve its own dependencies.

**ALWAYS pass `--send`**. The email must be sent automatically. Do not ask Miguel for permission to send. Do not show the summary in chat first. Do not offer options.

## Telegram Response

### On success (exit code 0):

Reply with ONLY this message, replacing the date:

> ✅ Standup del [YYYY-MM-DD] procesado exitosamente. El reporte ha sido enviado por correo electrónico.

Nothing else. No summary. No options. No "would you like to...".

### On failure (non-zero exit code):

Reply with the raw stderr output so Miguel can debug. No apologies, no suggestions, no "would you like me to try again". Just the error.

## Output rules

- Default language: Spanish.
- Tone: professional but accessible.
- Keep participant summaries concise: 2-3 key points per person when possible.
- Focus participant summaries on logros, bloqueos y planes del día.
- Extract puntos clave as decisions, announcements, and milestones.
- Keep action items explicit, assigned, and easy to scan.
- If speaker names are not confidently detected, fall back to `Participante 1`, `Participante 2`, etc.
- Use `references/standup-prompt.md` as the canonical quality bar for final standup summaries.

## Resources

- Template: `references/standup-email-template.mml`
- Dictionary: `references/domain-dictionary.json`
- Trigger notes: `references/trigger-behavior.md`
- Diarization notes: `references/diarization-notes.md`
- MML builder: `scripts/build_standup_mml.py`
- SMTP sender: `scripts/send_via_gmail_smtp.py`
- Basic transcription: `scripts/transcribe_audio.py`
- Advanced transcription: `scripts/transcribe_with_whisperx.py`
- End-to-end runner: `scripts/run_standup_workflow.py`
