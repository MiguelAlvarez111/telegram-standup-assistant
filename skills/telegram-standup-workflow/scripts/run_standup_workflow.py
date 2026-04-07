#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from openai import OpenAI


BASE = Path(__file__).resolve().parent.parent
VENV_PYTHON = str(BASE / '.venv311-diarization/bin/python3')

JSON_SCHEMA_INSTRUCTION = """

## Formato de salida obligatorio

Responde ÚNICAMENTE con un objeto JSON válido (sin texto adicional, sin bloques markdown).
Estructura exacta requerida:

{
  "general_summary": "Resumen ejecutivo de la reunión (1-2 párrafos).",
  "participants": ["Nombre 1", "Nombre 2"],
  "participant_blocks": [
    {
      "name": "Nombre 1",
      "achievements": ["Qué hizo"],
      "blockers": ["Qué lo detiene"],
      "plans": ["Qué hará hoy"]
    }
  ],
  "key_points": ["Decisión o anuncio importante a nivel general"],
  "actions": [
    {
      "task": "Descripción clara de la tarea",
      "owner": "Nombre del responsable (o 'Sin asignar')"
    }
  ],
  "confidence_warnings": ["Nota si el audio estaba confuso o faltan nombres"]
}

Reglas estrictas:
- general_summary: string con 1-2 párrafos de resumen ejecutivo.
- participants: lista de strings con los nombres detectados.
- participant_blocks: lista de objetos. Cada objeto tiene "name" (string), "achievements" (lista de strings), "blockers" (lista de strings) y "plans" (lista de strings). Incluir 1-3 items por categoría.
- key_points: lista de strings con las decisiones, anuncios o hitos más relevantes.
- actions: lista de objetos con "task" (string) y "owner" (string). Si no hay responsable claro, usar "Sin asignar".
- confidence_warnings: lista de strings. Si el audio es claro y todos los participantes fueron identificados, devolver lista vacía [].
- Si no puedes identificar con confianza el nombre de un participante, usa "Participante 1", "Participante 2", etc.
- Si no hay acciones claras, incluye al menos una acción genérica de seguimiento.
"""


def run(cmd, check=True):
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


GEMINI_API_KEY = 'AIzaSyAmVs8Sfeqd3bSFKKl-DrrKMRx2rP6nqGA'
GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/'


def build_llm_client(api_key=None, base_url=None):
    return OpenAI(
        api_key=api_key or os.environ.get('OPENAI_API_KEY', GEMINI_API_KEY),
        base_url=base_url or os.environ.get('OPENAI_API_BASE', GEMINI_BASE_URL),
    )


def _load_domain_dictionary():
    path = BASE / 'references/domain-dictionary.json'
    return json.loads(path.read_text(encoding='utf-8'))


def load_whisper_corrections():
    return _load_domain_dictionary().get('whisper_corrections', {})


def normalize_entities(text):
    for old, new in load_whisper_corrections().items():
        text = re.sub(rf'\b{re.escape(old)}\b', new, text, flags=re.IGNORECASE)
    return text


def _fallback_summary(error_msg):
    return {
        'participants': ['Equipo'],
        'general_summary': f'[Error LLM] {error_msg}',
        'participant_blocks': [],
        'key_points': [],
        'actions': [],
        'confidence_warnings': [f'LLM call failed: {error_msg}'],
    }


def _bridge_participant_blocks(raw_blocks):
    """Convert structured participant objects to backward-compatible tuples."""
    result = []
    for block in raw_blocks:
        if not isinstance(block, dict):
            continue
        name = block.get('name', 'Participante')
        bullets = []
        for item in block.get('achievements', []):
            if item:
                bullets.append(item)
        for item in block.get('blockers', []):
            if item:
                bullets.append(f'[Blocker] {item}')
        for item in block.get('plans', []):
            if item:
                bullets.append(f'[Plan] {item}')
        if bullets:
            result.append((name, bullets))
    return result


def summarize_from_text(text, *, client, model):
    prompt_path = BASE / 'references/standup-prompt.md'
    base_prompt = prompt_path.read_text(encoding='utf-8')

    domain = _load_domain_dictionary()
    terms = domain.get('terms', [])
    domain_instruction = (
        '\n\n## Terminología del equipo\n\n'
        'El equipo utiliza los siguientes nombres propios, sistemas y términos técnicos. '
        'Si la transcripción contiene errores ortográficos o fonéticos similares a estos términos, '
        'usa la nomenclatura correcta en tu resumen:\n\n'
        + ', '.join(terms) + '\n'
    )

    system_prompt = base_prompt + domain_instruction + JSON_SCHEMA_INSTRUCTION

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': text},
            ],
            temperature=0.3,
            response_format={'type': 'json_object'},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
    except Exception as exc:
        return _fallback_summary(str(exc))

    return {
        'participants': data.get('participants') or ['Equipo'],
        'general_summary': data.get('general_summary', ''),
        'participant_blocks': _bridge_participant_blocks(
            data.get('participant_blocks', []),
        ),
        'key_points': data.get('key_points') or [],
        'actions': [
            (a.get('task', ''), a.get('owner', 'Sin asignar'))
            for a in data.get('actions', [])
            if isinstance(a, dict) and a.get('task')
        ],
        'confidence_warnings': data.get('confidence_warnings') or [],
    }


