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
- Do not simulate or promise background/async execution.
- Do not send filler messages like "I am processing it, I will let you know when it is done."
- Do not promise future deliveries. Execute synchronously and reply with actual results or the raw error in the same turn.
