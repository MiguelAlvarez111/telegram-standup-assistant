#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from pathlib import Path

from openai import OpenAI


BASE = Path(__file__).resolve().parent.parent

JSON_SCHEMA_INSTRUCTION = """

## Formato de salida obligatorio

Responde ÚNICAMENTE con un objeto JSON válido (sin texto adicional, sin bloques markdown).
Estructura exacta requerida:

{
  "participants": ["Nombre1", "Nombre2"],
  "general_summary": "Resumen general breve de la reunión",
  "participant_blocks": [
    ["Nombre1", ["punto clave 1", "punto clave 2"]],
    ["Nombre2", ["punto clave 1", "punto clave 2"]]
  ],
  "key_points": ["punto clave global 1", "punto clave global 2"],
  "actions": [
    ["Descripción de la tarea", "Responsable"],
    ["Otra tarea", "Otro responsable"]
  ]
}

Reglas estrictas:
- participants: lista de strings con los nombres detectados.
- general_summary: string con un párrafo de resumen general.
- participant_blocks: lista de arrays de 2 elementos [nombre, [bullets]]. Cada nombre es un string y cada bullets es una lista de strings (2-3 puntos por participante).
- key_points: lista de strings con las decisiones, anuncios o hitos más relevantes.
- actions: lista de arrays de 2 elementos [tarea, responsable]. Cada elemento es un string.
- Si no puedes identificar con confianza el nombre de un participante, usa "Participante 1", "Participante 2", etc.
- Si no hay acciones claras, incluye al menos una acción genérica de seguimiento.
"""


def run(cmd, check=True):
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def build_llm_client(api_key=None, base_url=None):
    return OpenAI(
        api_key=api_key or os.environ.get('OPENAI_API_KEY', 'ollama'),
        base_url=base_url or os.environ.get('OPENAI_BASE_URL', 'http://localhost:11434/v1'),
    )


def load_domain_terms():
    dict_path = BASE / 'references/domain-dictionary.json'
    if not dict_path.exists():
        return []
    data = json.loads(dict_path.read_text(encoding='utf-8'))
    terms = data.get('terms', [])
    seen = []
    for t in terms:
        if t not in seen:
            seen.append(t)
    return seen


def summarize_from_text(text, *, client, model):
    prompt_path = BASE / 'references/standup-prompt.md'
    system_prompt = prompt_path.read_text(encoding='utf-8')

    domain_terms = load_domain_terms()
    if domain_terms:
        terms_list = ', '.join(domain_terms)
        system_prompt += (
            '\n\n## Diccionario de dominio\n\n'
            'El equipo utiliza los siguientes términos técnicos e internos. '
            'Si la transcripción contiene errores ortográficos o fonéticos '
            'similares a estos términos, debes usar la nomenclatura correcta '
            f'en tu resumen: {terms_list}.'
        )

    system_prompt += JSON_SCHEMA_INSTRUCTION

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

    return {
        'participants': data.get('participants') or ['Equipo'],
        'general_summary': data.get('general_summary', ''),
        'participant_blocks': [
            (block[0], block[1]) for block in data.get('participant_blocks', [])
            if isinstance(block, list) and len(block) == 2
        ],
        'key_points': data.get('key_points') or [],
        'actions': [
            (a[0], a[1]) for a in data.get('actions', [])
            if isinstance(a, list) and len(a) == 2
        ],
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
    parser.add_argument('--openai-model', default=os.environ.get('OPENAI_MODEL', 'phi3'))
    args = parser.parse_args()

    if not args.audio and not args.transcript_json:
        parser.error('either --audio or --transcript-json is required')

    transcript_path = Path(f'{args.output_prefix}-transcript.json')
    draft_path = Path(f'{args.output_prefix}.mml')

    if args.transcript_json:
        transcript = Path(args.transcript_json).read_text(encoding='utf-8')
    else:
        whisperx_python = BASE / '.venv311-diarization/bin/python'
        whisperx_script = BASE / 'scripts/transcribe_with_whisperx.py'
        if whisperx_python.exists() and whisperx_script.exists():
            result = run([str(whisperx_python), str(whisperx_script), args.audio, 'es'], check=False)
            if result.returncode == 0 and result.stdout.strip():
                transcript = result.stdout
            else:
                transcript = run(['python3', str(BASE / 'scripts/transcribe_audio.py'), args.audio, 'es']).stdout
        else:
            transcript = run(['python3', str(BASE / 'scripts/transcribe_audio.py'), args.audio, 'es']).stdout

    transcript_path.write_text(transcript)
    payload = json.loads(transcript)

    warnings = []
    raw_text = (payload.get('text') or '').strip()
    if len(raw_text) < 80:
        warnings.append('La transcripción es muy corta; el resumen puede ser incompleto.')

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
