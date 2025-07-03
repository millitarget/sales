#!/usr/bin/env python3
"""
Setup and Run Script for Cold Calling Automation System
This script sets up the complete system with Supabase and starts all services
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_python_version():
    """Check if Python version is 3.9 or higher"""
    if sys.version_info < (3, 9):
        logger.error("Python 3.9 or higher is required")
        return False
    logger.info(f"Python version: {sys.version}")
    return True

def check_environment_variables():
    """Check if all required environment variables are set"""
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_KEY',
        'OPENAI_API_KEY',
        'LIVEKIT_API_KEY',
        'LIVEKIT_API_SECRET',
        'LIVEKIT_URL',
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'TWILIO_PHONE_NUMBER',
        'WEBHOOK_BASE_URL'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.info("Please copy .env.local.example to .env.local and fill in your credentials")
        return False
    
    logger.info("All required environment variables are set")
    return True

def install_dependencies():
    """Install Python dependencies"""
    logger.info("Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        logger.info("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        logger.error("Failed to install dependencies")
        return False

def setup_supabase_database():
    """Setup Supabase database schema"""
    logger.info("Setting up Supabase database...")
    
    try:
        from supabase_client import supabase_client
        
        # Test connection
        response = supabase_client.client.table('system_config').select("*").limit(1).execute()
        logger.info("Successfully connected to Supabase")
        
        # The database schema should be created using the SQL file in Supabase dashboard
        logger.info("Note: Please ensure you've run supabase_schema.sql in your Supabase project")
        
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        logger.info("Please check your SUPABASE_URL and SUPABASE_KEY")
        return False

def import_sample_data():
    """Import sample leads into Supabase"""
    logger.info("Importing sample data...")
    
    try:
        from supabase_client import supabase_client
        import pandas as pd
        
        # Check if leads already exist
        existing_leads = supabase_client.get_leads(limit=1)
        if existing_leads:
            logger.info("Sample data already exists, skipping import")
            return True
        
        # Read sample CSV
        if os.path.exists('sample_leads.csv'):
            df = pd.read_csv('sample_leads.csv')
            leads_data = df.to_dict('records')
            
            # Import to Supabase
            created_leads = supabase_client.bulk_create_leads(leads_data)
            logger.info(f"Imported {len(created_leads)} sample leads")
            
            # Create a sample campaign
            campaign_data = {
                'name': 'Restaurant Outreach 2024',
                'description': 'Cold calling campaign for Portuguese restaurants',
                'max_calls_per_hour': 15,
                'max_calls_per_day': 75,
                'status': 'draft'
            }
            campaign = supabase_client.create_campaign(campaign_data)
            logger.info("Created sample campaign")
            
        return True
    except Exception as e:
        logger.error(f"Failed to import sample data: {e}")
        return False

def start_livekit_agent():
    """Start the LiveKit sales agent"""
    logger.info("Starting LiveKit sales agent...")
    
    try:
        # Start in a separate process
        agent_process = subprocess.Popen(
            [sys.executable, 'real_sales_agent.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give it time to start
        time.sleep(3)
        
        if agent_process.poll() is None:
            logger.info("LiveKit agent started successfully")
            return agent_process
        else:
            logger.error("LiveKit agent failed to start")
            return None
            
    except Exception as e:
        logger.error(f"Failed to start LiveKit agent: {e}")
        return None

def start_flask_app():
    """Start the Flask web application"""
    logger.info("Starting Flask web application...")
    
    try:
        # Start Flask app
        app_process = subprocess.Popen(
            [sys.executable, 'real_app.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give it time to start
        time.sleep(3)
        
        if app_process.poll() is None:
            logger.info("Flask app started successfully")
            return app_process
        else:
            logger.error("Flask app failed to start")
            return None
            
    except Exception as e:
        logger.error(f"Failed to start Flask app: {e}")
        return None

def setup_ngrok_tunnel():
    """Setup ngrok tunnel for local development"""
    logger.info("Setting up ngrok tunnel for webhooks...")
    
    try:
        # Check if ngrok is installed
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("ngrok not installed. Install it from https://ngrok.com/")
            logger.warning("Without ngrok, Twilio webhooks won't work in local development")
            return None
        
        # Start ngrok
        ngrok_process = subprocess.Popen(
            ['ngrok', 'http', '5000'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        time.sleep(3)
        
        logger.info("ngrok tunnel started")
        logger.info("Get your public URL from: http://localhost:4040")
        logger.info("Update WEBHOOK_BASE_URL in .env.local with the ngrok URL")
        
        return ngrok_process
        
    except Exception as e:
        logger.warning(f"Failed to start ngrok: {e}")
        return None

def main():
    """Main setup and run function"""
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║        COLD CALLING AUTOMATION SYSTEM             ║
    ║           WITH SUPABASE & TWILIO                  ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    
    # Check environment variables
    if not check_environment_variables():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Setup database
    if not setup_supabase_database():
        sys.exit(1)
    
    # Import sample data
    import_sample_data()
    
    # Start services
    processes = []
    
    # Start ngrok for local development
    if os.getenv('WEBHOOK_BASE_URL', '').startswith('http://localhost'):
        ngrok_process = setup_ngrok_tunnel()
        if ngrok_process:
            processes.append(ngrok_process)
    
    # Start LiveKit agent
    agent_process = start_livekit_agent()
    if agent_process:
        processes.append(agent_process)
    
    # Start Flask app
    app_process = start_flask_app()
    if app_process:
        processes.append(app_process)
    
    if not processes:
        logger.error("No services started successfully")
        sys.exit(1)
    
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║            SYSTEM STARTED SUCCESSFULLY!           ║
    ╚═══════════════════════════════════════════════════╝
    
    🌐 Web Dashboard: http://localhost:5000
    📊 Supabase Dashboard: Check your Supabase project URL
    🔊 LiveKit Agent: Running in background
    📞 Twilio Webhooks: Configure in Twilio console
    
    📋 Quick Start:
    1. Import leads: http://localhost:5000/leads/new
    2. Start bulk calling: Click "Start Bulk Calling" on dashboard
    3. Monitor calls: Real-time updates on dashboard
    4. View analytics: http://localhost:5000/analytics
    
    ⚠️  Important Setup Steps:
    1. Run supabase_schema.sql in your Supabase SQL editor
    2. Update WEBHOOK_BASE_URL with your ngrok URL
    3. Configure Twilio phone number webhooks
    4. Test with a single call before bulk calling
    
    Press Ctrl+C to stop all services
    """)
    
    try:
        # Keep running
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            for process in processes:
                if process.poll() is not None:
                    logger.error("A service has stopped unexpectedly")
                    break
                    
    except KeyboardInterrupt:
        logger.info("\nShutting down services...")
        
        # Terminate all processes
        for process in processes:
            process.terminate()
            process.wait()
        
        logger.info("All services stopped")
        sys.exit(0)

if __name__ == "__main__":
    main()