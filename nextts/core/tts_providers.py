import abc
import asyncio
import os
import edge_tts
from openai import OpenAI
from google.cloud import texttospeech
import pyttsx3
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

class BaseTTSProvider(abc.ABC):
    """Abstract base class for all TTS providers."""
    
    @abc.abstractmethod
    async def synthesize(self, text: str, voice: str, output_path: str, **kwargs) -> bool:
        """Synthesize text to an audio file."""
        pass

    @abc.abstractmethod
    async def get_voices(self) -> list:
        """Return a list of available voices. Each voice should be a dict with 'id' and 'name'."""
        pass

class EdgeTTSProvider(BaseTTSProvider):
    async def synthesize(self, text: str, voice: str, output_path: str, **kwargs) -> bool:
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return True
        except Exception as e:
            print(f"Edge TTS Error: {e}")
            return False

    async def get_voices(self) -> list:
        try:
            voices = await edge_tts.VoicesManager.create()
            v_list = voices.find(Locale="zh-CN") + voices.find(Locale="en-US")
            return [{"id": v["ShortName"], "name": f"{v['FriendlyName']} ({v['Gender']})"} for v in v_list]
        except:
            return []

class OpenAITTSProvider(BaseTTSProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key) if api_key else None

    async def synthesize(self, text: str, voice: str, output_path: str, **kwargs) -> bool:
        if not self.client: return False
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text
                )
            )
            response.stream_to_file(output_path)
            return True
        except Exception as e:
            print(f"OpenAI TTS Error: {e}")
            return False

    async def get_voices(self) -> list:
        voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        return [{"id": v, "name": v.capitalize()} for v in voices]

class GoogleTTSProvider(BaseTTSProvider):
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self.client = None
        if credentials_path and os.path.exists(credentials_path):
            try:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
                self.client = texttospeech.TextToSpeechClient()
            except Exception as e:
                print(f"Google Client Init Error: {e}")

    async def synthesize(self, text: str, voice: str, output_path: str, **kwargs) -> bool:
        if not self.client: return False
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            lang_code = "-".join(voice.split("-")[:2])
            voice_params = texttospeech.VoiceSelectionParams(language_code=lang_code, name=voice)
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.synthesize_speech(
                    input=synthesis_input, voice=voice_params, audio_config=audio_config
                )
            )
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
            return True
        except Exception as e:
            print(f"Google TTS Error: {e}")
            return False

    async def get_voices(self) -> list:
        if not self.client: return []
        try:
            loop = asyncio.get_event_loop()
            voices = await loop.run_in_executor(None, self.client.list_voices)
            # Filter for common languages to keep list manageable
            results = []
            for v in voices.voices:
                if any(lang.startswith(("en-", "zh-")) for lang in v.language_codes):
                    results.append({"id": v.name, "name": f"{v.name} ({v.ssml_gender.name})"})
            return results
        except Exception as e:
            print(f"Google List Voices Error: {e}")
            return []

class DashScopeTTSProvider(BaseTTSProvider):
    """Alibaba Cloud DashScope (Qwen/CosyVoice) provider."""
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def synthesize(self, text: str, voice: str, output_path: str, **kwargs) -> bool:
        if not self.api_key: return False
        try:
            dashscope.api_key = self.api_key
            loop = asyncio.get_event_loop()
            
            def _call():
                synthesizer = SpeechSynthesizer(model="cosyvoice-v1", voice=voice)
                audio = synthesizer.call(text)
                with open(output_path, 'wb') as f:
                    f.write(audio)
            
            await loop.run_in_executor(None, _call)
            return True
        except Exception as e:
            print(f"DashScope Error: {e}")
            return False

    async def get_voices(self) -> list:
        # These are common CosyVoice/DashScope voices
        v_list = [
            ("tongxiaoxia", "晓晓 (Female)"),
            ("tongyaoyao", "瑶瑶 (Female)"),
            ("guijia", "桂家 (Male)"),
            ("loongstella", "Stella (Female)"),
            ("loongbella", "Bella (Female)"),
        ]
        return [{"id": v[0], "name": v[1]} for v in v_list]

class LocalTTSProvider(BaseTTSProvider):
    def __init__(self):
        # Initialize engine on creation, but we'll need to handle threading carefully
        pass

    async def synthesize(self, text: str, voice: str, output_path: str, **kwargs) -> bool:
        try:
            loop = asyncio.get_event_loop()
            def _save():
                # Re-init in each thread to avoid COM/Event loop issues
                engine = pyttsx3.init()
                if voice:
                    engine.setProperty('voice', voice)
                engine.save_to_file(text, output_path)
                engine.runAndWait()
                # Clean up or ignore? pyttsx3 doesn't have a clear close()
            
            await loop.run_in_executor(None, _save)
            return True
        except Exception as e:
            print(f"Local TTS Error: {e}")
            return False

    async def get_voices(self) -> list:
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            return [{"id": v.id, "name": v.name} for v in voices]
        except:
            return []
