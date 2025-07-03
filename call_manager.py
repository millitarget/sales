import asyncio
import logging
import os
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import json
import requests
import openai
from livekit.agents import cli, WorkerOptions, WorkerType

from models import db, Call, Lead, CallStatus, LeadStatus
from sales_agent import entrypoint as sales_agent_entrypoint

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("call_manager")

class CallManager:
    """Manages individual call initiation, monitoring, and completion"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.active_calls = {}  # Track active calls by ID
        
    def initiate_call(self, lead: Lead, context: str = None) -> str:
        """
        Initiate a call to a specific lead
        
        Args:
            lead: The Lead object to call
            context: Optional context from previous calls for personalization
            
        Returns:
            call_id: The ID of the created call record
        """
        
        # Create call record
        call = Call(
            lead_id=lead.id,
            status=CallStatus.PENDING,
            scheduled_at=datetime.now(timezone.utc),
            livekit_room_name=f"call-{uuid.uuid4()}",
            livekit_session_id=str(uuid.uuid4())
        )
        
        db.session.add(call)
        db.session.commit()
        
        log.info(f"Created call record {call.id} for lead {lead.full_name} at {lead.company_name}")
        
        # Start the actual call process
        self._start_livekit_call(call, lead, context)
        
        return call.id
    
    def _start_livekit_call(self, call: Call, lead: Lead, context: str = None):
        """Start the LiveKit call with the sales agent"""
        
        try:
            # Update call status
            call.status = CallStatus.IN_PROGRESS
            call.started_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Prepare context for the agent
            lead_context = self._prepare_lead_context(lead, context)
            
            # Set environment variables for the sales agent
            env = os.environ.copy()
            env['LEAD_CONTEXT'] = json.dumps(lead_context)
            env['CALL_ID'] = call.id
            env['LIVEKIT_ROOM_NAME'] = call.livekit_room_name
            env['PHONE_NUMBER'] = lead.phone_number
            
            log.info(f"Starting LiveKit call for {lead.phone_number}")
            
            # Start the sales agent process
            # In a production environment, this would integrate with your telephony provider
            self._simulate_outbound_call(call, lead, lead_context)
            
        except Exception as e:
            log.error(f"Failed to start call {call.id}: {str(e)}")
            call.status = CallStatus.FAILED
            db.session.commit()
            raise
    
    def _prepare_lead_context(self, lead: Lead, additional_context: str = None) -> Dict[str, Any]:
        """Prepare context information for the sales agent"""
        
        # Get previous call history
        previous_calls = Call.query.filter_by(
            lead_id=lead.id,
            status=CallStatus.COMPLETED
        ).order_by(Call.created_at.desc()).limit(3).all()
        
        call_history = []
        for prev_call in previous_calls:
            call_history.append({
                'date': prev_call.started_at.isoformat() if prev_call.started_at else None,
                'outcome': prev_call.call_outcome,
                'summary': prev_call.summary,
                'next_action': prev_call.next_action,
                'pain_points': prev_call.pain_points_identified,
                'objections': prev_call.objections_raised
            })
        
        context = {
            'lead_info': {
                'name': lead.full_name,
                'company': lead.company_name,
                'title': lead.title,
                'business_type': lead.business_type,
                'phone': lead.phone_number,
                'email': lead.email,
                'best_time_to_call': lead.best_time_to_call,
                'notes': lead.notes
            },
            'call_history': call_history,
            'previous_interactions': len(previous_calls),
            'lead_status': lead.status.value if lead.status else 'new',
            'additional_context': additional_context
        }
        
        return context
    
    def _simulate_outbound_call(self, call: Call, lead: Lead, context: Dict[str, Any]):
        """
        Simulate an outbound call process
        In production, this would integrate with Twilio, Vonage, or another telephony provider
        """
        
        # For demonstration, we'll simulate the call process
        log.info(f"Simulating outbound call to {lead.phone_number}")
        
        # In a real implementation, this would:
        # 1. Connect to telephony provider (Twilio, etc.)
        # 2. Initiate outbound call
        # 3. Connect the call to LiveKit room
        # 4. Start the sales agent in the room
        
        # For now, we'll simulate a completed call with sample data
        self._simulate_call_completion(call, lead)
    
    def _simulate_call_completion(self, call: Call, lead: Lead):
        """
        Simulate call completion with sample transcription and analysis
        In production, this would be called by the actual LiveKit agent
        """
        
        import time
        import random
        
        # Simulate call duration
        time.sleep(2)  # Simulate processing time
        
        # Generate sample outcomes based on lead status
        outcomes = {
            'interested': {
                'outcome': 'interested',
                'summary': f"Spoke with {lead.full_name} at {lead.company_name}. They showed interest in our automated reservation system.",
                'sentiment': 0.6,
                'next_action': 'Schedule product demo',
                'demo_scheduled': True,
                'keywords': ['reservations', 'automation', 'busy times', 'lost calls'],
                'pain_points': ['Missing calls during rush hours', 'Staff spending too much time on phone'],
                'objections': []
            },
            'not_interested': {
                'outcome': 'not_interested',
                'summary': f"Spoke with {lead.full_name}. Currently satisfied with existing system.",
                'sentiment': -0.2,
                'next_action': 'Follow up in 6 months',
                'demo_scheduled': False,
                'keywords': ['satisfied', 'current system'],
                'pain_points': [],
                'objections': ['Already have a system', 'Not looking to change']
            },
            'callback_requested': {
                'outcome': 'callback_requested',
                'summary': f"Reached gatekeeper at {lead.company_name}. {lead.full_name} is busy, requested callback tomorrow at 10 AM.",
                'sentiment': 0.1,
                'next_action': 'Call back tomorrow at 10 AM',
                'demo_scheduled': False,
                'keywords': ['busy', 'callback'],
                'pain_points': [],
                'objections': []
            }
        }
        
        # Randomly select an outcome for simulation
        outcome_key = random.choice(list(outcomes.keys()))
        outcome_data = outcomes[outcome_key]
        
        # Update call record
        call.status = CallStatus.COMPLETED
        call.ended_at = datetime.now(timezone.utc)
        call.duration_seconds = random.randint(120, 600)  # 2-10 minutes
        call.call_outcome = outcome_data['outcome']
        call.summary = outcome_data['summary']
        call.sentiment_score = outcome_data['sentiment']
        call.next_action = outcome_data['next_action']
        call.demo_scheduled = outcome_data['demo_scheduled']
        call.keywords_mentioned = outcome_data['keywords']
        call.pain_points_identified = outcome_data['pain_points']
        call.objections_raised = outcome_data['objections']
        
        # Generate sample transcription
        call.transcription = self._generate_sample_transcription(lead, outcome_data)
        
        # Update lead status
        if outcome_data['demo_scheduled']:
            lead.status = LeadStatus.DEMO_SCHEDULED
        elif outcome_data['outcome'] == 'interested':
            lead.status = LeadStatus.INTERESTED
        elif outcome_data['outcome'] == 'callback_requested':
            lead.status = LeadStatus.FOLLOW_UP_SCHEDULED
        else:
            lead.status = LeadStatus.CONTACTED
        
        lead.last_contacted = datetime.now(timezone.utc)
        lead.updated_at = datetime.now(timezone.utc)
        
        # Commit changes
        db.session.commit()
        
        log.info(f"Call {call.id} completed with outcome: {outcome_data['outcome']}")
        
        # Process post-call actions
        self._process_post_call_actions(call, lead, outcome_data)
    
    def _generate_sample_transcription(self, lead: Lead, outcome_data: Dict[str, Any]) -> str:
        """Generate a sample transcription based on the call outcome"""
        
        transcriptions = {
            'interested': f"""
