#!/usr/bin/env python3
import json
import sys
import io
import contextlib
import whisperx


def main():
    if len(sys.argv) < 2:
        print('Usage: transcribe_with_whisperx.py <audio_path> [language]', file=sys.stderr)
        raise SystemExit(1)
    audio_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else 'es'
    device = 'cpu'
    compute_type = 'int8'
    log_buffer = io.StringIO()
    with contextlib.redirect_stdout(log_buffer):
        model = whisperx.load_model('small', device, compute_type=compute_type, language=language)
        audio = whisperx.load_audio(audio_path)
        result = model.transcribe(audio, batch_size=4)
        model_a, metadata = whisperx.load_align_model(language_code=result['language'], device=device)
        result = whisperx.align(result['segments'], model_a, metadata, audio, device, return_char_alignments=False)
    text = ' '.join(seg.get('text', '').strip() for seg in result.get('segments', []) if seg.get('text'))
    print(json.dumps({
        'language': result.get('language'),
        'duration': None,
        'text': text.strip(),
        'segments': result.get('segments', [])
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
