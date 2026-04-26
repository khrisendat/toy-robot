# Glossary

## Audio

**PCM (Pulse Code Modulation)**
The raw, uncompressed representation of digital audio. Each sample is a number representing the amplitude of the sound wave at a point in time. In this project audio is 16-bit PCM at 16,000 samples per second (16 kHz), mono. "16-bit" means each sample is an integer between -32,768 and 32,767. This is the format Vosk and webrtcvad expect.

**Sample rate (Hz)**
How many audio samples are recorded per second. 16,000 Hz (16 kHz) means 16,000 numbers per second. Higher sample rates capture higher frequencies. Human speech sits below 8 kHz, so 16 kHz captures everything needed for speech recognition.

**Downsampling**
Converting audio from a higher sample rate to a lower one. Browsers capture audio at 48 kHz (or 44.1 kHz); the server needs 16 kHz for Vosk. Each output sample is computed by averaging the corresponding input samples — this removes high-frequency content before discarding samples, preventing aliasing distortion.

**Aliasing**
Distortion introduced when you discard samples without first removing high-frequency content. High frequencies "fold back" into the speech band and become noise. Prevented by averaging (a simple low-pass filter) before decimating.

**WAV**
A container format for PCM audio. A WAV file is a short header (sample rate, channels, bit depth) followed by raw PCM bytes. Used internally because Python's `wave` module can read and write it without extra dependencies.

---

## Speech Processing

**VAD (Voice Activity Detection)**
Software that classifies each short frame of audio as "speech" or "silence". Used in `CommandRecorder` to detect when someone has finished speaking. The library used here is `webrtcvad` (Google's WebRTC VAD). It works on 30 ms frames and uses frequency-domain features — not just loudness — so it handles background noise better than a simple amplitude threshold.

**Wake word**
A specific phrase used to activate a voice assistant ("hey robot"). The system listens continuously for this phrase and only starts recording a command after it is detected. In this project wake word detection is handled by Vosk using a restricted grammar of just `["hey", "robot", "[unk]"]`.

**STT (Speech-to-Text)**
Converts recorded audio into a text transcript. The robot sends the user's command audio to a remote STT service which returns the words spoken. The transcript is then passed to the LLM.

**TTS (Text-to-Speech)**
Converts text into audio. The robot uses Piper on the Raspberry Pi and macOS `say` on Mac. The generated WAV is sent to the browser for playback.

---

## Vosk

**Vosk**
An offline speech recognition library. Unlike cloud STT, Vosk runs entirely on-device using a pre-downloaded acoustic model. Used here for wake word detection because it can run continuously at low CPU cost and does not require an internet connection.

**KaldiRecognizer**
The Vosk class that processes audio. Accepts PCM in chunks via `AcceptWaveform()`. Returns partial results (in-progress transcription) and final results (committed transcription after a pause). Configured with a restricted grammar so it only looks for the wake word vocabulary.

**Restricted grammar**
Telling Vosk to only recognise specific words (e.g. `["hey", "robot", "[unk]"]`). This improves accuracy and speed for wake word detection because the decoder does not search the full English vocabulary. `[unk]` is a catch-all for anything that doesn't match.

---

## Architecture

**WebSocket**
A persistent, full-duplex connection between the browser and server. Used instead of HTTP requests so the server can push state updates and audio back to the browser at any time without the browser polling.

**LLM (Large Language Model)**
The AI model that generates the robot's responses. This project uses Google Gemini 2.5 Flash via the Gemini API. The model receives the conversation history and the user's latest message and streams a response sentence by sentence.

**Streaming response**
Instead of waiting for the full LLM response before speaking, the server sends sentences to the browser as they are generated. This reduces perceived latency — the robot starts speaking the first sentence while the LLM is still generating the rest.
