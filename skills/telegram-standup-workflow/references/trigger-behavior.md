# Trigger behavior

## Direct trigger

If Miguel sends an audio and the accompanying message is exactly or primarily `standup`, treat it as an end-to-end workflow request.

## Expected behavior

1. Accept the attached audio path.
2. Transcribe it in Spanish.
3. Summarize it into the standup structure.
4. Build the `.mml` email draft.
5. If Miguel asks to send it, send it.
6. If Himalaya fails on Gmail Sent append, use the SMTP workaround.

## Do not

- Do not explain what a standup is.
- Do not ask unnecessary clarification unless the audio is missing or unusable.
- Do not claim the email was sent unless delivery succeeded.