Ana: Bom dia! Daqui fala a Ana Sousa da Chamada AI. Com quem posso falar sobre a gestão do {lead.company_name}, por favor?

{lead.first_name}: Sou eu, {lead.first_name} {lead.last_name}.

Ana: Perfeito, Sr. {lead.last_name}! É uma chamada comercial não solicitada - posso ter apenas 30 segundos do seu tempo para explicar porque pode ser do seu interesse?

{lead.first_name}: Está bem, pode falar.

Ana: Muito obrigada! Trabalhamos com restaurantes para nunca mais perderem uma única reserva quando estão ocupados. Como gerem atualmente as reservas - sistema digital ou telefone?

{lead.first_name}: Principalmente por telefone. Às vezes perdemos chamadas quando estamos muito ocupados...

Ana: Exatamente! Cada chamada perdida vale 25-40 euros. A Chamada AI atende automaticamente 24/7, faz reservas e liberta a equipa. Restaurantes portugueses registam +25-40% de reservas em 30-60 dias. Vale a pena marcarmos 30 min para lhe mostrar?

{lead.first_name}: Sim, parece interessante. Podemos marcar para a próxima semana.

Ana: Perfeito! Que tal quinta-feira às 10h? Posso enviar o convite para o vosso email?
""",
            'not_interested': f"""
