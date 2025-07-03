# Cold Calling Automation System

A comprehensive automation platform for bulk cold calling with AI-powered conversations, automatic transcription, lead management, and intelligent scheduling. Built specifically for Portuguese B2B sales targeting restaurants and hospitality businesses.

## 🚀 Features

### Core Functionality
- **Bulk Cold Calling**: Automated calling of multiple leads with intelligent timing
- **AI Sales Agent**: Portuguese-speaking AI agent (Ana Sousa) with advanced sales techniques
- **Real-time Transcription**: Automatic call transcription and analysis
- **Lead Management**: Complete CRM for tracking prospects and customers
- **Smart Scheduling**: Automatic follow-up scheduling based on call outcomes
- **Campaign Management**: Organized bulk calling campaigns with performance tracking
- **Analytics Dashboard**: Comprehensive reporting and performance metrics

### Advanced Features
- **Intelligent Context**: AI remembers previous conversations and adapts approach
- **Sentiment Analysis**: Real-time emotion detection during calls
- **Pain Point Identification**: Automatic extraction of business challenges
- **Objection Handling**: AI trained in Portuguese sales objection responses
- **Demo Scheduling**: Automatic calendar integration for product demonstrations
- **Multi-channel Follow-up**: Email and call coordination

### Technical Capabilities
- **Scalable Architecture**: Handle hundreds of concurrent calls
- **LiveKit Integration**: Professional voice communication platform
- **OpenAI GPT-4**: Advanced natural language processing
- **Flexible Telephony**: Support for Twilio, Vonage, and other providers
- **Cloud Storage**: Call recordings stored securely
- **Real-time Dashboard**: Live updates and monitoring

## 📋 Prerequisites

- Python 3.9 or higher
- OpenAI API key (for AI agent and transcription analysis)
- LiveKit account (for voice communication)
- Telephony provider account (Twilio, Vonage, etc.)
- Redis (for task queue management)

## 🛠 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd cold-calling-automation
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy the example configuration
cp .env.local.example .env.local

# Edit with your API keys and settings
nano .env.local
```

### 4. Set Up API Keys
Edit `.env.local` with your credentials:

```env
# Required
OPENAI_API_KEY=sk-your-openai-api-key
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret
LIVEKIT_URL=wss://your-livekit-server.com

# Telephony Provider (choose one)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Database
DATABASE_URL=sqlite:///cold_calling.db

# Optional but recommended
REDIS_URL=redis://localhost:6379/0
```

### 5. Start the System
```bash
# Quick start with demo data
python run_cold_calling_system.py --demo

# Or start without demo
python run_cold_calling_system.py
```

## 🎯 Quick Start Guide

### 1. Access the Dashboard
Open your browser to `http://localhost:5000`

### 2. Import Leads
- Click "Import Leads" in the sidebar
- Upload the provided `sample_leads.csv` or create your own
- CSV format: `first_name,last_name,company_name,phone_number,email,title,city,business_type`

### 3. Start Bulk Calling
- Click "Start Bulk Calling" 
- Select leads to call
- Choose campaign settings
- Monitor progress in real-time

### 4. Review Results
- View call transcriptions
- Check lead status updates
- Review scheduled follow-ups
- Analyze performance metrics

## 📊 System Architecture

### Components

1. **Web Application** (`app.py`)
   - Flask-based dashboard and API
   - Lead and campaign management
   - Real-time monitoring

2. **Call Manager** (`call_manager.py`)
   - Individual call initiation and management
   - LiveKit integration
   - Transcription processing

3. **Call Scheduler** (`call_scheduler.py`)
   - Bulk calling orchestration
   - Automatic follow-up scheduling
   - Campaign timing management

4. **Sales Agent** (`sales_agent.py`)
   - Portuguese AI sales representative
   - Advanced conversation handling
   - Cultural and business context awareness

5. **Database Models** (`models.py`)
   - Lead management
   - Call history and transcriptions
   - Campaign tracking
   - Scheduling system

### Data Flow

```
Leads Import → Campaign Creation → Bulk Scheduling → 
AI Calls → Transcription → Analysis → Follow-up Scheduling
```

## 🎨 User Interface

### Dashboard
- Real-time statistics and KPIs
- Recent call activity
- Upcoming scheduled calls
- Campaign performance
- Quick action buttons

### Lead Management
- Complete prospect database
- Call history and notes
- Status tracking
- Contact information management

### Campaign Management
- Bulk calling campaigns
- Performance metrics
- Scheduling configuration
- Script management

### Analytics
- Call volume and success rates
- Conversion funnel analysis
- Performance over time
- ROI calculations

