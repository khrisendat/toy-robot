from google.cloud import texttospeech
import os

class Speaker:
    def __init__(self):
        self.client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

    def say(self, text):
        synthesis_input = texttospeech.SynthesisInput(text=text)
        try:
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=self.voice, audio_config=self.audio_config
            )

            # For simplicity, we'll write to a temp file and play it.
            with open("output.mp3", "wb") as out:
                out.write(response.audio_content)

            # Play the audio file using mpg123
            os.system("mpg123 -q output.mp3")

        except Exception as e:
            print(f"Error during text-to-speech synthesis or playback: {e}")
            # Fallback to printing the message if TTS fails
            print(f"Speaking (fallback): {text}")

