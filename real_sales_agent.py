"""
Real Sales Agent - Portuguese AI sales representative for actual phone calls
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any

from livekit import agents, rtc
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, WorkerType
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, deepgram, silero

from supabase_client import supabase_client

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("real_sales_agent")

# Portuguese language configuration
LANGUAGE_CONFIG = {
    "language": "pt-PT",
    "voice": "pt-PT-FernandaNeural",  # Azure voice
    "model": "gpt-4",
    "temperature": 0.7
}

def create_assistant_prompt(lead_context: Dict[str, Any]) -> str:
    """Create a personalized prompt based on lead context"""
    
    lead_info = lead_context.get('lead_info', {})
    previous_calls = lead_context.get('previous_calls', [])
    
    # Build context from previous interactions
    history_context = ""
    if previous_calls:
        history_context = "\n\nHISTÓRICO DE INTERAÇÕES:"
        for call in previous_calls:
            history_context += f"\n- {call['date']}: {call.get('summary', 'Sem resumo')}"
            if call.get('pain_points'):
                history_context += f"\n  Problemas: {', '.join(call['pain_points'])}"
            if call.get('objections'):
                history_context += f"\n  Objeções: {', '.join(call['objections'])}"
    
    prompt = f"""
Você é Ana Sousa, representante de vendas da Chamada AI, uma empresa portuguesa que oferece soluções de atendimento automático para restaurantes.

INFORMAÇÕES DO LEAD:
- Nome: {lead_info.get('name', 'Cliente')}
- Empresa: {lead_info.get('company', 'Restaurante')}
- Tipo de negócio: {lead_info.get('business_type', 'Restaurante')}
- Cargo: {lead_info.get('title', 'Gestor')}
{history_context}

REGRAS DE CONDUTA:
1. Fale APENAS em português de Portugal
2. Use tratamento formal (você/o senhor/a senhora)
3. Seja profissional mas calorosa
4. Mantenha respostas concisas (máximo 2-3 frases)
5. Use a metodologia SPIN para descoberta
6. Foque em problemas de perder chamadas e reservas

OBJETIVO PRINCIPAL:
Agendar uma demonstração de 30 minutos do sistema Chamada AI

FLUXO DA CONVERSA:
1. Apresentação breve e pedido de permissão
2. Descoberta de problemas com reservas
3. Quantificar perdas (cada chamada = 25-40€)
4. Apresentar solução (atendimento 24/7 automático)
5. Agendar demonstração

TRATAMENTO DE OBJEÇÕES:
- "Não tenho tempo": Sugira horário específico conveniente
- "Já tenho sistema": Pergunte sobre chamadas fora de horário
- "É caro": Foque no ROI (recupera investimento em 2-4 semanas)
- "Preciso pensar": Ofereça enviar informações e remarcar

Responda de forma natural e conversacional, como uma vendedora portuguesa real.
"""
    
    return prompt

async def run_sales_agent(room_name: str, token: str, lead_context: Dict[str, Any]):
    """Run the sales agent in a LiveKit room"""
    
    log.info(f"Starting sales agent for room {room_name}")
    
    # Create LiveKit room connection
    room = rtc.Room()
    
    try:
        # Connect to room
        await room.connect(
            os.getenv('LIVEKIT_URL'),
            token,
            options=rtc.RoomOptions(
                auto_subscribe=True,
                dynacast=True,
            )
        )
        
        log.info(f"Connected to room {room_name}")
        
        # Initialize STT (Speech to Text)
        stt = deepgram.STT(
            language="pt-PT",
            model="nova-2",
            punctuate=True,
            interim_results=True
        )
        
        # Initialize LLM
        llm = openai.LLM(
            model=LANGUAGE_CONFIG["model"],
            temperature=LANGUAGE_CONFIG["temperature"]
        )
        
        # Initialize TTS (Text to Speech)
        tts = openai.TTS(
            voice="nova",  # OpenAI voice
            model="tts-1",
            speed=1.0
        )
        
        # Create initial context
        initial_ctx = agents.AssistantContext(
            system_prompt=create_assistant_prompt(lead_context),
            # Add function definitions here if needed
        )
        
        # Create voice assistant
        assistant = VoiceAssistant(
            vad=silero.VAD.load(),
            stt=stt,
            llm=llm,
            tts=tts,
            context=initial_ctx,
            interrupt_min_words=3,
            base_volume=1.0,
            debug=True
        )
        
        # Start the assistant
        assistant.start(room)
        
        # Track conversation
        call_id = lead_context.get('call_id')
        transcription_buffer = []
        
        # Handle room events
        @room.on("track_published")
        def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            log.info(f"Track published: {publication.sid} by {participant.identity}")
        
        @room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            log.info(f"Track subscribed: {track.sid}")
            if track.kind == rtc.TrackKind.AUDIO:
                # Process audio if needed
                pass
        
        @room.on("participant_disconnected")
        async def on_participant_disconnected(participant: rtc.RemoteParticipant):
            log.info(f"Participant disconnected: {participant.identity}")
            # Call ended - save transcription and close
            if call_id and transcription_buffer:
                await save_call_results(call_id, transcription_buffer)
            await room.disconnect()
        
        # Capture assistant messages for transcription
        @assistant.on("user_speech_committed")
        def on_user_speech(message: str):
            transcription_buffer.append(f"Cliente: {message}")
            log.info(f"User: {message}")
        
        @assistant.on("agent_speech_committed")
        def on_agent_speech(message: str):
            transcription_buffer.append(f"Ana: {message}")
            log.info(f"Agent: {message}")
        
        # Keep the agent running
        while room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            await asyncio.sleep(1)
        
        log.info("Sales agent session ended")
        
    except Exception as e:
        log.error(f"Error in sales agent: {e}")
        raise
    finally:
        await room.disconnect()

async def save_call_results(call_id: str, transcription_buffer: list):
    """Save call transcription and trigger analysis"""
    
    try:
        # Join transcription
        full_transcription = "\n".join(transcription_buffer)
        
        # Update call with transcription
        from real_call_manager import real_call_manager
        
        # Calculate duration (simplified - in real scenario, track actual time)
        duration = len(transcription_buffer) * 5  # Rough estimate
        
        await real_call_manager.handle_call_completed(
            call_id=call_id,
            duration=duration,
            transcription=full_transcription
        )
        
        log.info(f"Call results saved for {call_id}")
        
    except Exception as e:
        log.error(f"Failed to save call results: {e}")

# Agent worker setup for LiveKit
async def entrypoint(ctx: JobContext):
    """LiveKit agent entrypoint"""
    
    # Get lead context from job metadata
    lead_context = ctx.job.metadata.get('lead_context', {})
    
    # Create and run agent session
    await run_sales_agent(
        room_name=ctx.room.name,
        token=ctx.token,
        lead_context=lead_context
    )

if __name__ == "__main__":
    # Run as LiveKit worker
    from livekit.agents import cli
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            worker_type=WorkerType.ROOM
        )
    )