from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, String, Text, Boolean, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship, DeclarativeBase
from enum import Enum
import uuid

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class CallStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    VOICEMAIL = "voicemail"

class LeadStatus(Enum):
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    FOLLOW_UP_SCHEDULED = "follow_up_scheduled"
    DEMO_SCHEDULED = "demo_scheduled"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    DO_NOT_CALL = "do_not_call"

class Lead(db.Model):
    __tablename__ = 'leads'
    
    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic Information
    first_name = db.Column(String(100), nullable=False)
    last_name = db.Column(String(100), nullable=False)
    company_name = db.Column(String(200), nullable=False)
    phone_number = db.Column(String(20), nullable=False, unique=True)
    email = db.Column(String(200))
    title = db.Column(String(100))
    
    # Address Information
    address = db.Column(String(500))
    city = db.Column(String(100))
    postal_code = db.Column(String(20))
    country = db.Column(String(100), default="Portugal")
    
    # Business Information
    business_type = db.Column(String(100))  # Restaurant, Cafe, Bar, etc.
    number_of_employees = db.Column(Integer)
    estimated_revenue = db.Column(Float)
    
    # Lead Management
    status = db.Column(db.Enum(LeadStatus), default=LeadStatus.NEW)
    priority = db.Column(Integer, default=5)  # 1-10 scale
    source = db.Column(String(100))  # Where did we get this lead
    
    # Call Management
    best_time_to_call = db.Column(String(100))  # "mornings", "afternoons", "10:00-12:00"
    timezone = db.Column(String(50), default="Europe/Lisbon")
    preferred_language = db.Column(String(20), default="Portuguese")
    
    # Tracking
    created_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_contacted = db.Column(DateTime(timezone=True))
    
    # Notes and Context
    notes = db.Column(Text)
    custom_fields = db.Column(JSON)  # For additional flexible data storage
    
    # Relationships
    calls = relationship("Call", back_populates="lead", cascade="all, delete-orphan")
    scheduled_calls = relationship("ScheduledCall", back_populates="lead", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Lead {self.first_name} {self.last_name} - {self.company_name}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'company_name': self.company_name,
            'phone_number': self.phone_number,
            'email': self.email,
            'title': self.title,
            'status': self.status.value if self.status else None,
            'priority': self.priority,
            'source': self.source,
            'best_time_to_call': self.best_time_to_call,
            'last_contacted': self.last_contacted.isoformat() if self.last_contacted else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'notes': self.notes,
            'total_calls': len(self.calls),
            'last_call_status': self.calls[-1].status.value if self.calls else None
        }

class Call(db.Model):
    __tablename__ = 'calls'
    
    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = db.Column(String(36), ForeignKey('leads.id'), nullable=False)
    
    # Call Details
    status = db.Column(db.Enum(CallStatus), default=CallStatus.PENDING)
    direction = db.Column(String(20), default="outbound")  # outbound, inbound
    duration_seconds = db.Column(Integer)
    
    # Timing
    scheduled_at = db.Column(DateTime(timezone=True))
    started_at = db.Column(DateTime(timezone=True))
    ended_at = db.Column(DateTime(timezone=True))
    created_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Call Content
    transcription = db.Column(Text)
    summary = db.Column(Text)
    sentiment_score = db.Column(Float)  # -1 to 1, negative to positive
    
    # Outcomes
    call_outcome = db.Column(String(100))  # "interested", "not_interested", "callback_requested", etc.
    next_action = db.Column(String(200))
    follow_up_date = db.Column(DateTime(timezone=True))
    demo_scheduled = db.Column(Boolean, default=False)
    
    # Technical Details
    livekit_room_name = db.Column(String(200))
    livekit_session_id = db.Column(String(200))
    recording_url = db.Column(String(500))
    
    # Analysis
    keywords_mentioned = db.Column(JSON)  # Array of important keywords detected
    objections_raised = db.Column(JSON)  # Array of objections and how they were handled
    pain_points_identified = db.Column(JSON)  # Business pain points discovered
    
    # Relationships
    lead = relationship("Lead", back_populates="calls")
    
    def __repr__(self):
        return f'<Call {self.id} - {self.lead.company_name} - {self.status.value}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'status': self.status.value if self.status else None,
            'direction': self.direction,
            'duration_seconds': self.duration_seconds,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'transcription': self.transcription,
            'summary': self.summary,
            'sentiment_score': self.sentiment_score,
            'call_outcome': self.call_outcome,
            'next_action': self.next_action,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'demo_scheduled': self.demo_scheduled,
            'keywords_mentioned': self.keywords_mentioned,
            'objections_raised': self.objections_raised,
            'pain_points_identified': self.pain_points_identified
        }

class ScheduledCall(db.Model):
    __tablename__ = 'scheduled_calls'
    
    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = db.Column(String(36), ForeignKey('leads.id'), nullable=False)
    
    # Scheduling Details
    scheduled_for = db.Column(DateTime(timezone=True), nullable=False)
    call_type = db.Column(String(50), default="follow_up")  # follow_up, demo, check_in
    
    # Status
    status = db.Column(String(20), default="scheduled")  # scheduled, completed, cancelled, rescheduled
    
    # Context for the call
    context = db.Column(Text)  # What happened in previous calls, what to discuss
    agenda = db.Column(Text)  # Specific agenda items
    priority = db.Column(Integer, default=5)  # 1-10 priority
    
    # Tracking
    created_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Result when completed
    call_id = db.Column(String(36), ForeignKey('calls.id'))  # Link to actual call when executed
    
    # Relationships
    lead = relationship("Lead", back_populates="scheduled_calls")
    
    def __repr__(self):
        return f'<ScheduledCall {self.id} - {self.lead.company_name} - {self.scheduled_for}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'call_type': self.call_type,
            'status': self.status,
            'context': self.context,
            'agenda': self.agenda,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'call_id': self.call_id
        }

class CallCampaign(db.Model):
    __tablename__ = 'call_campaigns'
    
    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Campaign Details
    name = db.Column(String(200), nullable=False)
    description = db.Column(Text)
    
    # Configuration
    script_template = db.Column(Text)  # Custom script for this campaign
    max_calls_per_hour = db.Column(Integer, default=20)
    max_calls_per_day = db.Column(Integer, default=100)
    
    # Timing
    start_time = db.Column(String(10), default="09:00")  # Daily start time
    end_time = db.Column(String(10), default="18:00")   # Daily end time
    working_days = db.Column(JSON, default=["monday", "tuesday", "wednesday", "thursday", "friday"])
    
    # Status
    status = db.Column(String(20), default="draft")  # draft, active, paused, completed
    
    # Statistics
    total_leads = db.Column(Integer, default=0)
    calls_made = db.Column(Integer, default=0)
    successful_calls = db.Column(Integer, default=0)
    demos_scheduled = db.Column(Integer, default=0)
    
    # Tracking
    created_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    started_at = db.Column(DateTime(timezone=True))
    completed_at = db.Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f'<CallCampaign {self.name} - {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'max_calls_per_hour': self.max_calls_per_hour,
            'max_calls_per_day': self.max_calls_per_day,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'working_days': self.working_days,
            'status': self.status,
            'total_leads': self.total_leads,
            'calls_made': self.calls_made,
            'successful_calls': self.successful_calls,
            'demos_scheduled': self.demos_scheduled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }