# Telegram Standup Assistant

Turn a short daily standup recording into a clean, shareable summary email.

## What it does

This workflow takes a standup audio file sent through Telegram and turns it into:

- a transcription
- cleaned terminology using a domain dictionary
- a concise summary by participant
- key decisions and highlights
- an action-items table
- a polished HTML email ready for review or forwarding

## Why it exists

Daily standups are useful, but the follow-up is usually messy:

1. record audio
2. move it to another device
3. upload it to a transcription tool
4. fix names and internal product terms
5. rewrite the meeting into something readable
6. send it by email

This project reduces that friction into a simpler flow.

## Workflow

```text
Telegram audio
   ↓
Speech-to-text
   ↓
Dictionary cleanup
   ↓
Structured summary
   ↓
HTML email draft
   ↓
Send to review inbox
```

## Features

- Supports short standup recordings from Telegram
- Works with `.ogg`, `.m4a`, and similar audio formats
- Uses `faster-whisper` for local transcription
- Handles internal naming through a domain dictionary
- Produces professional email output in Spanish
- Uses HTML tables and clean sectioning for readability

## Example use case

A support team lead records the team standup, sends the audio to the assistant in Telegram with the trigger `standup`, and receives a polished summary email in their Gmail inbox for final review.

## Repository structure

```text
scripts/
  transcribe_audio.py
examples/
  domain_dictionary.example.json
templates/
  standup-email-template.mml
```

## Requirements

- Python 3.14 or another supported Python runtime
- `faster-whisper`
- `ffmpeg`
- an email sender such as Himalaya (optional, for final delivery)

## Install

### 1. Install transcription dependencies

```bash
python3 -m pip install faster-whisper
```

### 2. Install ffmpeg

Make sure `ffmpeg` is available in your environment.

### 3. Run transcription

```bash
python3 scripts/transcribe_audio.py ./meeting.m4a es
```

## Domain dictionary

Use a custom dictionary to preserve product names, abbreviations, and people names.

Example terms:

- USAP
- RCMLinx
- MD Web
- MDClaim+
- Providers
- Brayan
- Angie
- Jose
- Astrid
- Miguel

## Email output

The included MML template shows how to generate a bilingual-friendly, structured email with:

- titles
- participant sections
- key points
- action table

## Security notes

This public repository intentionally excludes:

- API keys
- tokens
- app passwords
- personal emails beyond placeholders
- raw meeting audio
- private calendar data
- private assistant memory

## Status

This repository captures the public, reusable version of a working prototype built around Telegram, local transcription, and HTML standup summaries.

## License

MIT
