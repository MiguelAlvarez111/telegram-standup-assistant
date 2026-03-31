---
name: telegram-standup-workflow
description: Process work standup audio sent through Telegram into a structured Spanish summary and email draft. Use when Miguel sends an audio and says `standup`, asks to process a standup, or wants a summary email from a team standup recording. This skill should trigger for Telegram standup workflows involving transcription, domain dictionary cleanup, participant summaries, key points, action items, and HTML/MML email output.
---

# Telegram Standup Workflow

Use this skill when Miguel sends a work audio with the trigger `standup` or asks to process a standup recording.

## Core rule

If Miguel sends audio and says `standup`, do **not** explain what a standup is. Assume he wants the workflow executed.

## Workflow

1. Transcribe the audio in Spanish using `scripts/transcribe_audio.py` or the project transcriber.
2. Read `references/domain-dictionary.json` and preserve/correct internal names, systems, and terms when the transcript is noisy.
3. Produce a structured standup summary in Spanish with:
   - resumen general
   - participantes identificados
   - resumen por participante
   - puntos clave
   - acciones pendientes con responsable cuando se pueda inferir
4. Be honest about ambiguity. If audio is unclear, mark uncertain details instead of inventing.
5. Prefer the project email format with HTML sections and an actions table. Use `references/standup-email-template.mml` as the canonical structure.
6. Save generated drafts under `integrations/email/standup-YYYY-MM-DD.mml` unless the user asks otherwise.
7. If asked to send the email, verify the mailer path/config actually works before claiming it was sent.
8. If Himalaya fails on Gmail with `cannot add IMAP message` / `Folder doesn't exist` while appending to Sent, use `scripts/send_via_gmail_smtp.py` as the delivery workaround and keep the generated `.mml` draft.

## Output rules

- Default language: Spanish.
- Tone: professional but accessible.
- Keep participant summaries concise: 2-3 key points per person when possible.
- Focus participant summaries on logros, bloqueos y planes del día.
- Extract puntos clave as decisions, announcements, and milestones.
- Keep action items explicit, assigned, and easy to scan.
- Use headers, bullets, bold labels, and an HTML actions table in the email draft.
- If the transcript is long/noisy, prioritize clarity over literalness.
- If speaker names are confidently detected, use real names.
- If speaker names are not confidently detected, fall back to `Participante 1`, `Participante 2`, `Participante 3` rather than collapsing to `Equipo`.
- Use `references/standup-prompt.md` as the canonical quality bar for final standup summaries.

## Resources

- Template: `references/standup-email-template.mml`
- Dictionary: `references/domain-dictionary.json`
- Example output: `references/example-standup-2026-03-30.mml`
- Trigger notes: `references/trigger-behavior.md`
- Diarization notes: `references/diarization-notes.md`
- MML builder: `scripts/build_standup_mml.py`
- SMTP workaround sender: `scripts/send_via_gmail_smtp.py`
- Basic transcription: `scripts/transcribe_audio.py`
- Advanced transcription: `scripts/transcribe_with_whisperx.py`
- End-to-end runner: `scripts/run_standup_workflow.py`

## Preferred execution path

When the request is a direct standup trigger, prefer the end-to-end runner so the workflow produces stable artifacts:

```bash
python3 skills/telegram-standup-workflow/scripts/run_standup_workflow.py \
  --audio <audio_path> \
  --date '<fecha>' \
  --output-prefix integrations/email/standup-YYYY-MM-DD \
  [--send --gmail-user <gmail> --gmail-app-password <app_password>]
```

## Delivery note

If email sending fails, say exactly what failed (for example IMAP Sent/Drafts folder handling) and keep the generated `.mml` draft available.
