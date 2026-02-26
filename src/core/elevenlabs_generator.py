import os
from elevenlabs.client import ElevenLabs
from elevenlabs import save

class ElevenLabsGenerator:
    def __init__(self, api_key):
        self.client = ElevenLabs(api_key=api_key)

    def generate_cloned_speech(self, text, voice_name, sample_path, output_path):
        """
        1. Checks if a voice with 'voice_name' already exists.
        2. If not, creates it using 'sample_path'.
        3. Generates audio for 'text'.
        4. Saves to 'output_path'.
        """
        
        # 1. Check existing voices
        try:
            voices = self.client.voices.get_all()
            voice_id = None
            
            for v in voices.voices:
                if v.name == voice_name:
                    voice_id = v.voice_id
                    break
            
            # 2. Create if missing
            if not voice_id:
                if not os.path.exists(sample_path):
                    raise FileNotFoundError("Voice sample not found. Please record a sample first.")
                
                # Create the voice
                # Note: 'files' argument expects open file handles or paths
                # The SDK usually takes a list of paths/files
                # Verify exact signature for latest SDK, assuming v3+ style
                try: 
                    # Assuming we can pass the file path directly or open it
                    with open(sample_path, "rb") as f:
                        voice = self.client.voices.add(
                            name=voice_name,
                            description="Author Narrator Clone",
                            files=[sample_path] # The SDK handles path strings usually, or verify
                        )
                    voice_id = voice.voice_id
                except Exception as e:
                     raise Exception(f"Failed to clone voice: {str(e)}")

            # 3. Generate Audio
            audio = self.client.generate(
                text=text,
                voice=voice_id,
                model="eleven_monolingual_v1"
            )
            
            # 4. Save
            save(audio, output_path)
            return True

        except Exception as e:
            raise Exception(f"ElevenLabs Error: {str(e)}")
