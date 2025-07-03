from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv
import json
import pandas as pd
from io import StringIO

# Import our models
from models import db, Lead, Call, ScheduledCall, CallCampaign, CallStatus, LeadStatus

# Load environment variables
load_dotenv(".env.local")

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///cold_calling.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
CORS(app)

# Initialize database tables
with app.app_context():
    db.create_all()

@app.route('/')
def dashboard():
    """Main dashboard showing overview of leads and campaigns"""
    # Get summary statistics
    total_leads = Lead.query.count()
    new_leads = Lead.query.filter_by(status=LeadStatus.NEW).count()
    contacted_leads = Lead.query.filter(Lead.status.in_([
        LeadStatus.CONTACTED, 
        LeadStatus.INTERESTED, 
        LeadStatus.FOLLOW_UP_SCHEDULED
    ])).count()
    
    demos_scheduled = Lead.query.filter_by(status=LeadStatus.DEMO_SCHEDULED).count()
    closed_won = Lead.query.filter_by(status=LeadStatus.CLOSED_WON).count()
    
    # Recent calls
    recent_calls = Call.query.order_by(Call.created_at.desc()).limit(10).all()
    
    # Upcoming scheduled calls
    upcoming_calls = ScheduledCall.query.filter(
        ScheduledCall.scheduled_for >= datetime.now(timezone.utc),
        ScheduledCall.status == 'scheduled'
    ).order_by(ScheduledCall.scheduled_for).limit(10).all()
    
    # Active campaigns
    active_campaigns = CallCampaign.query.filter_by(status='active').all()
    
    stats = {
        'total_leads': total_leads,
        'new_leads': new_leads,
        'contacted_leads': contacted_leads,
        'demos_scheduled': demos_scheduled,
        'closed_won': closed_won,
        'conversion_rate': round((closed_won / total_leads * 100) if total_leads > 0 else 0, 1)
    }
    
    return render_template('dashboard.html', 
                         stats=stats,
                         recent_calls=recent_calls,
                         upcoming_calls=upcoming_calls,
                         active_campaigns=active_campaigns)

@app.route('/leads')
def leads_list():
    """Display all leads with filtering and sorting options"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = Lead.query
    
    # Apply filters
    if status_filter:
        query = query.filter_by(status=LeadStatus(status_filter))
    
    if search:
        query = query.filter(
            (Lead.first_name.contains(search)) |
            (Lead.last_name.contains(search)) |
            (Lead.company_name.contains(search)) |
            (Lead.phone_number.contains(search))
        )
    
    # Pagination
    leads = query.order_by(Lead.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('leads.html', leads=leads, 
                         status_filter=status_filter, search=search,
                         lead_statuses=LeadStatus)

@app.route('/leads/new', methods=['GET', 'POST'])
def new_lead():
    """Create a new lead"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        lead = Lead(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            company_name=data.get('company_name'),
            phone_number=data.get('phone_number'),
            email=data.get('email'),
            title=data.get('title'),
            address=data.get('address'),
            city=data.get('city'),
            postal_code=data.get('postal_code'),
            business_type=data.get('business_type'),
            best_time_to_call=data.get('best_time_to_call'),
            source=data.get('source'),
            notes=data.get('notes')
        )
        
        try:
            db.session.add(lead)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'lead_id': lead.id})
            else:
                return redirect(url_for('leads_list'))
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': str(e)}), 400
            else:
                return render_template('new_lead.html', error=str(e))
    
    return render_template('new_lead.html')

@app.route('/leads/bulk-import', methods=['POST'])
def bulk_import_leads():
    """Import leads from CSV file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Read CSV data
        stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = pd.read_csv(stream)
        
        leads_created = 0
        errors = []
        
        for index, row in csv_input.iterrows():
            try:
                # Map CSV columns to Lead fields
                lead = Lead(
                    first_name=row.get('first_name', ''),
                    last_name=row.get('last_name', ''),
                    company_name=row.get('company_name', ''),
                    phone_number=row.get('phone_number', ''),
                    email=row.get('email', ''),
                    title=row.get('title', ''),
                    address=row.get('address', ''),
                    city=row.get('city', ''),
                    postal_code=row.get('postal_code', ''),
                    business_type=row.get('business_type', ''),
                    best_time_to_call=row.get('best_time_to_call', ''),
                    source='CSV Import',
                    notes=row.get('notes', '')
                )
                
                db.session.add(lead)
                leads_created += 1
                
            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'leads_created': leads_created,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to process CSV: {str(e)}'}), 400

@app.route('/leads/<lead_id>')
def lead_detail(lead_id):
    """Show detailed view of a specific lead"""
    lead = Lead.query.get_or_404(lead_id)
    calls = Call.query.filter_by(lead_id=lead_id).order_by(Call.created_at.desc()).all()
    scheduled_calls = ScheduledCall.query.filter_by(lead_id=lead_id).filter(
        ScheduledCall.status == 'scheduled'
    ).order_by(ScheduledCall.scheduled_for).all()
    
    return render_template('lead_detail.html', 
                         lead=lead, 
                         calls=calls, 
                         scheduled_calls=scheduled_calls)

@app.route('/campaigns')
def campaigns_list():
    """List all call campaigns"""
    campaigns = CallCampaign.query.order_by(CallCampaign.created_at.desc()).all()
    return render_template('campaigns.html', campaigns=campaigns)

@app.route('/campaigns/new', methods=['GET', 'POST'])
def new_campaign():
    """Create a new call campaign"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        campaign = CallCampaign(
            name=data.get('name'),
            description=data.get('description'),
            script_template=data.get('script_template'),
            max_calls_per_hour=int(data.get('max_calls_per_hour', 20)),
            max_calls_per_day=int(data.get('max_calls_per_day', 100)),
            start_time=data.get('start_time', '09:00'),
            end_time=data.get('end_time', '18:00'),
            working_days=data.getlist('working_days') if hasattr(data, 'getlist') else data.get('working_days', [])
        )
        
        try:
            db.session.add(campaign)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'campaign_id': campaign.id})
            else:
                return redirect(url_for('campaigns_list'))
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': str(e)}), 400
    
    return render_template('new_campaign.html')

