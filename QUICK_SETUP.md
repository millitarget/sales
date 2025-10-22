# 🚀 Quick Setup Guide - Cold Calling System

Get your cold calling system running in 15 minutes!

## Prerequisites Checklist

Before starting, ensure you have:
- [ ] Python 3.9+ installed
- [ ] Git installed
- [ ] Web browser (Chrome/Firefox recommended)

## Step 1: Get Your API Keys (10 minutes)

### 1.1 Supabase (Database) - FREE
1. Go to [supabase.com](https://supabase.com)
2. Sign up for a free account
3. Create a new project (name it "cold-calling")
4. Once created, go to Settings → API
5. Copy these values:
   - Project URL (looks like: https://xxxxx.supabase.co)
   - Anon/Public key (starts with: eyJ...)

### 1.2 OpenAI (AI Agent) - PAID
1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up/login
3. Go to API Keys → Create new secret key
4. Copy the key (starts with: sk-...)
5. Add credits ($20 recommended for testing)

### 1.3 Twilio (Phone Calls) - PAID
1. Go to [twilio.com](https://twilio.com)
2. Sign up for account (get $15 free credit)
3. Buy a phone number ($1/month)
4. From Console, copy:
   - Account SID
   - Auth Token
   - Your phone number (format: +1234567890)

### 1.4 LiveKit (Voice Engine) - FREE TRIAL
1. Go to [livekit.io](https://livekit.io)
2. Sign up for LiveKit Cloud (free tier available)
3. Create a new project
4. Copy from project settings:
   - API Key
   - API Secret
   - WebSocket URL (wss://xxxxx.livekit.cloud)

## Step 2: Setup Database (3 minutes)

1. Go to your Supabase project dashboard
2. Click on "SQL Editor" in the left sidebar
3. Click "New Query"
4. Copy ALL contents from `supabase_schema.sql` file
5. Paste into the SQL editor
6. Click "RUN" button
7. You should see "Success. No rows returned"

## Step 3: Configure System (2 minutes)

1. In the project folder, copy the example config:
```bash
cp .env.local.example .env.local
```

2. Edit `.env.local` file and add your keys:
```env
# Replace these with your actual values
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key-here

OPENAI_API_KEY=sk-your-openai-key-here

LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret
LIVEKIT_URL=wss://your-project.livekit.cloud

TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Leave this for now, we'll update it later
WEBHOOK_BASE_URL=http://localhost:5000
```

## Step 4: Install & Run (5 minutes)

1. Open terminal in project folder

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the setup script:
```bash
python setup_and_run.py
```

5. The system will:
   - Check your configuration
   - Test database connection
   - Import sample leads
   - Start all services
   - Open dashboard at http://localhost:5000

## Step 5: Configure Twilio (2 minutes)

For local testing with ngrok:

1. Install ngrok:
   - Mac: `brew install ngrok`
   - Windows/Linux: Download from [ngrok.com](https://ngrok.com)

2. In a new terminal, run:
```bash
ngrok http 5000
```

3. Copy the HTTPS URL (like: https://abc123.ngrok.io)

4. Update `.env.local`:
```env
WEBHOOK_BASE_URL=https://abc123.ngrok.io
```

5. In Twilio Console:
   - Go to Phone Numbers → Manage → Active Numbers
   - Click your number
   - In Voice Configuration:
     - Webhook: `https://abc123.ngrok.io/twilio/voice`
     - Method: HTTP POST
   - Save

## Step 6: Make Your First Call!

1. Go to http://localhost:5000
2. You'll see the dashboard with sample leads
3. Click on any lead name
4. Click "Call Now" button
5. The system will call that number!

## 🎉 Success Checklist

- [ ] Dashboard loads at http://localhost:5000
- [ ] Sample leads appear in the system
- [ ] "System Status" shows all services as "Active"
- [ ] Can initiate a test call
- [ ] Call status updates in real-time

## 🔧 Troubleshooting

### "Failed to connect to Supabase"
- Check SUPABASE_URL and SUPABASE_KEY are correct
- Make sure you ran the SQL schema in Supabase

### "Twilio authentication failed"
- Verify Account SID and Auth Token
- Ensure phone number includes country code (+1 for US)

### "LiveKit connection error"
- Check API Key and Secret match
- Verify WebSocket URL starts with wss://

### "No audio in calls"
- Ensure LiveKit credentials are correct
- Check your internet connection
- Try restarting the LiveKit agent

## 📱 Quick Test Numbers

For testing without real calls:
- Use Twilio test numbers: +15005550006 (always answers)
- Or call your own mobile phone

## 🚀 Next Steps

1. **Import Your Leads**: 
   - Prepare CSV with: name, company, phone, email
   - Go to Leads → Import CSV

2. **Customize AI Agent**:
   - Edit `real_sales_agent.py` for your product/service
   - Adjust language and personality

3. **Start Campaigns**:
   - Create campaign
   - Add leads
   - Set schedule
   - Launch!

## 💡 Pro Tips

- Start with 5-10 test calls before going large scale
- Monitor the dashboard during calls for real-time insights
- Check call transcriptions to improve AI responses
- Use business hours settings to comply with regulations

## 🆘 Need Help?

- Check the full README.md for detailed documentation
- Review error logs in the terminal
- Ensure all services show "Active" in dashboard

Happy calling! 🎯📞