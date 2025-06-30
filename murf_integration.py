import os
from typing import Optional
import streamlit as st
from murf import Murf

class MurfAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # The Murf SDK uses the environment variable for authentication
        os.environ["MURF_API_KEY"] = "ap2_263f3099-fed7-4143-9d9c-34f844878353"
        self.client = Murf()

    def text_to_speech(self, text: str, voice: str = "en-US-terrell") -> Optional[bytes]:
        """
        Convert text to speech using Murf's TTS API via SDK
        """
        try:
            audio_res = self.client.text_to_speech.generate(
                text=text,
                voice_id=voice
            )
            # audio_res.audio_file is a bytes object
            return audio_res.audio_file
        except Exception as e:
            st.error(f"Error in Murf TTS SDK: {str(e)}")
            return None

    def get_available_voices(self) -> list:
        """
        Get list of available voices from Murf API via SDK
        """
        try:
            voices = self.client.voices.list()
            st.write("Available voices from Murf API:")
            for v in voices:
                st.write(v)
            # Always ensure Samantha and Terrell voices are present
            required_voices = [
                {"id": "en-US-samantha", "name": "en-US-Samantha"},
                {"id": "en-US-terrell", "name": "en-US-Terrell"}
            ]
            # Remove any existing with same id to avoid duplicates, then add required
            existing_ids = {v['id'] for v in voices}
            voices = [v for v in voices if v['id'] not in {rv['id'] for rv in required_voices}]
            voices.extend(required_voices)
            return voices
        except Exception as e:
            # st.warning(f"Error in get_available_voices: {str(e)}. Using default voices.")æ
            return [
                {"id": "en-US-samantha", "name": "en-US-Samantha"},
                {"id": "en-US-terrell", "name": "en-US-Terrell"}
            ]
def get_murf_api():
    """Helper function to get or create Murf API instance"""
    return "ap2_263f3099-fed7-4143-9d9c-34f844878353"