def write_summary_artifact(output_prefix: str, payload: dict, summary: dict, warnings: list):
    artifact = {
        'transcript_language': payload.get('language'),
        'transcript_duration': payload.get('duration'),
        'participants': summary.get('participants', []),
        'general_summary': summary.get('general_summary'),
        'participant_blocks': summary.get('participant_blocks', []),
        'key_points': summary.get('key_points', []),
        'actions': summary.get('actions', []),
        'confidence_warnings': summary.get('confidence_warnings', []),
        'warnings': warnings,
    }
    path = Path(f'{output_prefix}-summary.json')
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio')
    parser.add_argument('--transcript-json', help='Pre-transcribed JSON file (skips audio transcription)')
    parser.add_argument('--date', required=True)
    parser.add_argument('--output-prefix', required=True)
    parser.add_argument('--gmail-user')
    parser.add_argument('--gmail-app-password')
    parser.add_argument('--send', action='store_true')
    parser.add_argument('--openai-api-key', default=os.environ.get('OPENAI_API_KEY'))
    parser.add_argument('--openai-base-url', default=os.environ.get('OPENAI_BASE_URL'))
    parser.add_argument('--openai-model', default=os.environ.get('OPENAI_MODEL', 'gemini-2.5-flash'))
    args = parser.parse_args()

    if not args.audio and not args.transcript_json:
        parser.error('either --audio or --transcript-json is required')

    transcript_path = Path(f'{args.output_prefix}-transcript.json')
    draft_path = Path(f'{args.output_prefix}.mml')

    if args.transcript_json:
        transcript = Path(args.transcript_json).read_text(encoding='utf-8')
    else:
        whisperx_script = BASE / 'scripts/transcribe_with_whisperx.py'
        if Path(VENV_PYTHON).exists() and whisperx_script.exists():
            result = run([VENV_PYTHON, str(whisperx_script), args.audio, 'es'], check=False)
            if result.returncode == 0 and result.stdout.strip():
                transcript = result.stdout
            else:
                transcript = run([VENV_PYTHON, str(BASE / 'scripts/transcribe_audio.py'), args.audio, 'es']).stdout
        else:
            transcript = run([VENV_PYTHON, str(BASE / 'scripts/transcribe_audio.py'), args.audio, 'es']).stdout

    transcript_path.write_text(transcript)
    payload = json.loads(transcript)

    warnings = []
    raw_text = (payload.get('text') or '').strip()
    if len(raw_text) < 80:
        warnings.append('La transcripción es muy corta; el resumen puede ser incompleto.')
    raw_text = normalize_entities(raw_text)

    client = build_llm_client(api_key=args.openai_api_key, base_url=args.openai_base_url)
    summary = summarize_from_text(raw_text, client=client, model=args.openai_model)
    summary_path = write_summary_artifact(args.output_prefix, payload, summary, warnings)

    build_cmd = [
        'python3', str(BASE / 'scripts/build_standup_mml.py'),
        '--template', str(BASE / 'references/standup-email-template.mml'),
        '--output', str(draft_path),
        '--date', args.date,
        '--from-header', f'From: Miguel Alvarez <{args.gmail_user or "dando.zentido111@gmail.com"}>',
        '--to-header', f'To: {args.gmail_user or "dando.zentido111@gmail.com"}',
        '--participants', ', '.join(summary['participants']),
        '--general-summary', summary['general_summary'],
    ]
    for name, bullets in summary['participant_blocks']:
        build_cmd += ['--participant-block', name + '::' + '||'.join(bullets)]
    for kp in summary['key_points']:
        build_cmd += ['--key-point', kp]
    for task, owner in summary['actions']:
        build_cmd += ['--action', task + '::' + owner]
    run(build_cmd)

    if args.send:
        if not args.gmail_user or not args.gmail_app_password:
            raise SystemExit('Missing Gmail credentials for --send')
        send_cmd = [
            'python3', str(BASE / 'scripts/send_via_gmail_smtp.py'),
            '--mml', str(draft_path),
            '--gmail-user', args.gmail_user,
            '--gmail-app-password', args.gmail_app_password,
            '--to', args.gmail_user,
            '--subject', f'Standup Diario – {args.date}',
        ]
        run(send_cmd)

    print(json.dumps({
        'transcript_path': str(transcript_path),
        'summary_path': str(summary_path),
        'draft_path': str(draft_path),
        'participants': summary['participants'],
        'sent': bool(args.send),
        'warnings': warnings,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
