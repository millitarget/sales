-- Cold Calling Automation System - Supabase Schema

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enum types
CREATE TYPE lead_status AS ENUM (
    'new',
    'contacted',
    'interested',
    'follow_up_scheduled',
    'demo_scheduled',
    'closed_won',
    'closed_lost',
    'do_not_call'
);

CREATE TYPE call_status AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'failed',
    'scheduled',
    'no_answer',
    'busy',
    'voicemail'
);

CREATE TYPE call_direction AS ENUM ('inbound', 'outbound');
CREATE TYPE call_type AS ENUM ('cold_call', 'follow_up', 'demo', 'check_in');
CREATE TYPE campaign_status AS ENUM ('draft', 'active', 'paused', 'completed');

-- Leads table
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Basic Information
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(200),
    title VARCHAR(100),
    
    -- Address Information
    address TEXT,
    city VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'Portugal',
    
    -- Business Information
    business_type VARCHAR(100),
    number_of_employees INTEGER,
    estimated_revenue DECIMAL(12, 2),
    
    -- Lead Management
    status lead_status DEFAULT 'new',
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    source VARCHAR(100),
    
    -- Call Management
    best_time_to_call VARCHAR(100),
    timezone VARCHAR(50) DEFAULT 'Europe/Lisbon',
    preferred_language VARCHAR(20) DEFAULT 'Portuguese',
    
    -- Tracking
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_contacted TIMESTAMPTZ,
    
    -- Notes and Context
    notes TEXT,
    custom_fields JSONB DEFAULT '{}'::jsonb
);

-- Calls table
CREATE TABLE IF NOT EXISTS calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    
    -- Call Details
    status call_status DEFAULT 'pending',
    direction call_direction DEFAULT 'outbound',
    duration_seconds INTEGER,
    
    -- Timing
    scheduled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Call Content
    transcription TEXT,
    summary TEXT,
    sentiment_score DECIMAL(3, 2) CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    
    -- Outcomes
    call_outcome VARCHAR(100),
    next_action VARCHAR(200),
    follow_up_date TIMESTAMPTZ,
    demo_scheduled BOOLEAN DEFAULT FALSE,
    
    -- Technical Details
    livekit_room_name VARCHAR(200),
    livekit_session_id VARCHAR(200),
    recording_url TEXT,
    call_sid VARCHAR(100), -- Twilio/telephony provider ID
    
    -- Analysis
    keywords_mentioned JSONB DEFAULT '[]'::jsonb,
    objections_raised JSONB DEFAULT '[]'::jsonb,
    pain_points_identified JSONB DEFAULT '[]'::jsonb
);

-- Scheduled Calls table
CREATE TABLE IF NOT EXISTS scheduled_calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    
    -- Scheduling Details
    scheduled_for TIMESTAMPTZ NOT NULL,
    call_type call_type DEFAULT 'follow_up',
    
    -- Status
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled', 'rescheduled', 'missed', 'failed')),
    
    -- Context for the call
    context TEXT,
    agenda TEXT,
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    
    -- Tracking
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Result when completed
    call_id UUID REFERENCES calls(id)
);

-- Call Campaigns table
CREATE TABLE IF NOT EXISTS call_campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Campaign Details
    name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Configuration
    script_template TEXT,
    max_calls_per_hour INTEGER DEFAULT 20,
    max_calls_per_day INTEGER DEFAULT 100,
    
    -- Timing
    start_time TIME DEFAULT '09:00',
    end_time TIME DEFAULT '18:00',
    working_days JSONB DEFAULT '["monday", "tuesday", "wednesday", "thursday", "friday"]'::jsonb,
    
    -- Status
    status campaign_status DEFAULT 'draft',
    
    -- Statistics
    total_leads INTEGER DEFAULT 0,
    calls_made INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    demos_scheduled INTEGER DEFAULT 0,
    
    -- Tracking
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Campaign Leads (many-to-many relationship)
CREATE TABLE IF NOT EXISTS campaign_leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES call_campaigns(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    call_order INTEGER,
    UNIQUE(campaign_id, lead_id)
);

-- Call Events (for tracking call progress)
CREATE TABLE IF NOT EXISTS call_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    call_id UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- System Configuration
CREATE TABLE IF NOT EXISTS system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_phone ON leads(phone_number);
CREATE INDEX idx_leads_company ON leads(company_name);
CREATE INDEX idx_leads_last_contacted ON leads(last_contacted);

CREATE INDEX idx_calls_lead_id ON calls(lead_id);
CREATE INDEX idx_calls_status ON calls(status);
CREATE INDEX idx_calls_created_at ON calls(created_at);
CREATE INDEX idx_calls_scheduled_at ON calls(scheduled_at);

CREATE INDEX idx_scheduled_calls_lead_id ON scheduled_calls(lead_id);
CREATE INDEX idx_scheduled_calls_scheduled_for ON scheduled_calls(scheduled_for);
CREATE INDEX idx_scheduled_calls_status ON scheduled_calls(status);

CREATE INDEX idx_campaigns_status ON call_campaigns(status);
CREATE INDEX idx_campaign_leads_campaign ON campaign_leads(campaign_id);
CREATE INDEX idx_campaign_leads_lead ON campaign_leads(lead_id);

-- Updated at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_scheduled_calls_updated_at BEFORE UPDATE ON scheduled_calls
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON call_campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Row Level Security (RLS)
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_campaigns ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust based on your auth setup)
-- Example: Allow authenticated users to see all data
CREATE POLICY "Allow authenticated read access" ON leads
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow authenticated write access" ON leads
    FOR ALL USING (auth.role() = 'authenticated');

-- Repeat for other tables...

-- Functions for analytics
CREATE OR REPLACE FUNCTION get_lead_statistics()
RETURNS TABLE (
    total_leads BIGINT,
    new_leads BIGINT,
    contacted_leads BIGINT,
    interested_leads BIGINT,
    demos_scheduled BIGINT,
    closed_won BIGINT,
    conversion_rate DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_leads,
        COUNT(*) FILTER (WHERE status = 'new')::BIGINT as new_leads,
        COUNT(*) FILTER (WHERE status IN ('contacted', 'interested', 'follow_up_scheduled'))::BIGINT as contacted_leads,
        COUNT(*) FILTER (WHERE status = 'interested')::BIGINT as interested_leads,
        COUNT(*) FILTER (WHERE status = 'demo_scheduled')::BIGINT as demos_scheduled,
        COUNT(*) FILTER (WHERE status = 'closed_won')::BIGINT as closed_won,
        CASE 
            WHEN COUNT(*) > 0 THEN ROUND((COUNT(*) FILTER (WHERE status = 'closed_won')::DECIMAL / COUNT(*) * 100), 2)
            ELSE 0
        END as conversion_rate
    FROM leads;
END;
$$ LANGUAGE plpgsql;

-- Function to get upcoming calls
CREATE OR REPLACE FUNCTION get_upcoming_calls(hours_ahead INTEGER DEFAULT 24)
RETURNS TABLE (
    id UUID,
    lead_id UUID,
    lead_name TEXT,
    company_name VARCHAR(200),
    scheduled_for TIMESTAMPTZ,
    call_type call_type,
    context TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sc.id,
        sc.lead_id,
        l.first_name || ' ' || l.last_name as lead_name,
        l.company_name,
        sc.scheduled_for,
        sc.call_type,
        sc.context
    FROM scheduled_calls sc
    JOIN leads l ON sc.lead_id = l.id
    WHERE sc.scheduled_for >= NOW() 
        AND sc.scheduled_for <= NOW() + INTERVAL '1 hour' * hours_ahead
        AND sc.status = 'scheduled'
    ORDER BY sc.scheduled_for;
END;
$$ LANGUAGE plpgsql;