Ana: Bom dia! Daqui fala a Ana Sousa da Chamada AI. Com quem posso falar sobre a gestão do {lead.company_name}, por favor?

{lead.first_name}: Sou eu, {lead.first_name}.

Ana: Perfeito, Sr. {lead.last_name}! É uma chamada comercial não solicitada - posso ter apenas 30 segundos do seu tempo para explicar porque pode ser do seu interesse?

{lead.first_name}: Não estamos interessados, já temos um sistema que funciona bem.

Ana: Compreendo. Só para confirmar: está 100% seguro de que nenhuma chamada fica por atender quando estão muito ocupados?

{lead.first_name}: Sim, estamos satisfeitos com o que temos. Obrigado.

Ana: Muito bem. Fico à disposição se mudarem de ideias. Tenha um bom dia!
""",
            'callback_requested': f"""
Ana: Bom dia! Daqui fala a Ana Sousa da Chamada AI. Com quem posso falar sobre a gestão do {lead.company_name}, por favor?

Staff: O Sr. {lead.first_name} não está disponível agora. Está numa reunião.

Ana: Compreendo perfeitamente. Qual seria o melhor momento para contactá-lo directamente?

Staff: Amanhã de manhã é melhor, por volta das 10h.

Ana: Perfeito! Ligo amanhã às 10h. Qual é o nome para eu poder agradecer quando ligar?

Staff: Pode dizer que falou com a Maria.

