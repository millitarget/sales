import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import time
import threading
from queue import Queue
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import pytz

from models import db, Lead, Call, ScheduledCall, CallCampaign, CallStatus, LeadStatus
from call_manager import CallManager

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("call_scheduler")

class CallScheduler:
    """Manages bulk calling operations and scheduled call execution"""
    
    def __init__(self):
        self.call_manager = CallManager()
        self.scheduler = BackgroundScheduler(timezone=pytz.UTC)
        self.scheduler.start()
        self.call_queue = Queue()
        self.active_campaigns = {}
        self.is_running = False
        
        # Start the call processor thread
        self.processor_thread = threading.Thread(target=self._process_call_queue, daemon=True)
        self.processor_thread.start()
        
        # Schedule recurring jobs
        self._schedule_recurring_jobs()
        
        log.info("CallScheduler initialized and started")
    
    def schedule_bulk_calls(self, lead_ids: List[str], campaign_id: str = None) -> str:
        """
        Schedule bulk calls for a list of leads
        
        Args:
            lead_ids: List of lead IDs to call
            campaign_id: Optional campaign ID for tracking
            
        Returns:
            job_id: Unique identifier for this bulk calling job
        """
        job_id = str(uuid.uuid4())
        
        # Get campaign settings if provided
        campaign = None
        if campaign_id:
            campaign = CallCampaign.query.get(campaign_id)
        
        # Default settings
        max_calls_per_hour = campaign.max_calls_per_hour if campaign else 20
        start_time = campaign.start_time if campaign else "09:00"
        end_time = campaign.end_time if campaign else "18:00"
        working_days = campaign.working_days if campaign else ["monday", "tuesday", "wednesday", "thursday", "friday"]
        
        # Get leads
        leads = Lead.query.filter(Lead.id.in_(lead_ids)).all()
        
        log.info(f"Scheduling bulk calls for {len(leads)} leads (job: {job_id})")
        
        # Calculate call schedule respecting timing constraints
        call_times = self._calculate_call_schedule(
            len(leads), 
            max_calls_per_hour, 
            start_time, 
            end_time, 
            working_days
        )
        
        # Schedule each call
        for i, lead in enumerate(leads):
            if i < len(call_times):
                scheduled_time = call_times[i]
                
                # Create scheduled call entry
                scheduled_call = ScheduledCall(
                    lead_id=lead.id,
                    scheduled_for=scheduled_time,
                    call_type='cold_call',
                    context=f"Bulk call campaign {campaign.name if campaign else 'Direct'}"
                )
                db.session.add(scheduled_call)
                
                # Schedule with APScheduler
                self.scheduler.add_job(
                    func=self._execute_scheduled_call,
                    trigger=DateTrigger(run_date=scheduled_time),
                    args=[scheduled_call.id],
                    id=f"call_{scheduled_call.id}",
                    name=f"Call {lead.full_name} at {lead.company_name}"
                )
        
        db.session.commit()
        
        # Track the campaign
        self.active_campaigns[job_id] = {
            'campaign_id': campaign_id,
            'leads_count': len(leads),
            'calls_scheduled': len(call_times),
            'started_at': datetime.now(timezone.utc)
        }
        
        log.info(f"Scheduled {len(call_times)} calls for bulk job {job_id}")
        return job_id
    
    def _calculate_call_schedule(self, 
                               num_calls: int, 
                               max_calls_per_hour: int, 
                               start_time: str, 
                               end_time: str, 
                               working_days: List[str]) -> List[datetime]:
        """
        Calculate optimal scheduling times for calls
        """
        schedule = []
        current_time = datetime.now(timezone.utc)
        
        # Convert working days to numbers (0=Monday)
        day_mapping = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 
            'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
        }
        working_day_nums = [day_mapping[day.lower()] for day in working_days]
        
        # Parse start and end times
        start_hour, start_minute = map(int, start_time.split(':'))
        end_hour, end_minute = map(int, end_time.split(':'))
        
        # Calculate minutes between calls
        minutes_between_calls = 60 / max_calls_per_hour
        
        calls_scheduled = 0
        day_offset = 0
        
        while calls_scheduled < num_calls:
            # Calculate the date to check
            check_date = current_time + timedelta(days=day_offset)
            
            # Skip non-working days
            if check_date.weekday() not in working_day_nums:
                day_offset += 1
                continue
            
            # Calculate available slots for this day
            day_start = check_date.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            day_end = check_date.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
            
            # Skip if day has already passed
            if day_end < current_time:
                day_offset += 1
                continue
            
            # Adjust start time if it's today and current time is after start
            if day_offset == 0 and current_time > day_start:
                # Round up to next call slot
                minutes_since_start = (current_time - day_start).total_seconds() / 60
                next_slot = int(minutes_since_start / minutes_between_calls) + 1
                day_start = day_start + timedelta(minutes=next_slot * minutes_between_calls)
            
            # Schedule calls for this day
            current_slot_time = day_start
            while current_slot_time <= day_end and calls_scheduled < num_calls:
                schedule.append(current_slot_time)
                calls_scheduled += 1
                current_slot_time += timedelta(minutes=minutes_between_calls)
            
            day_offset += 1
        
        return schedule
    
    def _execute_scheduled_call(self, scheduled_call_id: str):
        """Execute a scheduled call"""
        try:
            scheduled_call = ScheduledCall.query.get(scheduled_call_id)
            if not scheduled_call:
                log.error(f"Scheduled call {scheduled_call_id} not found")
                return
            
            if scheduled_call.status != 'scheduled':
                log.info(f"Scheduled call {scheduled_call_id} is not in scheduled status")
                return
            
            lead = scheduled_call.lead
            log.info(f"Executing scheduled call to {lead.full_name} at {lead.company_name}")
            
            # Add context from scheduled call
            context = scheduled_call.context or ""
            if scheduled_call.agenda:
                context += f"\nAgenda: {scheduled_call.agenda}"
            
            # Initiate the call
            call_id = self.call_manager.initiate_call(lead, context)
            
            # Update scheduled call record
            scheduled_call.status = 'completed'
            scheduled_call.call_id = call_id
            db.session.commit()
            
            log.info(f"Scheduled call {scheduled_call_id} executed successfully as call {call_id}")
            
        except Exception as e:
            log.error(f"Failed to execute scheduled call {scheduled_call_id}: {str(e)}")
            
            # Mark as failed
            try:
                scheduled_call = ScheduledCall.query.get(scheduled_call_id)
                if scheduled_call:
                    scheduled_call.status = 'failed'
                    db.session.commit()
            except:
                pass
    
    def _schedule_recurring_jobs(self):
        """Schedule recurring maintenance jobs"""
        
        # Check for overdue scheduled calls every 5 minutes
        self.scheduler.add_job(
            func=self._check_overdue_calls,
            trigger='interval',
            minutes=5,
            id='check_overdue_calls',
            name='Check Overdue Calls'
        )
        
        # Process follow-up scheduling every hour
        self.scheduler.add_job(
            func=self._process_follow_ups,
            trigger='interval',
            hours=1,
            id='process_follow_ups',
            name='Process Follow-ups'
        )
        
        # Generate daily reports at 9 AM
        self.scheduler.add_job(
            func=self._generate_daily_report,
            trigger='cron',
            hour=9,
            minute=0,
            id='daily_report',
            name='Generate Daily Report'
        )
    
    def _check_overdue_calls(self):
        """Check for overdue scheduled calls and handle them"""
        try:
            # Find calls that are more than 30 minutes overdue
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            overdue_calls = ScheduledCall.query.filter(
                ScheduledCall.scheduled_for < cutoff_time,
                ScheduledCall.status == 'scheduled'
            ).all()
            
            for scheduled_call in overdue_calls:
                log.warning(f"Scheduled call {scheduled_call.id} is overdue")
                
                # Try to execute now or reschedule
                if self._should_reschedule_call(scheduled_call):
                    self._reschedule_call(scheduled_call)
                else:
                    # Mark as missed
                    scheduled_call.status = 'missed'
                    db.session.commit()
                    
        except Exception as e:
            log.error(f"Error checking overdue calls: {str(e)}")
    
    def _should_reschedule_call(self, scheduled_call: ScheduledCall) -> bool:
        """Determine if an overdue call should be rescheduled"""
        
        # Check if it's still within business hours
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        
        # Simple business hours check (9 AM to 6 PM)
        if 9 <= current_hour <= 18:
            return True
        
        return False
    
    def _reschedule_call(self, scheduled_call: ScheduledCall):
        """Reschedule an overdue call to next available slot"""
        try:
            # Calculate next available time slot
            next_slot = datetime.now(timezone.utc) + timedelta(minutes=30)
            
            # Update the scheduled call
            scheduled_call.scheduled_for = next_slot
            scheduled_call.context += f"\n[Rescheduled from {scheduled_call.scheduled_for}]"
            
            # Reschedule with APScheduler
            self.scheduler.add_job(
                func=self._execute_scheduled_call,
                trigger=DateTrigger(run_date=next_slot),
                args=[scheduled_call.id],
                id=f"call_{scheduled_call.id}_rescheduled",
                name=f"Rescheduled call {scheduled_call.lead.full_name}"
            )
            
            db.session.commit()
            log.info(f"Rescheduled call {scheduled_call.id} to {next_slot}")
            
        except Exception as e:
            log.error(f"Failed to reschedule call {scheduled_call.id}: {str(e)}")
    
    def _process_follow_ups(self):
        """Process automatic follow-up scheduling based on call outcomes"""
        try:
            # Find completed calls that need follow-ups but don't have them scheduled
            recent_calls = Call.query.filter(
                Call.status == CallStatus.COMPLETED,
                Call.ended_at >= datetime.now(timezone.utc) - timedelta(days=7),
                Call.next_action.like('%follow%')
            ).all()
            
            for call in recent_calls:
                # Check if follow-up is already scheduled
                existing_follow_up = ScheduledCall.query.filter(
                    ScheduledCall.lead_id == call.lead_id,
                    ScheduledCall.call_type == 'follow_up',
                    ScheduledCall.status == 'scheduled'
                ).first()
                
                if not existing_follow_up:
                    self._auto_schedule_follow_up(call)
                    
        except Exception as e:
            log.error(f"Error processing follow-ups: {str(e)}")
    
    def _auto_schedule_follow_up(self, call: Call):
        """Automatically schedule a follow-up call based on call outcome"""
        try:
            # Determine follow-up timing based on outcome
            follow_up_delay = timedelta(days=7)  # Default 1 week
            
            if call.call_outcome == 'interested':
                follow_up_delay = timedelta(days=3)  # Quick follow-up for interested leads
            elif call.call_outcome == 'callback_requested':
                follow_up_delay = timedelta(days=1)  # Next day for callback requests
            elif call.call_outcome == 'not_interested':
                follow_up_delay = timedelta(days=90)  # Quarterly follow-up
            
            follow_up_time = call.ended_at + follow_up_delay
            
            # Create scheduled follow-up
            scheduled_call = ScheduledCall(
                lead_id=call.lead_id,
                scheduled_for=follow_up_time,
                call_type='follow_up',
                context=f"Auto-scheduled follow-up from call on {call.ended_at.strftime('%Y-%m-%d')}. Previous outcome: {call.call_outcome}",
                agenda=call.next_action or "Follow-up call"
            )
            
            db.session.add(scheduled_call)
            db.session.commit()
            
            # Schedule with APScheduler
            self.scheduler.add_job(
                func=self._execute_scheduled_call,
                trigger=DateTrigger(run_date=follow_up_time),
                args=[scheduled_call.id],
                id=f"follow_up_{scheduled_call.id}",
                name=f"Follow-up call {call.lead.full_name}"
            )
            
            log.info(f"Auto-scheduled follow-up for lead {call.lead.full_name} on {follow_up_time}")
            
        except Exception as e:
            log.error(f"Failed to auto-schedule follow-up for call {call.id}: {str(e)}")
    
    def _generate_daily_report(self):
        """Generate daily calling activity report"""
        try:
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Get daily statistics
            daily_calls = Call.query.filter(
                Call.created_at >= yesterday_start,
                Call.created_at <= yesterday_end
            ).all()
            
            stats = {
                'total_calls': len(daily_calls),
                'completed_calls': len([c for c in daily_calls if c.status == CallStatus.COMPLETED]),
                'demos_scheduled': len([c for c in daily_calls if c.demo_scheduled]),
                'interested_leads': len([c for c in daily_calls if c.call_outcome == 'interested']),
                'follow_ups_needed': len([c for c in daily_calls if 'follow' in (c.next_action or '').lower()])
            }
            
            log.info(f"Daily Report for {yesterday_start.strftime('%Y-%m-%d')}: {stats}")
            
            # In a production system, you might want to:
            # - Send this report via email
            # - Store it in the database
            # - Push to a dashboard
            
        except Exception as e:
            log.error(f"Failed to generate daily report: {str(e)}")
    
    def get_upcoming_calls(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming scheduled calls within specified hours"""
        cutoff_time = datetime.now(timezone.utc) + timedelta(hours=hours)
        
        upcoming = ScheduledCall.query.filter(
            ScheduledCall.scheduled_for <= cutoff_time,
            ScheduledCall.scheduled_for >= datetime.now(timezone.utc),
            ScheduledCall.status == 'scheduled'
        ).order_by(ScheduledCall.scheduled_for).all()
        
        return [call.to_dict() for call in upcoming]
    
    def cancel_scheduled_call(self, scheduled_call_id: str) -> bool:
        """Cancel a scheduled call"""
        try:
            scheduled_call = ScheduledCall.query.get(scheduled_call_id)
            if not scheduled_call:
                return False
            
            # Remove from scheduler
            try:
                self.scheduler.remove_job(f"call_{scheduled_call_id}")
            except:
                pass  # Job might not exist in scheduler
            
            # Update status
            scheduled_call.status = 'cancelled'
            db.session.commit()
            
            log.info(f"Cancelled scheduled call {scheduled_call_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to cancel scheduled call {scheduled_call_id}: {str(e)}")
            return False
    
    def reschedule_call(self, scheduled_call_id: str, new_time: datetime) -> bool:
        """Reschedule a call to a new time"""
        try:
            scheduled_call = ScheduledCall.query.get(scheduled_call_id)
            if not scheduled_call:
                return False
            
            # Remove old job
            try:
                self.scheduler.remove_job(f"call_{scheduled_call_id}")
            except:
                pass
            
            # Update scheduled time
            old_time = scheduled_call.scheduled_for
            scheduled_call.scheduled_for = new_time
            scheduled_call.context += f"\n[Rescheduled from {old_time} to {new_time}]"
            
            # Add new job
            self.scheduler.add_job(
                func=self._execute_scheduled_call,
                trigger=DateTrigger(run_date=new_time),
                args=[scheduled_call_id],
                id=f"call_{scheduled_call_id}_rescheduled",
                name=f"Rescheduled call {scheduled_call.lead.full_name}"
            )
            
            db.session.commit()
            
            log.info(f"Rescheduled call {scheduled_call_id} from {old_time} to {new_time}")
            return True
            
        except Exception as e:
            log.error(f"Failed to reschedule call {scheduled_call_id}: {str(e)}")
            return False
    
    def _process_call_queue(self):
        """Background thread to process the call queue"""
        while True:
            try:
                if not self.call_queue.empty():
                    call_item = self.call_queue.get()
                    # Process the call item
                    self._process_queue_item(call_item)
                    self.call_queue.task_done()
                else:
                    time.sleep(1)  # Wait a bit before checking again
            except Exception as e:
                log.error(f"Error processing call queue: {str(e)}")
                time.sleep(5)  # Wait longer on error
    
    def _process_queue_item(self, call_item: Dict[str, Any]):
        """Process a single item from the call queue"""
        try:
            # This could be used for immediate calling or other queue-based operations
            pass
        except Exception as e:
            log.error(f"Error processing queue item: {str(e)}")
    
    def shutdown(self):
        """Shutdown the scheduler gracefully"""
        log.info("Shutting down CallScheduler...")
        self.scheduler.shutdown()
        self.is_running = False