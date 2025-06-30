import os
from typing import Optional
import streamlit as st
from murf import Murf

class MurfAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            # Initialize Murf client with API key directly
            self.client = Murf(api_key=api_key)
        except Exception as e:
            st.error(f"Failed to initialize Murf client: {str(e)}")
            raise

    def text_to_speech(self, text: str, voice: str = "en-US-terrell") -> Optional[bytes]:
        """
        Convert text to speech using Murf's TTS API via SDK
        """
        try:
            # Validate input
            if not text or not text.strip():
                return None
                
            # Truncate text if too long (Murf has character limits)
            max_length = 3000
            if len(text) > max_length:
                text = text[:max_length]
                # Try to find a good break point
                if '. ' in text[-200:]:
                    last_sentence = text.rfind('. ') + 1
                    if last_sentence > max_length - 200:
                        text = text[:last_sentence]
            
            # Generate audio
            audio_res = self.client.text_to_speech.generate(
                text=text.strip(),
                voice_id=voice
            )
            
            # Check if audio_res has audio_file attribute
            if hasattr(audio_res, 'audio_file') and audio_res.audio_file:
                audio_data = audio_res.audio_file
                
                # Ensure we return bytes
                if isinstance(audio_data, bytes):
                    return audio_data
                elif isinstance(audio_data, str):
                    # If it's a URL, download it
                    if audio_data.startswith('http'):
                        import requests
                        try:
                            response = requests.get(audio_data, timeout=30)
                            response.raise_for_status()
                            return response.content
                        except requests.RequestException as e:
                            st.error(f"Failed to download audio: {str(e)}")
                            return None
                    else:
                        # Try to decode as base64
                        try:
                            import base64
                            return base64.b64decode(audio_data)
                        except Exception:
                            # Last resort: encode as UTF-8
                            return audio_data.encode('utf-8')
                else:
                    return bytes(audio_data) if audio_data else None
            else:
                return None
                
        except Exception as e:
            # Only show error in debug mode or if specifically requested
            if hasattr(st.session_state, 'debug_mode') and st.session_state.debug_mode:
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
    api_key = "ap2_263f3099-fed7-4143-9d9c-34f844878353"
    try:
        return MurfAPI(api_key)
    except Exception as e:
        st.error(f"Failed to initialize Murf API: {str(e)}")
        return None
