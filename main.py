"""
Jarvis Starter - v1 ($0 stack, push-to-talk)
Everything here runs locally and free:
  - faster-whisper       -> speech-to-text (local)
  - Ollama + a local LLM -> the "brain" (local, free, no API key)
  - pyttsx3              -> text-to-speech (local)

Loop:
  1. Hold SPACE to record your voice, release to stop.
  2. Audio is transcribed locally with faster-whisper.
  3. The transcript is sent to a local Ollama model, which can either
     reply in text or call a tool (like opening an app) defined in tools.py.
  4. Jarvis speaks the response back to you.

REQUIRES: Ollama installed and running, with a tool-calling model pulled.
See README.md for setup.

Run:
    python main.py
"""

import os
import sys
import glob
import tempfile

import keyboard          # pip install keyboard
import numpy as np        # pip install numpy
import sounddevice as sd  # pip install sounddevice
from scipy.io.wavfile import write as write_wav  # pip install scipy
import pyttsx3            # pip install pyttsx3

if sys.platform == "win32":
    nvidia_root = os.path.join(sys.prefix, "Lib", "site-packages", "nvidia")
    bin_dirs = glob.glob(os.path.join(nvidia_root, "*", "bin"))
    if bin_dirs:
        for bin_dir in bin_dirs:
            os.add_dll_directory(bin_dir)
            print(f"[Added DLL directory: {bin_dir}]")
    else:
        print(f"[No nvidia DLL folders found under: {nvidia_root}]")

from faster_whisper import WhisperModel  # pip install faster-whisper
import ollama              # pip install ollama

from tools import TOOL_DEFINITIONS, execute_tool
from personality import SYSTEM_PROMPT


RECORD_KEY = "space"
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024
WHISPER_MODEL_SIZE = "small"    
OLLAMA_MODEL = "qwen2.5:14b"     


try:
    whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cuda", compute_type="int8_float16")
    # Construction alone doesn't trigger the CUDA libraries - actually run a
    # tiny dummy transcription so a missing DLL fails now, not mid-conversation.
    _dummy_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
    list(whisper_model.transcribe(_dummy_audio)[0])
    print("[Using GPU for transcription]")
except Exception as e:
    print(f"[GPU transcription unavailable: {e}]")
    print("[Falling back to CPU]")
    whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
tts_engine = pyttsx3.init()

conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]


def speak(text: str):
    print(f"Jarvis: {text}")
    tts_engine.say(text)
    tts_engine.runAndWait()


def record_audio() -> str:
    """Records while RECORD_KEY is held down. Returns path to a temp WAV file."""
    print(f"[Listening... release {RECORD_KEY} to stop]")
    frames = []

    def callback(indata, _frames, _time_info, _status):
        frames.append(indata.copy())

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                             dtype="int16", callback=callback)
    with stream:
        while keyboard.is_pressed(RECORD_KEY):
            sd.sleep(50)

    audio = np.concatenate(frames, axis=0) if frames else np.zeros((0,), dtype="int16")

    tmp_path = os.path.join(tempfile.gettempdir(), "jarvis_input.wav")
    write_wav(tmp_path, SAMPLE_RATE, audio)

    return tmp_path


def transcribe(audio_path: str) -> str:
    segments, _ = whisper_model.transcribe(
        audio_path,
        language="en",       # skip auto-detect (unreliable on short clips)
        vad_filter=True,     # trims silence/noise, improves accuracy
    )
    text = " ".join(segment.text.strip() for segment in segments)
    return text.strip()


def ask_ollama(user_text: str) -> str:
    conversation_history.append({"role": "user", "content": user_text})

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=conversation_history,
        tools=TOOL_DEFINITIONS,
    )

    message = response["message"]


    if message.get("tool_calls"):
        conversation_history.append(message)
        for call in message["tool_calls"]:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            result = execute_tool(name, args)
            conversation_history.append({
                "role": "tool",
                "content": str(result),
            })

        follow_up = ollama.chat(model=OLLAMA_MODEL, messages=conversation_history)
        reply_text = follow_up["message"]["content"]
        conversation_history.append({"role": "assistant", "content": reply_text})
        return reply_text

    reply_text = message["content"]
    conversation_history.append({"role": "assistant", "content": reply_text})
    return reply_text


def main():
    speak("Systems online. Hold space and talk to me whenever you're ready.")
    while True:
        keyboard.wait(RECORD_KEY)  # blocks until pressed
        audio_path = record_audio()
        transcript = transcribe(audio_path)

        if not transcript:
            continue

        print(f"You: {transcript}")

        if transcript.lower().strip() in ("exit", "quit", "shut down", "goodbye"):
            speak("Shutting down. Talk soon.")
            break

        reply = ask_ollama(transcript)
        speak(reply)


if __name__ == "__main__":
    main()
