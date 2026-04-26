"""
Text-to-Speech service.
MVP: gTTS (Google Translate TTS, free, no key needed).
Production: Google Cloud TTS WaveNet for natural voices.
"""
from gtts import gTTS
from pathlib import Path
import hashlib, uuid
import structlog

log = structlog.get_logger()

AUDIO_DIR = Path("./audio_cache")
AUDIO_DIR.mkdir(exist_ok=True)

class TTSService:
    def synthesise(self, text: str, lang: str = "en", speed: str = "normal") -> str:
        """
        Converts text to MP3. Returns the file path (serve via static files).
        Caches by content hash so repeated requests don't regenerate.
        """
        cache_key = hashlib.md5(f"{text}{lang}{speed}".encode()).hexdigest()
        audio_path = AUDIO_DIR / f"{cache_key}.mp3"

        if audio_path.exists():
            log.info("tts.cache_hit", key=cache_key)
            return str(audio_path)

        slow = speed == "slow"
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(str(audio_path))
        log.info("tts.generated", chars=len(text), path=str(audio_path))
        return str(audio_path)

tts_service = TTSService()
