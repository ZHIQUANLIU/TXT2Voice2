import asyncio
import os
import re
from PyQt6.QtCore import QThread, pyqtSignal
from .tts_providers import (EdgeTTSProvider, OpenAITTSProvider, 
                             GoogleTTSProvider, LocalTTSProvider, DashScopeTTSProvider)

class AudioWorker(QThread):
    progress = pyqtSignal(int, str)  # percentage, message
    finished = pyqtSignal(list)      # list of output paths
    error = pyqtSignal(str)

    def __init__(self, provider_type, segments, voice, output_dir, config_manager, filename_prefix):
        super().__init__()
        self.provider_type = provider_type
        self.segments = segments # list of (title, body)
        self.voice = voice
        self.output_dir = output_dir
        self.config_manager = config_manager
        self.filename_prefix = filename_prefix
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        asyncio.run(self._process())

    async def _process(self):
        provider = self._get_provider()
        if not provider:
            self.error.emit(f"Failed to initialize provider: {self.provider_type}")
            return

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

        output_files = []
        total_segments = len(self.segments)
        
        for i, (title, body) in enumerate(self.segments):
            if not self.is_running:
                break
            
            self.progress.emit(int((i / total_segments) * 100), f"Processing: {title}")
            
            # Chunking body for provider limits (e.g. OpenAI 4096 chars)
            chunks = self._chunk_text(body, max_chars=3000)
            
            # Safe filename
            safe_title = self._safe_filename(title)
            # [Filename]_[Engine]_[Voice]_c[ChapterID]_[Title].mp3
            file_name = f"{self.filename_prefix}_{self.provider_type}_{self.voice}_c{i+1:03d}_{safe_title}.mp3"
            if total_segments == 1:
                file_name = f"{self.filename_prefix}_{self.provider_type}_{self.voice}.mp3"
            
            output_path = os.path.join(self.output_dir, file_name)
            
            # Synthesize chunks and merge (or save directly if possible)
            # For simplicity, we'll synthesize each chunk and combine bytes
            all_audio_data = b""
            # temp files could be used, but since we are merging, we can just cat bytes if provider allows
            # actually our providers save to file directly. We need a way to merge.
            # I'll modify providers or use a temporary buffer.
            
            # For now, let's just save one file per segment (chapter)
            # If a chapter is too long, we need to split it internally and merge.
            
            current_chapter_success = True
            temp_files = []
            
            for j, chunk in enumerate(chunks):
                if not self.is_running:
                    break
                
                chunk_output = output_path if len(chunks) == 1 else f"{output_path}.part{j}.mp3"
                success = await provider.synthesize(chunk, self.voice, chunk_output)
                
                if success:
                    if len(chunks) > 1:
                        temp_files.append(chunk_output)
                else:
                    current_chapter_success = False
                    break
            
            if current_chapter_success:
                if len(chunks) > 1:
                    # Merge temp files
                    with open(output_path, "wb") as outfile:
                        for f in temp_files:
                            with open(f, "rb") as infile:
                                outfile.write(infile.read())
                            os.remove(f)
                output_files.append(output_path)
            else:
                self.error.emit(f"Failed to synthesize: {title}")
                return

        self.progress.emit(100, "Finished")
        self.finished.emit(output_files)

    def _get_provider(self):
        if self.provider_type == "Edge":
            return EdgeTTSProvider()
        elif self.provider_type == "OpenAI":
            api_key = self.config_manager.get_api_key("OpenAI")
            return OpenAITTSProvider(api_key)
        elif self.provider_type == "Google":
            creds = self.config_manager.get_setting("google_creds_path")
            return GoogleTTSProvider(creds)
        elif self.provider_type == "DashScope":
            api_key = self.config_manager.get_api_key("DashScope")
            return DashScopeTTSProvider(api_key)
        elif self.provider_type == "Local":
            return LocalTTSProvider()
        return None

    def _chunk_text(self, text, max_chars=3000):
        # Simple chunking by paragraph or sentence
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        while text:
            if len(text) <= max_chars:
                chunks.append(text)
                break
            
            # Try to find a good split point
            split_at = text.rfind("\n", 0, max_chars)
            if split_at == -1:
                split_at = text.rfind(". ", 0, max_chars)
            if split_at == -1:
                split_at = max_chars
            
            chunks.append(text[:split_at].strip())
            text = text[split_at:].strip()
        return chunks

    def _safe_filename(self, s):
        s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s.strip())
        return s.replace(" ", "_")[:30]
