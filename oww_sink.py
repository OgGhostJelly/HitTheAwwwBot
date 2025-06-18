import asyncio
from asyncio import Future
from collections import defaultdict
from queue import Queue
from typing import Awaitable, TypeVar
import numpy as np  
from openwakeword import Model
from scipy import signal
from discord.ext.voice_recv.sinks import AudioSink
import sounddevice as sd

T = TypeVar('T')

class OpenWakeWordSink(AudioSink):  
    def __init__(self, pred_cb, enable_playback=False, **kwargs):  
        super().__init__()
        self.pred_cb = pred_cb
        self._stream_data = defaultdict(lambda: _StreamData(model=Model(**kwargs)))
        self._enable_playback = enable_playback  
        
        if enable_playback:  
            self.playback_buffer = Queue(maxsize=10)  # Limit buffer size  
            self.stream = sd.OutputStream(  
                samplerate=16000,  
                channels=1,
                dtype=np.int16,  
                callback=self._audio_callback,  
                blocksize=1280  # Match OpenWakeWord chunk size  
            )  
            self.stream.start()  
          
    def wants_opus(self) -> bool:
        return False

    def _audio_callback(self, outdata, frames, time, status):  
        """Continuous audio stream callback"""  
        try:  
            if not self.playback_buffer.empty():  
                chunk = self.playback_buffer.get_nowait()  
                if len(chunk) == frames:  
                    outdata[:] = chunk.reshape(-1, 1)  
                else:  
                    # Handle size mismatch  
                    outdata[:] = 0  
            else:  
                # Play silence when no data available  
                outdata[:] = 0  
        except:  
            outdata[:] = 0  
      
    def write(self, user, data):
        if user is None:  
            return  
        
        # Process audio chunks
        chunks = self._stream_data[user.id].add_voice_data(data)  
        
        for chunk in chunks:  
            try:  
                predictions = self._stream_data[user.id].model.predict(chunk)
                self.pred_cb(user, predictions)
                
                # Queue chunk for playback (non-blocking)  
                if self._enable_playback:  
                    try:  
                        self.playback_buffer.put_nowait(chunk)  
                    except:  
                        pass  # Buffer full, skip this chunk  
                          
            except Exception as e:  
                print(f"OpenWakeWord error: {e}")  
      
    def _await(self, coro: Awaitable[T]) -> Future[T]:
        assert self.client is not None
        return asyncio.run_coroutine_threadsafe(coro, self.client.loop)  # type: ignore

    def cleanup(self):
        """Clean up resources when sink is no longer needed"""  
        self._stream_data.clear()  
        if hasattr(self, 'stream'):  
            self.stream.stop()  
            self.stream.close()

class AsyncOpenWakeWordSink(OpenWakeWordSink):
    def __init__(self, async_pred_cb=None, **kwargs):  
        self.async_pred_cb = async_pred_cb  
        super().__init__(pred_cb=self._sync_text_wrapper, **kwargs)  
    
    def _sync_text_wrapper(self, user, text):  
        if self.async_pred_cb:  
            self._await(self.async_pred_cb(user, text))

class _StreamData:
    def __init__(self, model: Model, target_chunk_size=1280):
        self.model = model
        self.target_chunk_size = target_chunk_size
        self.buffer = np.array([], dtype=np.float32) 
          
    def add_voice_data(self, voice_data):  
        """Add VoiceData and return chunks ready for OpenWakeWord"""  
        if not voice_data.pcm:  
            return []  
              
        # Convert Discord PCM (48kHz stereo) to OpenWakeWord format (16kHz mono)  
        pcm_array = np.frombuffer(voice_data.pcm, dtype=np.int16)  
          
        if len(pcm_array) == 0:  
            return []  
              
        # Convert stereo to mono  
        if len(pcm_array) % 2 == 0:  
            pcm_stereo = pcm_array.reshape(-1, 2)  
            pcm_mono = np.mean(pcm_stereo, axis=1)  
        else:  
            pcm_mono = pcm_array[:-1].reshape(-1, 2).mean(axis=1) if len(pcm_array) > 1 else pcm_array  
          
        # Resample from 48kHz to 16kHz  
        if len(pcm_mono) > 0:  
            num_samples_new = int(len(pcm_mono) * 16000 / 48000)  
            pcm_16khz = signal.resample(pcm_mono, num_samples_new)  
        else:  
            return []  
          
        # Add to buffer  
        self.buffer = np.concatenate([self.buffer, pcm_16khz])  
          
        # Extract complete chunks  
        chunks = []  
        while len(self.buffer) >= self.target_chunk_size:  
            chunk = self.buffer[:self.target_chunk_size]  
            chunks.append(chunk)  
            self.buffer = self.buffer[self.target_chunk_size:]  
              
        return chunks