# Trigger behavior

## Direct trigger

If Miguel sends an audio and the accompanying message is exactly or primarily `standup`, treat it as a **zero-touch** end-to-end workflow request. No confirmation. No preview. No options.

## Expected behavior

1. Accept the attached audio path.
2. Execute `run_standup_workflow.py` with `--send` (always auto-send).
3. Wait for the script to complete synchronously.
4. If exit code 0: reply with `✅ Standup del [Fecha] procesado exitosamente. El reporte ha sido enviado por correo electrónico.`
5. If exit code non-zero: reply with the raw stderr traceback.

## Do not

- Do not explain what a standup is.
- Do not ask unnecessary clarification unless the audio is missing or unusable.
- Do not show the standup summary in the Telegram chat.
- Do not ask "would you like me to send the email?" -- always send it.
- Do not offer follow-up options like "would you like to review it first?".
- Do not claim the email was sent unless delivery succeeded (exit code 0).
- Do not simulate or promise background/async execution.
- Do not send filler messages like "I am processing it, I will let you know when it is done."
- Do not promise future deliveries. Execute synchronously and reply with actual results or the raw error in the same turn.
- Do not hallucinate extra steps, menus, or options after the workflow completes.
