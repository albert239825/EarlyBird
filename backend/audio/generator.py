#!/usr/bin/env python3

import os
import re
import sys
import uuid
from pydub import AudioSegment
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs


class PodcastAudioGenerator:
    def __init__(self, output_dir=None):
        self.ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
        if not self.ELEVENLABS_API_KEY:
            raise ValueError("Please set the ELEVENLABS_API_KEY environment variable.")

        # Map speaker names to voice IDs
        self.SPEAKER_VOICES = {
            "host": "9BWtsMINqrJLrRacOk9x",  # Aria
            "expert": "CwhRBWXzGAHq8TQ4Fs17",  # Roger
        }

        # Initialize the ElevenLabs client
        self.client = ElevenLabs(api_key=self.ELEVENLABS_API_KEY)

        # Use the provided output directory or default to the audio_files directory
        if output_dir:
            self.audio_dir = output_dir
        else:
            # Fallback to the default directory
            self.podcast_dir = os.path.join(
                self.project_root,
                "backend",
                "podcast",
                "finished_podcasts",
            )

        os.makedirs(self.audio_dir, exist_ok=True)

    def text_to_speech_file(self, text: str, voice_id: str) -> str:
        """Converts text to speech using ElevenLabs with the specified voice, saves to an MP3 file."""
        response = self.client.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_22050_32",
            text=text,
            #model_id="eleven_multilingual_v2",  # high quality model
            model_id="eleven_flash_v2_5",  # Low latency model
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.5,
                style=0.0,
                use_speaker_boost=True,
            ),
        )
        temp_file_path = os.path.join(self.audio_dir, f"{uuid.uuid4()}.mp3")
        with open(temp_file_path, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)
        return temp_file_path

    def generate_audio(self, script: str) -> list:
        """
        Generates audio from a script with XML-like tags.
        Returns a list of paths to the generated audio files.
        """
        # Split by numbered tags and process each section
        interaction_files = []
        parts = re.findall(r"<(host|expert)(\d+)>\s*(.*?)\s*</\1\2>", script, re.DOTALL | re.IGNORECASE)

        if not parts:
            raise ValueError("No valid script sections found")

        try:
            interaction_count = 0
            for i in range(0, len(parts), 2):  # Process pairs of host/expert
                interaction_count += 1
                interaction_clips = []
                
                # Process both host and expert for this interaction
                for j in range(i, min(i+2, len(parts))):
                    speaker, number, text = parts[j]
                    speaker = speaker.lower()  # Convert to lowercase
                    voice_id = self.SPEAKER_VOICES.get(speaker, self.SPEAKER_VOICES["host"])
                    mp3_path = self.text_to_speech_file(text, voice_id)
                    interaction_clips.append(mp3_path)

                # Combine interaction clips
                final_audio = AudioSegment.empty()
                for clip in interaction_clips:
                    final_audio += AudioSegment.from_mp3(clip)
                    os.remove(clip)  # Clean up temporary files

                # Save individual interaction file
                output_file = os.path.join(self.audio_dir, f"interaction_{interaction_count}.mp3")
                final_audio.export(output_file, format="mp3")
                interaction_files.append(output_file)
                print(f"Saved interaction {interaction_count} to {output_file}")

            return interaction_files

        except Exception as e:
            # Clean up any temporary files in case of error
            for clip in interaction_clips:
                if os.path.exists(clip):
                    os.remove(clip)
            raise e

    def generate_interrupt_response(self, interrupt_response: str, output_path: str) -> str:
        """
        Generates audio for an interrupt response and saves it to the specified path.
        
        Args:
            interrupt_response (str): The text to convert to speech
            output_path (str): Path where the audio file should be saved
            
        Returns:
            str: Path to the generated audio file
        """
        # Ensure the directory exists (not the file path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Generate the audio using the expert voice
        voice_id = self.SPEAKER_VOICES["expert"]
        temp_path = self.text_to_speech_file(interrupt_response, voice_id)
        
        # Load and save the audio to the destination
        audio = AudioSegment.from_mp3(temp_path)
        audio.export(output_path, format="mp3")
        
        # Clean up temporary file
        os.remove(temp_path)
        
        return output_path


if __name__ == "__main__":
    # Example usage
    generator = PodcastAudioGenerator()
    script = """
    <HOST>Welcome to our podcast!</HOST>
    <EXPERT>Thank you for having me.</EXPERT>
    """
    generator.generate_audio(script)
