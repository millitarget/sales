"""
Twilio Client for Cold Calling Automation System
Handles actual telephony operations via Twilio
"""

import os
import logging
from typing import Dict, Any, Optional
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Dial, Stream
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv('.env.local')

logger = logging.getLogger(__name__)

class TwilioClient:
    """Twilio client for telephony operations"""
    
    def __init__(self):
        """Initialize Twilio client"""
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.webhook_base_url = os.getenv('WEBHOOK_BASE_URL', 'http://localhost:5000')
        
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            raise ValueError("TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER must be set")
        
        self.client = Client(self.account_sid, self.auth_token)
        logger.info("Twilio client initialized")
    
    def make_call(self, to_number: str, call_id: str, livekit_room_name: str) -> str:
        """
        Initiate an outbound call
        
        Args:
            to_number: Phone number to call
            call_id: Internal call ID for tracking
            livekit_room_name: LiveKit room name for the call
            
        Returns:
            Twilio call SID
        """
        try:
            # TwiML endpoint that will handle the call
            twiml_url = f"{self.webhook_base_url}/twilio/voice/{call_id}"
            status_callback_url = f"{self.webhook_base_url}/twilio/status/{call_id}"
            
            # Make the call
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=twiml_url,
                status_callback=status_callback_url,
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method='POST',
                record=True,  # Enable call recording
                recording_status_callback=f"{self.webhook_base_url}/twilio/recording/{call_id}",
                timeout=30,  # Ring for 30 seconds before giving up
                machine_detection='DetectMessageEnd',  # Detect answering machines
                async_amd=True,
                async_amd_status_callback=f"{self.webhook_base_url}/twilio/amd/{call_id}",
                # Pass custom parameters
                send_digits='',  # Can be used for extensions
                custom_parameters={
                    'call_id': call_id,
                    'livekit_room': livekit_room_name
                }
            )
            
            logger.info(f"Call initiated to {to_number} with SID {call.sid}")
            return call.sid
            
        except Exception as e:
            logger.error(f"Error making call to {to_number}: {e}")
            raise
    
    def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """Get the status of a call"""
        try:
            call = self.client.calls(call_sid).fetch()
            return {
                'sid': call.sid,
                'status': call.status,
                'direction': call.direction,
                'duration': call.duration,
                'start_time': call.start_time,
                'end_time': call.end_time,
                'answered_by': getattr(call, 'answered_by', None),
                'price': call.price,
                'price_unit': call.price_unit
            }
        except Exception as e:
            logger.error(f"Error getting call status for {call_sid}: {e}")
            return {}
    
    def end_call(self, call_sid: str) -> bool:
        """End an active call"""
        try:
            call = self.client.calls(call_sid).update(status='completed')
            logger.info(f"Call {call_sid} ended")
            return True
        except Exception as e:
            logger.error(f"Error ending call {call_sid}: {e}")
            return False
    
    def get_recording_url(self, call_sid: str) -> Optional[str]:
        """Get the recording URL for a completed call"""
        try:
            recordings = self.client.recordings.list(call_sid=call_sid, limit=1)
            if recordings:
                recording = recordings[0]
                # Return the MP3 URL
                return f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Recordings/{recording.sid}.mp3"
            return None
        except Exception as e:
            logger.error(f"Error getting recording for call {call_sid}: {e}")
            return None
    
    def create_twiml_response(self, call_id: str, livekit_room_name: str, livekit_token: str) -> str:
        """
        Create TwiML response for connecting call to LiveKit
        
        Args:
            call_id: Internal call ID
            livekit_room_name: LiveKit room to connect to
            livekit_token: LiveKit access token
            
        Returns:
            TwiML XML string
        """
        response = VoiceResponse()
        
        # Initial greeting while connecting
        response.say("Connecting your call...", voice='alice', language='pt-PT')
        
        # Connect to LiveKit via WebSocket
        stream = Stream(
            url=f"wss://{os.getenv('LIVEKIT_URL')}/twilio",
            name=f"livekit-stream-{call_id}"
        )
        
        # Add custom parameters for LiveKit
        stream.parameter(name='roomName', value=livekit_room_name)
        stream.parameter(name='token', value=livekit_token)
        stream.parameter(name='callId', value=call_id)
        
        response.append(stream)
        
        # Keep the call alive
        response.pause(length=3600)  # 1 hour max call duration
        
        return str(response)
    
    def create_status_twiml(self, status: str) -> str:
        """Create TwiML response for call status updates"""
        response = VoiceResponse()
        
        if status == 'no-answer':
            response.say("The person you are calling is not available. Please try again later.", 
                        voice='alice', language='pt-PT')
        elif status == 'busy':
            response.say("The line is busy. Please try again later.", 
                        voice='alice', language='pt-PT')
        elif status == 'failed':
            response.say("We're sorry, your call could not be completed.", 
                        voice='alice', language='pt-PT')
        
        return str(response)
    
    def handle_answering_machine(self, call_sid: str, is_machine: bool) -> None:
        """Handle answering machine detection"""
        try:
            if is_machine:
                # Update the call to leave a voicemail
                response = VoiceResponse()
                response.say(
                    "Olá, aqui é a Ana Sousa da Chamada AI. "
                    "Tentámos contactá-lo sobre uma solução inovadora para o seu restaurante. "
                    "Por favor, ligue-nos de volta quando for conveniente. Obrigada!",
                    voice='alice',
                    language='pt-PT'
                )
                response.hangup()
                
                # Update the call with the new TwiML
                self.client.calls(call_sid).update(
                    twiml=str(response)
                )
                logger.info(f"Voicemail left for call {call_sid}")
        except Exception as e:
            logger.error(f"Error handling answering machine for {call_sid}: {e}")
    
    def send_sms(self, to_number: str, message: str) -> Optional[str]:
        """Send an SMS message"""
        try:
            sms_message = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_number
            )
            logger.info(f"SMS sent to {to_number}: {sms_message.sid}")
            return sms_message.sid
        except Exception as e:
            logger.error(f"Error sending SMS to {to_number}: {e}")
            return None
    
    def validate_phone_number(self, phone_number: str) -> Dict[str, Any]:
        """Validate and get information about a phone number"""
        try:
            # Use Twilio Lookup API
            phone_info = self.client.lookups.v2.phone_numbers(phone_number).fetch(
                fields='line_type_intelligence,carrier'
            )
            
            return {
                'valid': True,
                'phone_number': phone_info.phone_number,
                'country_code': phone_info.country_code,
                'national_format': phone_info.national_format,
                'carrier': getattr(phone_info, 'carrier', {}).get('name'),
                'line_type': getattr(phone_info, 'line_type_intelligence', {}).get('type'),
                'mobile': getattr(phone_info, 'line_type_intelligence', {}).get('type') == 'mobile'
            }
        except Exception as e:
            logger.error(f"Error validating phone number {phone_number}: {e}")
            return {
                'valid': False,
                'error': str(e)
            }

# Create a singleton instance
twilio_client = TwilioClient()