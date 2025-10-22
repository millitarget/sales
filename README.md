# Cold Calling Automation System

A powerful, production-ready cold calling automation system that combines AI-powered voice agents, automated scheduling, and comprehensive CRM features. Built with **Supabase** (backend), **Twilio** (telephony), **LiveKit** (real-time voice), and **OpenAI** (AI conversations).

## 🚀 Key Features

### Core Functionality
- **Real Phone Calls**: Make actual calls via Twilio to any phone number
- **AI Sales Agent**: Portuguese-speaking AI agent (Ana Sousa) powered by GPT-4
- **Automated Scheduling**: Smart call scheduling with business hours compliance
- **Call Transcription**: Automatic transcription and analysis of all calls
- **Lead Management**: Full CRM with lead tracking and status progression
- **Bulk Operations**: Import and call hundreds of leads automatically
- **Campaign Management**: Organize leads into calling campaigns
- **Real-time Dashboard**: Monitor calls and analytics in real-time

### Technical Features
- **Supabase Backend**: PostgreSQL database with real-time subscriptions
- **Twilio Integration**: Voice calls, SMS, voicemail detection
- **LiveKit Voice**: High-quality, real-time AI voice conversations
- **OpenAI Analysis**: Call sentiment, pain points, and outcome analysis
- **Webhook Support**: Real-time call status updates
- **Call Recording**: Automatic recording with cloud storage
- **API Access**: RESTful API for third-party integrations

## 📋 Prerequisites

- Python 3.9 or higher
- Supabase account (free tier works)
- Twilio account with phone number
- LiveKit Cloud account or self-hosted server
- OpenAI API key
- ngrok (for local development)

## 🛠️ Complete Setup Guide

### 1. Clone and Install

```bash
# Clone the repository
git clone <repository-url>
cd cold-calling-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Supabase Setup

1. Create a new Supabase project at [supabase.com](https://supabase.com)

2. In your Supabase dashboard, go to SQL Editor and run the entire contents of `supabase_schema.sql`

3. Get your credentials:
   - Go to Settings → API
   - Copy the `URL` and `anon public` key

### 3. Twilio Setup

1. Sign up at [twilio.com](https://twilio.com)

2. Buy a phone number with voice capabilities

3. Get your credentials:
   - Account SID (from dashboard)
   - Auth Token (from dashboard)
   - Phone Number (format: +1234567890)

### 4. LiveKit Setup

1. Sign up at [livekit.io](https://livekit.io) or self-host

2. Create a new project and get:
   - API Key
   - API Secret
   - WebSocket URL (wss://your-project.livekit.cloud)

### 5. OpenAI Setup

1. Get API key from [platform.openai.com](https://platform.openai.com)

2. Ensure you have GPT-4 access and sufficient credits

### 6. Configuration

1. Copy the example environment file:
```bash
cp .env.local.example .env.local
```

2. Edit `.env.local` with your credentials:
```env
# Supabase Configuration (REQUIRED)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key

# LiveKit Configuration
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret
LIVEKIT_URL=wss://your-project.livekit.cloud

# Twilio Configuration
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# For local development, use ngrok
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io
```

### 7. Database Setup

The `supabase_schema.sql` file will create:
- `leads` table for contact management
- `calls` table for call records
- `scheduled_calls` table for future calls
- `call_campaigns` table for bulk campaigns
- All necessary indexes and functions

### 8. Configure Webhooks

For local development:
1. Install ngrok: `brew install ngrok` (Mac) or download from [ngrok.com](https://ngrok.com)
2. The setup script will start ngrok automatically
3. Copy the HTTPS URL from ngrok and update `WEBHOOK_BASE_URL`

In Twilio:
1. Go to your phone number settings
2. Set the Voice webhook to: `https://your-domain.com/twilio/voice/{CallSid}`
3. Set Status Callback to: `https://your-domain.com/twilio/status/{CallSid}`

## 🏃‍♂️ Running the System

### Automated Setup and Run

```bash
python setup_and_run.py
```

This will:
- Check all prerequisites
- Verify environment variables
- Test Supabase connection
- Import sample data
- Start all services
- Setup ngrok tunnel (if needed)

### Manual Start

```bash
# Terminal 1: Start the Flask app
python real_app.py

# Terminal 2: Start the LiveKit agent
python real_sales_agent.py

# Terminal 3: Start ngrok (for local dev)
ngrok http 5000
```

## 📱 Using the System

### 1. Access the Dashboard

Open http://localhost:5000 in your browser

### 2. Import Leads

- **Manual**: Go to Leads → New Lead
- **Bulk Import**: Leads → Import CSV
- **Sample Data**: Already imported if using setup script

### 3. Make Test Call

1. Select a lead from the dashboard
2. Click "Call Now"
3. Monitor real-time status
4. View transcription when complete

### 4. Bulk Calling

1. Go to Campaigns
2. Create new campaign
3. Add leads to campaign
4. Click "Start Campaign"
5. System will automatically call all leads

### 5. Monitor Analytics

- Dashboard shows real-time stats
- View call recordings and transcriptions
- Export reports as needed

## 🔧 API Usage

### Initiate a Call

```bash
curl -X POST http://localhost:5000/api/leads/{lead_id}/call \
  -H "Content-Type: application/json" \
  -d '{"context": "Follow up on previous conversation"}'
```

### Get Call Status

```bash
curl http://localhost:5000/api/calls/{call_id}/status
```

### Bulk Import Leads

```bash
curl -X POST http://localhost:5000/leads/bulk-import \
  -F "file=@leads.csv"
```

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Browser   │────▶│   Flask App     │────▶│    Supabase     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                          │
                               ▼                          │
                        ┌─────────────────┐              │
                        │     Twilio      │              │
                        └─────────────────┘              │
                               │                          │
                               ▼                          │
                        ┌─────────────────┐              │
                        │    LiveKit      │◀─────────────┘
                        └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  AI Sales Agent │
                        │   (OpenAI)      │
                        └─────────────────┘
```

## 🔒 Security Considerations

1. **Environment Variables**: Never commit `.env.local` to version control
2. **API Keys**: Use environment-specific keys
3. **Webhooks**: Validate Twilio signatures in production
4. **Database**: Enable RLS (Row Level Security) in Supabase
5. **Recording Storage**: Encrypt call recordings at rest

## � Production Deployment

### Recommended Setup

1. **Database**: Use Supabase Pro for better performance
2. **Application**: Deploy to AWS/GCP/Azure with auto-scaling
3. **LiveKit**: Use LiveKit Cloud or dedicated server
4. **Webhooks**: Use proper domain with SSL
5. **Monitoring**: Set up error tracking (Sentry)
6. **Backups**: Enable automatic Supabase backups

### Environment Variables for Production

```env
DEBUG=false
TESTING=false
LOG_LEVEL=WARNING
ENABLE_API_AUTHENTICATION=true
SESSION_TIMEOUT_MINUTES=60
```

## 🐛 Troubleshooting

### Common Issues

1. **"Failed to connect to Supabase"**
   - Check SUPABASE_URL and SUPABASE_KEY
   - Ensure database schema is created

2. **"Twilio webhook error"**
   - Verify WEBHOOK_BASE_URL is accessible
   - Check Twilio webhook configuration

3. **"LiveKit agent not starting"**
   - Verify LiveKit credentials
   - Check Python dependencies

4. **"No audio in calls"**
   - Ensure LiveKit is properly configured
   - Check firewall/network settings

### Debug Mode

Set in `.env.local`:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

## � Support

- **Documentation**: See `/docs` folder
- **Issues**: GitHub Issues
- **Email**: support@example.com

## 📄 License

[Your License Here]

---

**Note**: This system is designed for legitimate sales and customer service purposes. Always comply with local regulations regarding automated calling and obtain proper consent before calling. 