@app.route('/api/leads/<lead_id>/call', methods=['POST'])
def initiate_call(lead_id):
    """API endpoint to initiate a call to a specific lead"""
    from call_manager import CallManager
    
    lead = Lead.query.get_or_404(lead_id)
    call_manager = CallManager()
    
    try:
        call_id = call_manager.initiate_call(lead)
        return jsonify({'success': True, 'call_id': call_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/status', methods=['GET'])
def get_call_status(call_id):
    """Get the current status of a call"""
    call = Call.query.get_or_404(call_id)
    return jsonify(call.to_dict())

@app.route('/api/calls/<call_id>/complete', methods=['POST'])
def complete_call(call_id):
    """Mark a call as completed and process results"""
    call = Call.query.get_or_404(call_id)
    data = request.get_json()
    
    call.status = CallStatus.COMPLETED
    call.ended_at = datetime.now(timezone.utc)
    call.duration_seconds = data.get('duration_seconds')
    call.transcription = data.get('transcription')
    call.summary = data.get('summary')
    call.sentiment_score = data.get('sentiment_score')
    call.call_outcome = data.get('call_outcome')
    call.next_action = data.get('next_action')
    
    # Update lead status based on call outcome
    if data.get('demo_scheduled'):
        call.lead.status = LeadStatus.DEMO_SCHEDULED
        call.demo_scheduled = True
        
        # Schedule the demo call
        if data.get('demo_date'):
            demo_date = datetime.fromisoformat(data.get('demo_date'))
            scheduled_call = ScheduledCall(
                lead_id=call.lead_id,
                scheduled_for=demo_date,
                call_type='demo',
                context=f"Demo scheduled from call on {call.started_at.strftime('%Y-%m-%d')}",
                agenda=data.get('demo_agenda', 'Product demonstration')
            )
            db.session.add(scheduled_call)
    
    elif data.get('follow_up_date'):
        call.lead.status = LeadStatus.FOLLOW_UP_SCHEDULED
        follow_up_date = datetime.fromisoformat(data.get('follow_up_date'))
        call.follow_up_date = follow_up_date
        
        # Schedule follow-up call
        scheduled_call = ScheduledCall(
            lead_id=call.lead_id,
            scheduled_for=follow_up_date,
            call_type='follow_up',
            context=data.get('follow_up_context', ''),
            agenda=data.get('follow_up_agenda', '')
        )
        db.session.add(scheduled_call)
    
    # Update last contacted
    call.lead.last_contacted = datetime.now(timezone.utc)
    call.lead.updated_at = datetime.now(timezone.utc)
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/bulk-call', methods=['POST'])
def bulk_call():
    """Start bulk calling for selected leads"""
    from call_scheduler import CallScheduler
    
    data = request.get_json()
    lead_ids = data.get('lead_ids', [])
    campaign_id = data.get('campaign_id')
    
    if not lead_ids:
        return jsonify({'error': 'No leads specified'}), 400
    
    try:
        scheduler = CallScheduler()
        job_id = scheduler.schedule_bulk_calls(lead_ids, campaign_id)
        
        return jsonify({
            'success': True, 
            'job_id': job_id,
            'message': f'Bulk calling scheduled for {len(lead_ids)} leads'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analytics')
def analytics():
    """Show analytics and reporting dashboard"""
    # Calculate key metrics
    total_calls = Call.query.count()
    successful_calls = Call.query.filter_by(status=CallStatus.COMPLETED).count()
    
    # Conversion rates
    demos_scheduled = Call.query.filter_by(demo_scheduled=True).count()
    
    # Call outcomes distribution
    outcomes = db.session.query(Call.call_outcome, db.func.count(Call.id)).group_by(Call.call_outcome).all()
    
    # Daily call volume (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    daily_calls = db.session.query(
        db.func.date(Call.created_at).label('date'),
        db.func.count(Call.id).label('count')
    ).filter(Call.created_at >= thirty_days_ago).group_by(db.func.date(Call.created_at)).all()
    
    analytics_data = {
        'total_calls': total_calls,
        'successful_calls': successful_calls,
        'success_rate': round((successful_calls / total_calls * 100) if total_calls > 0 else 0, 1),
        'demos_scheduled': demos_scheduled,
        'demo_rate': round((demos_scheduled / total_calls * 100) if total_calls > 0 else 0, 1),
        'outcomes': dict(outcomes),
        'daily_calls': [{'date': str(date), 'count': count} for date, count in daily_calls]
    }
    
    return render_template('analytics.html', analytics=analytics_data)

# API endpoint for getting leads data (for AJAX)
@app.route('/api/leads')
def api_leads():
    """API endpoint to get leads data"""
    leads = Lead.query.all()
    return jsonify([lead.to_dict() for lead in leads])

@app.route('/api/scheduled-calls')
def api_scheduled_calls():
    """API endpoint to get upcoming scheduled calls"""
    calls = ScheduledCall.query.filter(
        ScheduledCall.scheduled_for >= datetime.now(timezone.utc),
        ScheduledCall.status == 'scheduled'
    ).order_by(ScheduledCall.scheduled_for).all()
    
    return jsonify([call.to_dict() for call in calls])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)