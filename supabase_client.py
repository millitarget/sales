"""
Supabase Client for Cold Calling Automation System
Handles all database operations with Supabase backend
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv('.env.local')

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Supabase client for all database operations"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.client: Client = create_client(self.url, self.key)
        logger.info("Supabase client initialized")
    
    # Lead Management
    
    def create_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new lead"""
        try:
            response = self.client.table('leads').insert(lead_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating lead: {e}")
            raise
    
    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get a lead by ID"""
        try:
            response = self.client.table('leads').select("*").eq('id', lead_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting lead: {e}")
            return None
    
    def get_lead_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get a lead by phone number"""
        try:
            response = self.client.table('leads').select("*").eq('phone_number', phone_number).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting lead by phone: {e}")
            return None
    
    def update_lead(self, lead_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a lead"""
        try:
            response = self.client.table('leads').update(update_data).eq('id', lead_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating lead: {e}")
            raise
    
    def get_leads(self, filters: Dict[str, Any] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get leads with optional filters"""
        try:
            query = self.client.table('leads').select("*")
            
            if filters:
                if 'status' in filters:
                    query = query.eq('status', filters['status'])
                if 'city' in filters:
                    query = query.eq('city', filters['city'])
                if 'business_type' in filters:
                    query = query.eq('business_type', filters['business_type'])
            
            query = query.order('created_at', desc=True).limit(limit)
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting leads: {e}")
            return []
    
    def bulk_create_leads(self, leads_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bulk create leads"""
        try:
            response = self.client.table('leads').insert(leads_data).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error bulk creating leads: {e}")
            raise
    
    # Call Management
    
    def create_call(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new call record"""
        try:
            response = self.client.table('calls').insert(call_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating call: {e}")
            raise
    
    def get_call(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get a call by ID"""
        try:
            response = self.client.table('calls').select("*, lead:leads(*)").eq('id', call_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting call: {e}")
            return None
    
    def update_call(self, call_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a call record"""
        try:
            response = self.client.table('calls').update(update_data).eq('id', call_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating call: {e}")
            raise
    
    def get_calls_for_lead(self, lead_id: str) -> List[Dict[str, Any]]:
        """Get all calls for a specific lead"""
        try:
            response = self.client.table('calls').select("*").eq('lead_id', lead_id).order('created_at', desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting calls for lead: {e}")
            return []
    
    def get_recent_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent calls"""
        try:
            response = self.client.table('calls').select("*, lead:leads(*)").order('created_at', desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting recent calls: {e}")
            return []
    
    def create_call_event(self, call_id: str, event_type: str, event_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a call event"""
        try:
            data = {
                'call_id': call_id,
                'event_type': event_type,
                'event_data': event_data or {}
            }
            response = self.client.table('call_events').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating call event: {e}")
            raise
    
    # Scheduled Calls Management
    
    def create_scheduled_call(self, scheduled_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a scheduled call"""
        try:
            response = self.client.table('scheduled_calls').insert(scheduled_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating scheduled call: {e}")
            raise
    
    def get_scheduled_call(self, scheduled_call_id: str) -> Optional[Dict[str, Any]]:
        """Get a scheduled call by ID"""
        try:
            response = self.client.table('scheduled_calls').select("*, lead:leads(*)").eq('id', scheduled_call_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting scheduled call: {e}")
            return None
    
    def update_scheduled_call(self, scheduled_call_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a scheduled call"""
        try:
            response = self.client.table('scheduled_calls').update(update_data).eq('id', scheduled_call_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating scheduled call: {e}")
            raise
    
    def get_upcoming_scheduled_calls(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming scheduled calls"""
        try:
            response = self.client.rpc('get_upcoming_calls', {'hours_ahead': hours}).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting upcoming calls: {e}")
            return []
    
    def get_overdue_scheduled_calls(self, minutes: int = 30) -> List[Dict[str, Any]]:
        """Get overdue scheduled calls"""
        try:
            cutoff_time = datetime.now(timezone.utc).isoformat()
            response = self.client.table('scheduled_calls').select("*, lead:leads(*)")\
                .lt('scheduled_for', cutoff_time)\
                .eq('status', 'scheduled')\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting overdue calls: {e}")
            return []
    
    # Campaign Management
    
    def create_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new campaign"""
        try:
            response = self.client.table('call_campaigns').insert(campaign_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            raise
    
    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get a campaign by ID"""
        try:
            response = self.client.table('call_campaigns').select("*").eq('id', campaign_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting campaign: {e}")
            return None
    
    def update_campaign(self, campaign_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a campaign"""
        try:
            response = self.client.table('call_campaigns').update(update_data).eq('id', campaign_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating campaign: {e}")
            raise
    
    def get_active_campaigns(self) -> List[Dict[str, Any]]:
        """Get all active campaigns"""
        try:
            response = self.client.table('call_campaigns').select("*").eq('status', 'active').execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting active campaigns: {e}")
            return []
    
    def add_leads_to_campaign(self, campaign_id: str, lead_ids: List[str]) -> List[Dict[str, Any]]:
        """Add multiple leads to a campaign"""
        try:
            data = [
                {'campaign_id': campaign_id, 'lead_id': lead_id}
                for lead_id in lead_ids
            ]
            response = self.client.table('campaign_leads').insert(data).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error adding leads to campaign: {e}")
            raise
    
    def get_campaign_leads(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Get all leads in a campaign"""
        try:
            response = self.client.table('campaign_leads').select("*, lead:leads(*)")\
                .eq('campaign_id', campaign_id)\
                .order('call_order', desc=False)\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting campaign leads: {e}")
            return []
    
    # Analytics
    
    def get_lead_statistics(self) -> Dict[str, Any]:
        """Get lead statistics"""
        try:
            response = self.client.rpc('get_lead_statistics').execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error getting lead statistics: {e}")
            return {}
    
    def get_call_analytics(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get call analytics"""
        try:
            query = self.client.table('calls').select("status, call_outcome, demo_scheduled")
            
            if start_date:
                query = query.gte('created_at', start_date)
            if end_date:
                query = query.lte('created_at', end_date)
            
            response = query.execute()
            
            # Process analytics
            total_calls = len(response.data)
            completed_calls = sum(1 for call in response.data if call['status'] == 'completed')
            demos_scheduled = sum(1 for call in response.data if call.get('demo_scheduled'))
            
            outcomes = {}
            for call in response.data:
                outcome = call.get('call_outcome', 'unknown')
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
            
            return {
                'total_calls': total_calls,
                'completed_calls': completed_calls,
                'success_rate': (completed_calls / total_calls * 100) if total_calls > 0 else 0,
                'demos_scheduled': demos_scheduled,
                'demo_rate': (demos_scheduled / total_calls * 100) if total_calls > 0 else 0,
                'outcomes': outcomes
            }
        except Exception as e:
            logger.error(f"Error getting call analytics: {e}")
            return {}
    
    # System Configuration
    
    def get_config(self, key: str) -> Any:
        """Get system configuration value"""
        try:
            response = self.client.table('system_config').select("value").eq('key', key).execute()
            if response.data:
                return response.data[0]['value']
            return None
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return None
    
    def set_config(self, key: str, value: Any) -> Dict[str, Any]:
        """Set system configuration value"""
        try:
            data = {
                'key': key,
                'value': value if isinstance(value, dict) else {'value': value}
            }
            response = self.client.table('system_config').upsert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error setting config: {e}")
            raise

# Create a singleton instance
supabase_client = SupabaseClient()