"""
Real Flask App - Integrated with Supabase and Twilio for actual functionality
"""

from flask import Flask, render_template, request, jsonify, Response, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timezone
import os
import logging
import asyncio
from functools import wraps

from supabase_client import supabase_client
from real_call_manager import real_call_manager
from twilio_client import twilio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
CORS(app)

# Helper to run async functions in Flask
def async_route(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

# Web Routes

@app.route('/')
def dashboard():
    """Main dashboard"""
    stats = supabase_client.get_lead_statistics()
    recent_calls = supabase_client.get_recent_calls(limit=10)
    upcoming_calls = supabase_client.get_upcoming_scheduled_calls(hours=24)
    active_campaigns = supabase_client.get_active_campaigns()
    
    return render_template('dashboard.html',
                         stats=stats,
                         recent_calls=recent_calls,
                         upcoming_calls=upcoming_calls,
                         active_campaigns=active_campaigns)

@app.route('/leads')
def leads_list():
    """Display leads"""
    status_filter = request.args.get('status', '')
    filters = {'status': status_filter} if status_filter else {}
    
    leads = supabase_client.get_leads(filters=filters)
    
    return render_template('leads.html', 
                         leads=leads,
                         status_filter=status_filter,
                         lead_statuses=['new', 'contacted', 'interested', 'demo_scheduled'])

@app.route('/leads/new', methods=['GET', 'POST'])
def new_lead():
    """Create new lead"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        try:
            lead = supabase_client.create_lead(data)
            
            if request.is_json:
                return jsonify({'success': True, 'lead_id': lead['id']})
            else:
                return redirect(url_for('leads_list'))
        except Exception as e:
            logger.error(f"Error creating lead: {e}")
            if request.is_json:
                return jsonify({'error': str(e)}), 400
    
    return render_template('new_lead.html')

@app.route('/leads/bulk-import', methods=['POST'])
def bulk_import_leads():
    """Import leads from CSV"""
    import pandas as pd
    from io import StringIO
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    try:
        stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
        df = pd.read_csv(stream)
        
        # Convert DataFrame to list of dicts
        leads_data = df.to_dict('records')
        
        # Bulk create in Supabase
        created_leads = supabase_client.bulk_create_leads(leads_data)
        
        return jsonify({
            'success': True,
            'leads_created': len(created_leads)
        })
        
    except Exception as e:
        logger.error(f"Bulk import error: {e}")
        return jsonify({'error': str(e)}), 400

# API Routes

@app.route('/api/leads')
def api_leads():
    """Get all leads API"""
    leads = supabase_client.get_leads()
    return jsonify(leads)

@app.route('/api/leads/<lead_id>/call', methods=['POST'])
@async_route
async def initiate_call(lead_id):
    """Initiate a call to a lead"""
    try:
        context = request.json.get('context', '') if request.is_json else ''
        call_id = await real_call_manager.initiate_call(lead_id, context)
        return jsonify({'success': True, 'call_id': call_id})
    except Exception as e:
        logger.error(f"Call initiation error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/status')
def get_call_status(call_id):
    """Get call status"""
    call = supabase_client.get_call(call_id)
    if call:
        return jsonify(call)
    return jsonify({'error': 'Call not found'}), 404

@app.route('/api/bulk-call', methods=['POST'])
@async_route
async def bulk_call():
    """Start bulk calling"""
    data = request.get_json()
    lead_ids = data.get('lead_ids', [])
    campaign_id = data.get('campaign_id')
    
    if not lead_ids:
        return jsonify({'error': 'No leads specified'}), 400
    
    try:
        # Create scheduled calls for each lead
        scheduled_calls = []
        for i, lead_id in enumerate(lead_ids):
            # Space out calls by 5 minutes
            scheduled_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
            scheduled_time = scheduled_time.replace(minute=(scheduled_time.minute + i * 5) % 60)
            
            scheduled_data = {
                'lead_id': lead_id,
                'scheduled_for': scheduled_time.isoformat(),
                'call_type': 'cold_call',
                'status': 'scheduled'
            }
            
            scheduled_call = supabase_client.create_scheduled_call(scheduled_data)
            scheduled_calls.append(scheduled_call)
        
        # If campaign, add leads to campaign
        if campaign_id:
            supabase_client.add_leads_to_campaign(campaign_id, lead_ids)
        
        return jsonify({
            'success': True,
            'scheduled_calls': len(scheduled_calls),
            'message': f'Scheduled {len(scheduled_calls)} calls'
        })
        
    except Exception as e:
        logger.error(f"Bulk call error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scheduled-calls')
def api_scheduled_calls():
    """Get upcoming scheduled calls"""
    calls = supabase_client.get_upcoming_scheduled_calls()
    return jsonify(calls)

@app.route('/api/analytics')
def api_analytics():
    """Get analytics data"""
    stats = supabase_client.get_lead_statistics()
    call_analytics = supabase_client.get_call_analytics()
    
    return jsonify({
        'lead_stats': stats,
        'call_analytics': call_analytics
    })

# Twilio Webhooks

@app.route('/twilio/voice/<call_id>', methods=['POST'])
def twilio_voice_webhook(call_id):
    """Handle incoming Twilio call"""
    try:
        # Get call record
        call = supabase_client.get_call(call_id)
        if not call:
            return Response("Call not found", status=404)
        
        # Create LiveKit token for this call
        from real_call_manager import real_call_manager
        livekit_token = real_call_manager._create_livekit_token(
            call['livekit_room_name'],
            f"twilio-{call_id}"
        )
        
        # Create TwiML response
        twiml = twilio_client.create_twiml_response(
            call_id,
            call['livekit_room_name'],
            livekit_token
        )
        
        return Response(twiml, mimetype='text/xml')
        
    except Exception as e:
        logger.error(f"Twilio voice webhook error: {e}")
        return Response("Error", status=500)

@app.route('/twilio/status/<call_id>', methods=['POST'])
def twilio_status_webhook(call_id):
    """Handle Twilio call status updates"""
    try:
        status = request.form.get('CallStatus')
        duration = request.form.get('CallDuration', 0)
        
        logger.info(f"Call {call_id} status update: {status}")
        
        # Map Twilio status to our status
        status_map = {
            'initiated': 'pending',
            'ringing': 'in_progress',
            'in-progress': 'in_progress',
            'completed': 'completed',
            'busy': 'busy',
            'no-answer': 'no_answer',
            'failed': 'failed'
        }
        
        our_status = status_map.get(status, status)
        
        # Update call status
        update_data = {'status': our_status}
        
        if status == 'completed':
            update_data['duration_seconds'] = int(duration)
            update_data['ended_at'] = datetime.now(timezone.utc).isoformat()
        
        supabase_client.update_call(call_id, update_data)
        
        # Create call event
        supabase_client.create_call_event(call_id, f'twilio_status_{status}', {
            'duration': str(duration),
            'twilio_data': dict(request.form)
        })
        
        return Response("OK", status=200)
        
    except Exception as e:
        logger.error(f"Twilio status webhook error: {e}")
        return Response("Error", status=500)

@app.route('/twilio/recording/<call_id>', methods=['POST'])
def twilio_recording_webhook(call_id):
    """Handle Twilio recording completion"""
    try:
        recording_url = request.form.get('RecordingUrl')
        recording_sid = request.form.get('RecordingSid')
        
        if recording_url:
            # Update call with recording URL
            supabase_client.update_call(call_id, {
                'recording_url': f"{recording_url}.mp3"
            })
            
            # Create event
            supabase_client.create_call_event(call_id, 'recording_completed', {
                'recording_sid': recording_sid,
                'recording_url': recording_url
            })
        
        return Response("OK", status=200)
        
    except Exception as e:
        logger.error(f"Twilio recording webhook error: {e}")
        return Response("Error", status=500)

@app.route('/twilio/amd/<call_id>', methods=['POST'])
def twilio_amd_webhook(call_id):
    """Handle Twilio answering machine detection"""
    try:
        answered_by = request.form.get('AnsweredBy')
        call_sid = request.form.get('CallSid')
        
        logger.info(f"Call {call_id} answered by: {answered_by}")
        
        if answered_by in ['machine_start', 'machine_end_beep', 'machine_end_silence']:
            # Handle voicemail
            twilio_client.handle_answering_machine(call_sid, True)
            
            # Update call
            supabase_client.update_call(call_id, {
                'status': 'voicemail',
                'call_outcome': 'voicemail'
            })
        
        return Response("OK", status=200)
        
    except Exception as e:
        logger.error(f"Twilio AMD webhook error: {e}")
        return Response("Error", status=500)

# Background Tasks

def process_scheduled_calls():
    """Process scheduled calls that are due"""
    try:
        # Get overdue scheduled calls
        overdue_calls = supabase_client.get_overdue_scheduled_calls(minutes=0)
        
        for scheduled_call in overdue_calls:
            if scheduled_call['status'] == 'scheduled':
                try:
                    # Initiate the call
                    asyncio.run(real_call_manager.initiate_call(
                        scheduled_call['lead_id'],
                        scheduled_call.get('context', '')
                    ))
                    
                    # Update scheduled call status
                    supabase_client.update_scheduled_call(scheduled_call['id'], {
                        'status': 'completed'
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to process scheduled call {scheduled_call['id']}: {e}")
                    supabase_client.update_scheduled_call(scheduled_call['id'], {
                        'status': 'failed'
                    })
        
    except Exception as e:
        logger.error(f"Error processing scheduled calls: {e}")

# Error handlers

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Start background task processor
    from apscheduler.schedulers.background import BackgroundScheduler
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=process_scheduled_calls,
        trigger="interval",
        seconds=30,  # Check every 30 seconds
        id='process_scheduled_calls',
        name='Process scheduled calls',
        replace_existing=True
    )
    scheduler.start()
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)