from elevenlabs import ElevenLabs
import os

client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY")
)

voices = client.voices.get_all()

# Print to console and save to file
with open('available_voices.txt', 'w') as f:
    for voice in voices.voices:
        f.write(str(voice) + '\n')