## 🤖 AI Sales Agent (Ana Sousa)

### Personality & Approach
- **Name**: Ana Sousa from Chamada AI
- **Language**: Native Portuguese (European)
- **Tone**: Professional, warm, consultative
- **Specialty**: Restaurant automation solutions

### Sales Methodology
- **SPIN Selling**: Situation, Problem, Implication, Need-payoff
- **Cultural Sensitivity**: Portuguese business etiquette
- **Objection Handling**: Trained responses to common concerns
- **Value Proposition**: Focus on revenue increase and automation

### Conversation Flow
1. **Opening**: Professional introduction with permission request
2. **Discovery**: Understand current reservation management
3. **Pain Points**: Identify lost calls and inefficiencies
4. **Solution**: Present automated reservation system benefits
5. **Close**: Schedule demo or follow-up call

## 📈 Performance Optimization

### Call Quality
- Optimal timing based on business hours
- Rate limiting to avoid overwhelming prospects
- Intelligent retry logic for busy/no-answer scenarios

### Scalability
- Asynchronous call processing
- Database optimization for large lead volumes
- Efficient scheduling algorithms

### Monitoring
- Real-time call status tracking
- Performance metrics and alerts
- Error handling and recovery

## 🔧 Customization

### Sales Scripts
Modify `sales_agent.py` to customize:
- Opening statements
- Product positioning
- Objection responses
- Closing techniques

### Call Timing
Adjust in `.env.local`:
```env
BUSINESS_START_TIME=09:00
BUSINESS_END_TIME=18:00
WORKING_DAYS=monday,tuesday,wednesday,thursday,friday
MAX_CALLS_PER_HOUR=20
```

### Lead Scoring
Configure lead prioritization:
- Recent engagement
- Company size
- Geographic location
- Industry segment

## 🔐 Security & Compliance

### Data Protection
- Encrypted call recordings
- GDPR compliance features
- Secure API access
- Call data retention policies

### Privacy
- Do-not-call list management
- Consent tracking
- Data anonymization options

## 📞 Telephony Integration

### Supported Providers
- **Twilio**: Full integration with voice, SMS, and recording
- **Vonage**: Voice calling and recording capabilities
- **Custom SIP**: Direct SIP trunk integration

### Call Features
- Automatic dialing
- Call recording
- Real-time transcription
- Conference calling for demos
- Voicemail detection

## 📊 Analytics & Reporting

### Key Metrics
- **Call Volume**: Daily, weekly, monthly statistics
- **Success Rates**: Connection and conversion percentages
- **Lead Quality**: Scoring and segmentation analysis
- **Revenue Impact**: Closed deals and pipeline value

### Reports
- Daily activity summaries
- Campaign performance analysis
- Sales team leaderboards
- ROI calculations

## 🚨 Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Reset database
rm cold_calling.db
python run_cold_calling_system.py
```

**Missing Dependencies**
```bash
pip install -r requirements.txt
```

**API Key Issues**
- Verify OpenAI API key has sufficient credits
- Check LiveKit credentials and server status
- Confirm telephony provider account status

**Call Quality Issues**
- Check internet connection stability
- Verify microphone and audio settings
- Test with smaller batch sizes first

### Logs and Debugging
```bash
# Enable debug mode
python run_cold_calling_system.py --debug

# Check logs
tail -f logs/cold_calling.log
```

## 🤝 Contributing

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Code formatting
black .
flake8 .
```

### Adding Features
1. Create feature branch
2. Implement changes with tests
3. Update documentation
4. Submit pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section
- Review the API documentation

## 🚀 Deployment

### Production Setup
1. **Environment Configuration**
   - Use PostgreSQL instead of SQLite
   - Configure Redis for production
   - Set up proper logging

2. **Security**
   - Use environment variables for secrets
   - Enable SSL/TLS
   - Configure firewall rules

3. **Scaling**
   - Deploy on cloud infrastructure
   - Use load balancers for high availability
   - Implement monitoring and alerting

### Docker Deployment
```bash
# Build and run with Docker
docker-compose up -d
```

## 📋 API Documentation

### REST Endpoints
- `GET /api/leads` - Retrieve leads
- `POST /api/leads` - Create new lead
- `POST /api/bulk-call` - Start bulk calling
- `GET /api/calls/{id}/status` - Check call status
- `POST /api/calls/{id}/complete` - Mark call complete

### Webhooks
- Call completion notifications
- Lead status updates
- Campaign progress reports

---

**Built with ❤️ for Portuguese B2B sales teams**

Transform your cold calling process with AI-powered automation and intelligent conversation management. 