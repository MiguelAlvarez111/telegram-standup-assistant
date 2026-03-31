#!/usr/bin/env python3
import json
import os
import sys
from faster_whisper import WhisperModel


def main():
    if len(sys.argv) < 2:
        print('Usage: transcribe_audio.py <audio_path> [language]', file=sys.stderr)
        sys.exit(1)
    audio_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else 'es'
    model_name = os.getenv('WHISPER_MODEL', 'base')
    model = WhisperModel(model_name, device='cpu', compute_type='int8')
    segments, info = model.transcribe(audio_path, language=language, vad_filter=True)
    text_parts = []
    segs = []
    for s in segments:
        piece = s.text.strip()
        if piece:
            text_parts.append(piece)
        segs.append({'start': s.start, 'end': s.end, 'text': s.text})
    print(json.dumps({'language': info.language, 'duration': info.duration, 'text': ' '.join(text_parts).strip(), 'segments': segs}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
