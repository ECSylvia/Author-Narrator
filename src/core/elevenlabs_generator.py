import os
import re
import subprocess
import tempfile
from elevenlabs.client import ElevenLabs
from elevenlabs import save

MAX_CHUNK_CHARS = 4500
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB (ElevenLabs limit is 11 MB)


def _compress_for_upload(wav_path):
    """Compress a WAV to MP3 if it exceeds the upload size limit.

    Returns (file_path, is_temp) — caller must delete temp files.
    """
    if os.path.getsize(wav_path) <= MAX_UPLOAD_BYTES:
        return wav_path, False

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-ar", "44100", "-ac", "1",
             "-b:a", "128k", tmp.name],
            check=True, capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        os.unlink(tmp.name)
        raise RuntimeError(
            f"Failed to compress voice sample (ffmpeg required): {e}"
        )
    return tmp.name, True

COST_PER_1K_CHARS = 0.30


def estimate_cost(text):
    """Return estimated ElevenLabs API cost in USD for the given text."""
    return (len(text) / 1000) * COST_PER_1K_CHARS


def estimate_cost_for_chapters(chapters):
    """Return (total_chars, total_cost) for a list of Chapter objects."""
    total = sum(len(ch.content) for ch in chapters)
    return total, (total / 1000) * COST_PER_1K_CHARS


def _split_text_into_chunks(text, max_chars=MAX_CHUNK_CHARS):
    """Split text into chunks that respect sentence boundaries."""
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 > max_chars:
            if current:
                chunks.append(current.strip())
            if len(sentence) > max_chars:
                for i in range(0, len(sentence), max_chars):
                    chunks.append(sentence[i:i + max_chars])
                current = ""
            else:
                current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks


class ElevenLabsGenerator:
    def __init__(self, api_key):
        self.client = ElevenLabs(api_key=api_key)
        self._voice_id_cache = {}

    def _resolve_voice(self, voice_name, sample_path=None):
        """Find or create a voice via Instant Voice Clone, returning its ID."""
        if voice_name in self._voice_id_cache:
            return self._voice_id_cache[voice_name]

        voices = self.client.voices.get_all()
        for v in voices.voices:
            if v.name == voice_name:
                self._voice_id_cache[voice_name] = v.voice_id
                return v.voice_id

        if not sample_path or not os.path.exists(sample_path):
            raise FileNotFoundError("Voice sample not found. Please record a sample first.")

        upload_path, is_temp = _compress_for_upload(sample_path)
        try:
            with open(upload_path, "rb") as f:
                voice = self.client.voices.ivc.create(
                    name=voice_name,
                    files=[f],
                    description="Author Narrator Clone",
                )
        finally:
            if is_temp:
                os.unlink(upload_path)

        self._voice_id_cache[voice_name] = voice.voice_id
        return voice.voice_id

    def _tts(self, text, voice_id, output_path):
        """Run TTS for a single chunk and save the result."""
        audio = self.client.text_to_speech.convert(
            voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        save(audio, output_path)

    def generate_cloned_speech(self, text, voice_name, sample_path, output_path):
        """Generate speech for a short text snippet and save to output_path."""
        try:
            voice_id = self._resolve_voice(voice_name, sample_path)
            self._tts(text, voice_id, output_path)
            return True
        except Exception as e:
            raise Exception(f"ElevenLabs Error: {str(e)}")

    def generate_chapter_audio(self, text, voice_name, sample_path, output_path,
                               on_chunk_progress=None):
        """Generate audio for a full chapter, splitting into chunks if needed.

        on_chunk_progress(current_chunk, total_chunks) is called after each chunk.
        Intermediate chunk files are concatenated into the final output_path.
        """
        voice_id = self._resolve_voice(voice_name, sample_path)
        chunks = _split_text_into_chunks(text)
        total = len(chunks)

        if total == 1:
            self._tts(chunks[0], voice_id, output_path)
            if on_chunk_progress:
                on_chunk_progress(1, 1)
            return

        chunk_files = []
        base, ext = os.path.splitext(output_path)
        try:
            for i, chunk_text in enumerate(chunks):
                chunk_path = f"{base}_chunk{i}{ext}"
                self._tts(chunk_text, voice_id, output_path=chunk_path)
                chunk_files.append(chunk_path)
                if on_chunk_progress:
                    on_chunk_progress(i + 1, total)

            _concatenate_mp3(chunk_files, output_path)
        finally:
            for cf in chunk_files:
                try:
                    os.remove(cf)
                except OSError:
                    pass


def _concatenate_mp3(file_list, output_path):
    """Simple binary concatenation of MP3 files."""
    with open(output_path, "wb") as out:
        for fpath in file_list:
            with open(fpath, "rb") as inp:
                out.write(inp.read())
