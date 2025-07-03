"""
Real Call Manager - Integrates Supabase and Twilio for actual phone calls
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import json
import jwt
from livekit import api

from supabase_client import supabase_client
from twilio_client import twilio_client

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class RealCallManager:
    """Manages real phone calls using Twilio and LiveKit"""
    
    def __init__(self):
        self.livekit_api_key = os.getenv('LIVEKIT_API_KEY')
        self.livekit_api_secret = os.getenv('LIVEKIT_API_SECRET')
        self.livekit_url = os.getenv('LIVEKIT_URL')
        
        if not all([self.livekit_api_key, self.livekit_api_secret, self.livekit_url]):
            raise ValueError("LiveKit configuration missing")
        
        log.info("RealCallManager initialized")
    
    async def initiate_call(self, lead_id: str, context: str = None) -> str:
        """
        Initiate a real phone call to a lead
        
        Args:
            lead_id: UUID of the lead to call
            context: Optional context from previous calls
            
        Returns:
            call_id: UUID of the created call record
        """
        
        # Get lead information from Supabase
        lead = supabase_client.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        log.info(f"Initiating call to {lead['first_name']} {lead['last_name']} at {lead['company_name']}")
        
        # Create call record in Supabase
        call_id = str(uuid.uuid4())
        livekit_room_name = f"call-{call_id}"
        
        call_data = {
            'id': call_id,
            'lead_id': lead_id,
            'status': 'pending',
            'scheduled_at': datetime.now(timezone.utc).isoformat(),
            'livekit_room_name': livekit_room_name,
            'livekit_session_id': str(uuid.uuid4())
        }
        
        call_record = supabase_client.create_call(call_data)
        
        # Create LiveKit room and token
        livekit_token = self._create_livekit_token(livekit_room_name, f"agent-{call_id}")
        
        # Start the actual phone call via Twilio
        try:
            # Update call status
            supabase_client.update_call(call_id, {
                'status': 'in_progress',
                'started_at': datetime.now(timezone.utc).isoformat()
            })
            
            # Make the actual call
            twilio_sid = twilio_client.make_call(
                to_number=lead['phone_number'],
                call_id=call_id,
                livekit_room_name=livekit_room_name
            )
            
            # Update call with Twilio SID
            supabase_client.update_call(call_id, {
                'call_sid': twilio_sid
            })
            
            # Start the AI agent in the LiveKit room
            asyncio.create_task(self._start_ai_agent(
                call_id=call_id,
                lead=lead,
                room_name=livekit_room_name,
                token=livekit_token,
                context=context
            ))
            
            # Create call event
            supabase_client.create_call_event(call_id, 'call_initiated', {
                'twilio_sid': twilio_sid,
                'phone_number': lead['phone_number']
            })
            
            log.info(f"Call {call_id} initiated successfully with Twilio SID {twilio_sid}")
            return call_id
            
        except Exception as e:
            log.error(f"Failed to initiate call {call_id}: {e}")
            
            # Update call status to failed
            supabase_client.update_call(call_id, {
                'status': 'failed',
                'ended_at': datetime.now(timezone.utc).isoformat()
            })
            
            raise
    
    def _create_livekit_token(self, room_name: str, participant_name: str) -> str:
        """Create a LiveKit access token"""
        
        claims = {
            'exp': int(datetime.now(timezone.utc).timestamp()) + 3600,  # 1 hour expiry
            'iss': self.livekit_api_key,
            'sub': participant_name,
            'video': {
                'room': room_name,
                'roomJoin': True,
                'canPublish': True,
                'canSubscribe': True,
                'canPublishData': True
            }
        }
        
        token = jwt.encode(
            claims,
            self.livekit_api_secret,
            algorithm='HS256'
        )
        
        return token
    
    async def _start_ai_agent(self, call_id: str, lead: Dict[str, Any], 
                             room_name: str, token: str, context: str = None):
        """Start the AI sales agent in the LiveKit room"""
        
        # Import here to avoid circular dependency
        from sales_agent import run_sales_agent
        
        try:
            # Prepare lead context
            lead_context = {
                'call_id': call_id,
                'lead_info': {
                    'name': f"{lead['first_name']} {lead['last_name']}",
                    'company': lead['company_name'],
                    'title': lead.get('title'),
                    'business_type': lead.get('business_type'),
                    'phone': lead['phone_number'],
                    'email': lead.get('email'),
                    'best_time_to_call': lead.get('best_time_to_call'),
                    'notes': lead.get('notes')
                },
                'previous_calls': self._get_previous_calls(lead['id']),
                'context': context
            }
            
            # Run the sales agent
            await run_sales_agent(
                room_name=room_name,
                token=token,
                lead_context=lead_context
            )
            
        except Exception as e:
            log.error(f"Failed to start AI agent for call {call_id}: {e}")
            supabase_client.create_call_event(call_id, 'agent_error', {
                'error': str(e)
            })
    
    def _get_previous_calls(self, lead_id: str) -> list:
        """Get summary of previous calls for context"""
        
        calls = supabase_client.get_calls_for_lead(lead_id)
        
        # Get last 3 completed calls
        completed_calls = [c for c in calls if c['status'] == 'completed'][:3]
        
        call_history = []
        for call in completed_calls:
            call_history.append({
                'date': call['created_at'],
                'outcome': call.get('call_outcome'),
                'summary': call.get('summary'),
                'next_action': call.get('next_action'),
                'pain_points': call.get('pain_points_identified', []),
                'objections': call.get('objections_raised', [])
            })
        
        return call_history
    
    async def handle_call_completed(self, call_id: str, duration: int, 
                                  transcription: str = None) -> bool:
        """
        Handle call completion
        
        Args:
            call_id: UUID of the call
            duration: Call duration in seconds
            transcription: Optional call transcription
            
        Returns:
            Success status
        """
        
        try:
            call = supabase_client.get_call(call_id)
            if not call:
                log.error(f"Call {call_id} not found")
                return False
            
            # Get recording URL from Twilio if available
            recording_url = None
            if call.get('call_sid'):
                recording_url = twilio_client.get_recording_url(call['call_sid'])
            
            # Update call record
            update_data = {
                'status': 'completed',
                'ended_at': datetime.now(timezone.utc).isoformat(),
                'duration_seconds': duration,
                'recording_url': recording_url
            }
            
            if transcription:
                update_data['transcription'] = transcription
                
                # Analyze transcription
                analysis = await self._analyze_transcription(transcription)
                update_data.update(analysis)
            
            supabase_client.update_call(call_id, update_data)
            
            # Update lead status and last contacted
            lead_update = {
                'last_contacted': datetime.now(timezone.utc).isoformat()
            }
            
            # Update lead status based on outcome
            if update_data.get('demo_scheduled'):
                lead_update['status'] = 'demo_scheduled'
            elif update_data.get('call_outcome') == 'interested':
                lead_update['status'] = 'interested'
            elif update_data.get('call_outcome') == 'callback_requested':
                lead_update['status'] = 'follow_up_scheduled'
            else:
                lead_update['status'] = 'contacted'
            
            supabase_client.update_lead(call['lead_id'], lead_update)
            
            # Schedule follow-up if needed
            if update_data.get('follow_up_date'):
                self._schedule_follow_up(call['lead_id'], update_data['follow_up_date'], 
                                       update_data.get('next_action'))
            
            # Create completion event
            supabase_client.create_call_event(call_id, 'call_completed', {
                'duration': duration,
                'outcome': update_data.get('call_outcome'),
                'demo_scheduled': update_data.get('demo_scheduled', False)
            })
            
            log.info(f"Call {call_id} completed successfully")
            return True
            
        except Exception as e:
            log.error(f"Failed to complete call {call_id}: {e}")
            return False
    
    async def _analyze_transcription(self, transcription: str) -> Dict[str, Any]:
        """Analyze call transcription using OpenAI"""
        
        import openai
        
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert sales call analyzer. Analyze the transcription and extract insights in JSON format."
                    },
                    {
                        "role": "user",
                        "content": f"""
                        Analyze this sales call transcription and return JSON with:
                        - call_outcome: (interested, not_interested, callback_requested, no_answer, voicemail)
                        - sentiment_score: (-1 to 1)
                        - summary: (brief summary)
                        - pain_points_identified: (array)
                        - objections_raised: (array)
                        - keywords_mentioned: (array)
                        - next_action: (recommended action)
                        - demo_scheduled: (boolean)
                        - follow_up_date: (ISO date if mentioned)
                        
                        Transcription:
                        {transcription}
                        """
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            log.error(f"Failed to analyze transcription: {e}")
            return {
                "call_outcome": "unknown",
                "sentiment_score": 0.0,
                "summary": "Analysis failed"
            }
    
    def _schedule_follow_up(self, lead_id: str, follow_up_date: str, context: str = None):
        """Schedule a follow-up call"""
        
        try:
            scheduled_data = {
                'lead_id': lead_id,
                'scheduled_for': follow_up_date,
                'call_type': 'follow_up',
                'context': context or 'Follow-up call as discussed',
                'status': 'scheduled'
            }
            
            supabase_client.create_scheduled_call(scheduled_data)
            log.info(f"Follow-up scheduled for lead {lead_id} on {follow_up_date}")
            
        except Exception as e:
            log.error(f"Failed to schedule follow-up: {e}")

# Create singleton instance
real_call_manager = RealCallManager()