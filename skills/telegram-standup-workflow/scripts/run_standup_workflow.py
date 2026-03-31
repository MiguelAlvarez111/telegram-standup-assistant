#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from pathlib import Path


def run(cmd, check=True):
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def detect_participants(text):
    speaker_patterns = [
        ('Kelly', [r'mi nombre es\s+kelly', r'buenos d[ií]as, mi nombre es kelly']),
        ('Angie', [r'hola\s+angie', r'hola,?\s+soy\s+angie']),
        ('Astrid', [r'hola,?\s+soy\s+astrid', r'mi nombre es\s+astrid']),
        ('Miguel', [r'mi nombre es\s+miguel', r'buenos d[ií]as, mi nombre es miguel']),
    ]
    participants = []
    lowered = text.lower()
    for name, patterns in speaker_patterns:
        for pat in patterns:
            if re.search(pat, lowered, re.IGNORECASE):
                participants.append(name)
                break
    if re.search(r'primero, pues decirles que lo hicieron muy bien|dirigi[oó] muy bien el equipo', lowered, re.IGNORECASE):
        participants.append('Liderazgo del equipo')
    seen = []
    for p in participants:
        if p not in seen:
            seen.append(p)
    return seen


def split_fallback_blocks(text):
    markers = ['buenos días', 'el día de ayer', 'también el día de ayer', 'por acá', 'de resto', 'buen día']
    lowered = text.lower()
    positions = []
    for marker in markers:
        start = 0
        while True:
            idx = lowered.find(marker, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + len(marker)
    positions = sorted(set(positions))
    if len(positions) < 2:
        return []
    blocks = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        chunk = text[pos:end].strip()
        if len(chunk) > 80:
            blocks.append(chunk)
    return blocks[:4]


def speaker_blocks_from_segments(segments):
    blocks = []
    current_name = None
    current_text = []
    valid_names = {'Kelly', 'Angie', 'Astrid', 'Miguel', 'Brayan', 'Jose', 'José'}

    def flush():
        nonlocal current_name, current_text, blocks
        if current_text:
            label = current_name or '__UNKNOWN__'
            text = ' '.join(current_text).strip()
            if text:
                blocks.append((label, text))
        current_name = None
        current_text = []

    last_end = None
    for seg in segments:
        text = (seg.get('text') or '').strip()
        lower = text.lower()
        start = seg.get('start')
        if last_end is not None and start is not None and start - last_end > 2.0:
            flush()
        cue_name = None
        m = re.search(r'vamos con\s+([a-záéíóúñ]+)', lower, re.IGNORECASE)
        if m:
            candidate = m.group(1).capitalize()
            if candidate in valid_names:
                cue_name = candidate
        for pattern in [r'hola,?\s+soy\s+([a-záéíóúñ]+)', r'mi nombre es\s+([a-záéíóúñ]+)']:
            mm = re.search(pattern, lower, re.IGNORECASE)
            if mm:
                candidate = mm.group(1).capitalize()
                if candidate in valid_names:
                    cue_name = candidate
                    break
        if cue_name:
            flush()
            current_name = cue_name
            last_end = seg.get('end')
            continue
        if text:
            current_text.append(text)
        last_end = seg.get('end')
    flush()

    merged = []
    for label, text in blocks:
        lower = text.lower()
        if 'iniciamos' in lower and 'daily stand up' in lower and len(text) < 120:
            continue
        if ('lo hicieron muy bien' in lower or 'dirigió muy bien el equipo' in lower or 'equipo bastante funcional' in lower):
            label = 'Liderazgo del equipo'
        if label == '__UNKNOWN__' and merged and merged[-1][0] == '__UNKNOWN__':
            merged[-1] = ('__UNKNOWN__', merged[-1][1] + ' ' + text)
        else:
            merged.append((label, text))

    numbered = []
    unknown_count = 0
    for label, text in merged:
        if label == '__UNKNOWN__':
            unknown_count += 1
            label = f'Participante {unknown_count}'
        numbered.append((label, text))
    return [(name, text) for name, text in numbered if text]


DOMAIN_TERMS = ['USAP', 'NASSAU', 'RCMLinx', 'MD Web', 'MDClaim+', 'Providers']


def normalize_entities(text):
    replacements = {
        'ucp': 'USAP',
        'icp': 'USAP',
        'ycp': 'USAP',
        'nassau': 'NASSAU',
        'nasa': 'NASSAU',
        'ercienlinks': 'RCMLinx',
        'sien-links': 'RCMLinx',
        'mdweb': 'MD Web',
        'ndweb': 'MD Web',
    }
    out = text
    for old, new in replacements.items():
        out = re.sub(rf'\b{re.escape(old)}\b', new, out, flags=re.IGNORECASE)
    return out


def summarize_block(block_text, label):
    block_text = normalize_entities(block_text)
    lower_block = block_text.lower()

    bullets = []

    if 'reactiv' in lower_block:
        bullets.append('Trabajó casos o correos de reactivaciones.')
    if 'credencial' in lower_block:
        bullets.append('Apoyó con envío o validación de credenciales.')
    if 'base de datos' in lower_block:
        bullets.append('Dejó al menos un caso pendiente que requiere manejo por base de datos.')
    if 'cambiar el doctor' in lower_block or 'cambio del doctor' in lower_block or 'change the doctor' in lower_block:
        bullets.append('Escaló tickets relacionados con cambio de doctor y quedó a la espera de respuesta.')
    if 'reporte' in lower_block and 'no' in lower_block and ('llega' in lower_block or 'llegar' in lower_block):
        bullets.append('Mencionó seguimiento a un usuario al que no le estaba llegando un reporte.')
    if 'código de verificación' in lower_block:
        bullets.append('Atendió un caso de acceso donde fue necesario reenviar el código de verificación.')
    if 'bloquead' in lower_block or 'contraseña' in lower_block and 'intenta tres veces' in lower_block:
        bullets.append('Aclaró un supuesto bloqueo que en realidad correspondía a intentos fallidos de inicio de sesión.')
    if '%' in block_text or 'rcmlinx' in lower_block or 'md web' in lower_block:
        bullets.append('Expuso un problema técnico con contraseñas que incluyen % y diferencias entre RCMLinx y MD Web.')
    if 'task monitor' in lower_block or 'gris' in lower_block:
        bullets.append('Revisó un caso del task monitor que se quedaba en gris y no fue posible reproducir de forma estable.')
    if 'usap' in lower_block and 'pending' in lower_block:
        bullets.append('Aclaró que los tickets USAP en pending no deben tocarse porque USAP los procesa internamente.')
    if 'nassau' in lower_block:
        bullets.append('Dejó en seguimiento una consulta sobre el alcance del equipo frente a un caso relacionado con NASSAU.')
    if 'transactional lock' in lower_block or 'second report' in lower_block or 'segundo reporte' in lower_block:
        bullets.append('Dejó seguimiento operativo abierto sobre revisiones técnicas o reportes pendientes.')
    if label == 'Liderazgo del equipo' or 'lo hicieron muy bien' in lower_block or 'dirigió muy bien el equipo' in lower_block or 'equipo bastante funcional' in lower_block:
        return [
            'Reconoció el buen trabajo, la coordinación y la respuesta del equipo durante una semana complicada.',
            'Resaltó que el equipo respondió bien en medio de una semana caótica.',
            'Dejó retroalimentación positiva sobre el liderazgo y la forma de trabajo del grupo.'
        ]

    if not bullets:
        sentences = re.split(r'(?<=[.!?])\s+', block_text)
        for s in sentences:
            s = s.strip()
            if len(s) > 40:
                bullets.append(s[:180].rstrip('. ') + '.')
            if len(bullets) == 3:
                break

    if not bullets:
        bullets = [
            'Compartió actualización operativa del día anterior.',
            'Mencionó pendientes o bloqueos que requieren seguimiento.',
            'Dejó definido un próximo paso para hoy.'
        ]

    deduped = []
    seen = set()
    for bullet in bullets:
        if bullet not in seen:
            deduped.append(bullet)
            seen.add(bullet)
    return deduped[:3]


def extract_key_points_and_actions_from_blocks(blocks):
    blocks = [(label, normalize_entities(text)) for label, text in blocks]
    key_points = []
    actions = []
    seen_kp = set()
    seen_actions = set()

    def add_kp(text):
        if text not in seen_kp:
            key_points.append(text)
            seen_kp.add(text)

    def add_action(task, owner):
        key = (task, owner)
        if key not in seen_actions:
            actions.append((task, owner))
            seen_actions.add(key)

    for label, block_text in blocks:
        lower = block_text.lower()
        if 'reactiv' in lower or 'credencial' in lower:
            add_kp('Hubo seguimiento operativo a reactivaciones y credenciales.')
        if 'usap' in lower and 'pending' in lower:
            add_kp('Se aclaró que los tickets USAP en pending no deben tocarse porque USAP los procesa internamente.')
            add_action('Mantener la instrucción de no modificar tickets USAP en pending', label)
        if '%' in block_text or 'rcmlinx' in lower or 'md web' in lower:
            add_kp('Se revisó un problema de autenticación relacionado con contraseñas que contienen % entre RCMLinx y MD Web.')
            add_action('Dar seguimiento al ajuste técnico del problema de contraseñas con % entre RCMLinx y MD Web', label)
        if 'nassau' in lower:
            add_kp('Quedó pendiente definir el alcance del equipo frente a un caso consultado sobre NASSAU.')
            add_action('Confirmar el alcance del equipo frente al caso de NASSAU', label)
        if 'código de verificación' in lower or 'bloquead' in lower:
            add_kp('Se aclararon casos de acceso relacionados con códigos de verificación y supuestos bloqueos.')
        if '%' in block_text or 'task monitor' in lower or 'pending' in lower or 'nassau' in lower:
            add_kp('Se revisaron casos técnicos y operativos que requieren seguimiento adicional.')
            add_action('Dar seguimiento a los casos técnicos/operativos pendientes reportados en el standup', label)
        if 'facilit' in lower or 'sincroniz' in lower or 'domini' in lower:
            add_kp('Hubo seguimiento a creación/configuración pendiente y bloqueos asociados a sincronización o dominios.')
            add_action('Completar lo pendiente relacionado con facilities o configuración', label)
        if 'usuario' in lower and 'correo' in lower:
            add_kp('Se detectó un posible comportamiento incorrecto al recrear usuarios inactivos con el mismo correo.')
            add_action('Validar el posible conflicto por recreación de usuarios inactivos con el mismo correo', label)
        if 'tac' in lower or 'rechaz' in lower:
            add_kp('Se reportaron tickets rechazados que todavía requieren validación o respuesta externa.')
            add_action('Dar seguimiento a los tickets rechazados y esperar respuesta del área correspondiente', label)
        if 'datalinks' in lower or 'transactional' in lower or 'lock' in lower:
            add_kp('Se comunicaron cambios o validaciones sobre documentación, credenciales o Transactional Lock.')
        if 'cron' in lower or 'no visibles' in lower or 'no estaban visibles' in lower:
            add_kp('Se revisaron tickets que no estaban visibles y se aplicaron pasos de corrección o reproceso.')
            add_action('Confirmar si los tickets corregidos ya pueden ser trabajados normalmente por el equipo', label)
        if 'tipo anestesia' in lower or 'base de datos' in lower:
            add_kp('Quedó seguimiento abierto a un caso técnico que podría requerir intervención adicional de base de datos.')
            add_action('Hacer seguimiento al caso técnico pendiente para confirmar si requiere intervención adicional de base de datos', label)
        if 'lo hicieron muy bien' in lower or 'dirigió muy bien el equipo' in lower:
            add_kp('Se destacó el buen desempeño y coordinación del equipo durante una semana difícil.')

    if not key_points:
        key_points = [
            'Se compartieron avances operativos del día anterior.',
            'Se identificaron pendientes y bloqueos que requieren seguimiento.',
            'El equipo dejó definidos próximos pasos para hoy.'
        ]
    if not actions:
        actions = [('Revisar el resumen y confirmar próximos pasos operativos del día', 'Equipo')]
    return key_points, actions


def summarize_from_text(text, segments=None):
    detected = detect_participants(text)
    segment_blocks = speaker_blocks_from_segments(segments or []) if segments else []
    general = 'Reunión de seguimiento del equipo de Soporte con foco en avances operativos, validaciones, bloqueos y próximos pasos. El objetivo del resumen es dejar una versión clara y útil para quienes no asistieron al standup.'

    participant_blocks = []
    if segment_blocks:
        for label, block_text in segment_blocks[:4]:
            participant_blocks.append((label, summarize_block(block_text, label), block_text))
    else:
        raw_blocks = split_fallback_blocks(text)
        if raw_blocks:
            for i, block_text in enumerate(raw_blocks[:4], start=1):
                label = f'Participante {i}'
                participant_blocks.append((label, summarize_block(block_text, label), block_text))
        else:
            participant_blocks = [('Equipo', ['La transcripción no permitió separar con confianza todas las intervenciones.'], text)]

    participants = [name for name, _, _ in participant_blocks]

    for forced in detected:
        if forced == 'Liderazgo del equipo' and forced not in participants and re.search(r'primero, pues decirles que lo hicieron muy bien|dirigi[oó] muy bien el equipo', text.lower(), re.IGNORECASE):
            participant_blocks.append(('Liderazgo del equipo', summarize_block(text, 'Liderazgo del equipo'), text))
            participants.append('Liderazgo del equipo')

    key_points, actions = extract_key_points_and_actions_from_blocks([(name, block_text) for name, _, block_text in participant_blocks])

    return {
        'participants': participants or ['Equipo'],
        'general_summary': general,
        'participant_blocks': [(name, bullets) for name, bullets, _ in participant_blocks],
        'key_points': key_points,
        'actions': actions,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', required=True)
    parser.add_argument('--date', required=True)
    parser.add_argument('--output-prefix', required=True)
    parser.add_argument('--gmail-user')
    parser.add_argument('--gmail-app-password')
    parser.add_argument('--send', action='store_true')
    args = parser.parse_args()

    base = Path('/data/.openclaw/workspace/skills/telegram-standup-workflow')
    transcript_path = Path(f'{args.output_prefix}-transcript.json')
    draft_path = Path(f'{args.output_prefix}.mml')

    whisperx_python = base / '.venv311-diarization/bin/python'
    whisperx_script = base / 'scripts/transcribe_with_whisperx.py'
    used_whisperx = False
    if whisperx_python.exists() and whisperx_script.exists():
        transcribe_cmd = [str(whisperx_python), str(whisperx_script), args.audio, 'es']
        result = run(transcribe_cmd, check=False)
        if result.returncode == 0 and result.stdout.strip():
            transcript = result.stdout
            used_whisperx = True
        else:
            fallback_cmd = ['python3', str(base / 'scripts/transcribe_audio.py'), args.audio, 'es']
            transcript = run(fallback_cmd).stdout
    else:
        transcribe_cmd = ['python3', str(base / 'scripts/transcribe_audio.py'), args.audio, 'es']
        transcript = run(transcribe_cmd).stdout
    transcript_path.write_text(transcript)
    payload = json.loads(transcript)

    summary = summarize_from_text(payload.get('text', ''), payload.get('segments', []))

    build_cmd = [
        'python3', str(base / 'scripts/build_standup_mml.py'),
        '--template', str(base / 'references/standup-email-template.mml'),
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
            'python3', str(base / 'scripts/send_via_gmail_smtp.py'),
            '--mml', str(draft_path),
            '--gmail-user', args.gmail_user,
            '--gmail-app-password', args.gmail_app_password,
            '--to', args.gmail_user,
            '--subject', f'Standup Diario – {args.date}',
        ]
        run(send_cmd)

    print(json.dumps({
        'transcript_path': str(transcript_path),
        'draft_path': str(draft_path),
        'participants': summary['participants'],
        'sent': bool(args.send),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
