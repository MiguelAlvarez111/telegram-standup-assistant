import json
import sys
import whisperx

audio_file = sys.argv[1]
device = 'cpu'
batch_size = 4
compute_type = 'int8'
model = whisperx.load_model('small', device, compute_type=compute_type, language='es')
audio = whisperx.load_audio(audio_file)
result = model.transcribe(audio, batch_size=batch_size)
model_a, metadata = whisperx.load_align_model(language_code=result['language'], device=device)
result = whisperx.align(result['segments'], model_a, metadata, audio, device, return_char_alignments=False)
print(json.dumps({'language': result.get('language'), 'segments': result.get('segments', [])[:20]}, ensure_ascii=False, indent=2))