Ana: Muito obrigada, Maria. Até amanhã!
"""
        }
        
        return transcriptions.get(outcome_data['outcome'], "Transcription processing...")
    
    def _process_post_call_actions(self, call: Call, lead: Lead, outcome_data: Dict[str, Any]):
        """Process actions that need to happen after the call"""
        
        if outcome_data['demo_scheduled']:
            # Schedule demo call
            from datetime import timedelta
            demo_date = datetime.now(timezone.utc) + timedelta(days=3)  # Schedule for 3 days from now
            
            from models import ScheduledCall
            scheduled_call = ScheduledCall(
                lead_id=lead.id,
                scheduled_for=demo_date,
                call_type='demo',
                context=f"Demo scheduled from call on {call.started_at.strftime('%Y-%m-%d')}. Interest in automated reservation system.",
                agenda='Product demonstration - automated reservation system'
            )
            db.session.add(scheduled_call)
            db.session.commit()
            
            log.info(f"Demo scheduled for {lead.full_name} on {demo_date}")
        
        elif outcome_data['outcome'] == 'callback_requested':
            # Schedule follow-up call
            from datetime import timedelta
            callback_date = datetime.now(timezone.utc) + timedelta(days=1)  # Tomorrow
            
            from models import ScheduledCall
            scheduled_call = ScheduledCall(
                lead_id=lead.id,
                scheduled_for=callback_date,
                call_type='follow_up',
                context=f"Callback requested from call on {call.started_at.strftime('%Y-%m-%d')}. Spoke with gatekeeper.",
                agenda='Follow-up call as requested'
            )
            db.session.add(scheduled_call)
            db.session.commit()
            
            log.info(f"Callback scheduled for {lead.full_name} on {callback_date}")
    
    def get_call_status(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a call"""
        call = Call.query.get(call_id)
        if call:
            return call.to_dict()
        return None
    
    def process_transcription(self, call_id: str, transcription: str) -> Dict[str, Any]:
        """
        Process call transcription using OpenAI to extract insights
        """
        try:
            # Use OpenAI to analyze the transcription
            analysis_prompt = f"""
            Analyze this sales call transcription and extract the following information in JSON format:

            Transcription:
            {transcription}

            Please provide:
            1. call_outcome: (interested, not_interested, callback_requested, no_answer, voicemail)
            2. sentiment_score: (-1 to 1, where -1 is very negative, 1 is very positive)
            3. summary: (brief summary of the conversation)
            4. pain_points_identified: (array of business pain points mentioned)
            5. objections_raised: (array of objections and concerns)
            6. keywords_mentioned: (important keywords and topics discussed)
            7. next_action: (recommended next step)
            8. demo_scheduled: (boolean - was a demo/meeting scheduled?)
            9. follow_up_date: (if mentioned, in ISO format)

            Return only valid JSON.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert sales call analyzer. Return only valid JSON."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            analysis = json.loads(response.choices[0].message.content)
            return analysis
            
        except Exception as e:
            log.error(f"Failed to process transcription for call {call_id}: {str(e)}")
            return {
                "call_outcome": "unknown",
                "sentiment_score": 0.0,
                "summary": "Transcription analysis failed",
                "pain_points_identified": [],
                "objections_raised": [],
                "keywords_mentioned": [],
                "next_action": "Manual review required",
                "demo_scheduled": False
            }
    
    def complete_call(self, call_id: str, transcription: str, duration_seconds: int) -> bool:
        """
        Mark a call as completed and process the results
        """
        try:
            call = Call.query.get(call_id)
            if not call:
                log.error(f"Call {call_id} not found")
                return False
            
            # Process transcription
            analysis = self.process_transcription(call_id, transcription)
            
            # Update call record
            call.status = CallStatus.COMPLETED
            call.ended_at = datetime.now(timezone.utc)
            call.duration_seconds = duration_seconds
            call.transcription = transcription
            call.call_outcome = analysis.get('call_outcome')
            call.sentiment_score = analysis.get('sentiment_score')
            call.summary = analysis.get('summary')
            call.next_action = analysis.get('next_action')
            call.demo_scheduled = analysis.get('demo_scheduled', False)
            call.keywords_mentioned = analysis.get('keywords_mentioned', [])
            call.pain_points_identified = analysis.get('pain_points_identified', [])
            call.objections_raised = analysis.get('objections_raised', [])
            
            # Update lead
            lead = call.lead
            lead.last_contacted = datetime.now(timezone.utc)
            lead.updated_at = datetime.now(timezone.utc)
            
            # Update lead status based on outcome
            if analysis.get('demo_scheduled'):
                lead.status = LeadStatus.DEMO_SCHEDULED
            elif analysis.get('call_outcome') == 'interested':
                lead.status = LeadStatus.INTERESTED
            elif analysis.get('call_outcome') == 'callback_requested':
                lead.status = LeadStatus.FOLLOW_UP_SCHEDULED
            else:
                lead.status = LeadStatus.CONTACTED
            
            db.session.commit()
            
            log.info(f"Call {call_id} completed successfully")
            return True
            
        except Exception as e:
            log.error(f"Failed to complete call {call_id}: {str(e)}")
            db.session.rollback()
            return False