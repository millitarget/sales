#!/usr/bin/env python3
"""
Cold Calling Automation System - Main Startup Script

This script initializes and runs the complete cold calling automation system including:
- Web dashboard and API
- Call scheduling and management
- Database initialization
- Sample data loading

Usage:
    python run_cold_calling_system.py [--demo] [--port 5000]
"""

import os
import sys
import time
import argparse
import threading
import subprocess
from datetime import datetime, timezone
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Setup environment variables and configuration"""
    
    # Check if .env.local exists, if not create from example
    env_file = '.env.local'
    env_example = '.env.local.example'
    
    if not os.path.exists(env_file) and os.path.exists(env_example):
        logger.info("Creating .env.local from example file...")
        with open(env_example, 'r') as src, open(env_file, 'w') as dst:
            content = src.read()
            # Set some default values for demo
            content = content.replace('your-secret-key-here-change-in-production', 'demo-secret-key-123')
            content = content.replace('sk-your-openai-api-key-here', 'sk-demo-key-replace-with-real')
            dst.write(content)
        logger.info(f"Created {env_file}. Please edit it with your actual API keys.")

def initialize_database():
    """Initialize the database with tables and sample data"""
    try:
        from app import app, db
        from models import Lead, CallCampaign, LeadStatus
        
        with app.app_context():
            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Check if we need to add sample data
            if Lead.query.count() == 0:
                logger.info("Adding sample data...")
                add_sample_data()
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False
    
    return True

def add_sample_data():
    """Add sample leads and campaigns for demonstration"""
    try:
        from app import app, db
        from models import Lead, CallCampaign, LeadStatus
        import csv
        
        with app.app_context():
            # Load sample leads from CSV
            if os.path.exists('sample_leads.csv'):
                with open('sample_leads.csv', 'r', encoding='utf-8') as file:
                    csv_reader = csv.DictReader(file)
                    leads_added = 0
                    
                    for row in csv_reader:
                        try:
                            lead = Lead(
                                first_name=row['first_name'],
                                last_name=row['last_name'],
                                company_name=row['company_name'],
                                phone_number=row['phone_number'],
                                email=row['email'],
                                title=row['title'],
                                city=row['city'],
                                postal_code=row['postal_code'],
                                business_type=row['business_type'],
                                best_time_to_call=row['best_time_to_call'],
                                notes=row['notes'],
                                source='Sample Data'
                            )
                            db.session.add(lead)
                            leads_added += 1
                        except Exception as e:
                            logger.warning(f"Failed to add lead {row.get('company_name', 'Unknown')}: {e}")
                    
                    db.session.commit()
                    logger.info(f"Added {leads_added} sample leads")
            
            # Create a sample campaign
            if CallCampaign.query.count() == 0:
                campaign = CallCampaign(
                    name="Restaurant Outreach 2024",
                    description="Initial outreach to Portuguese restaurants for automated reservation system",
                    script_template="Use the default Portuguese sales script",
                    max_calls_per_hour=15,
                    max_calls_per_day=75,
                    start_time="09:00",
                    end_time="18:00",
                    working_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
                    status="draft",
                    total_leads=leads_added
                )
                db.session.add(campaign)
                db.session.commit()
                logger.info("Created sample campaign")
                
    except Exception as e:
        logger.error(f"Failed to add sample data: {e}")

def start_call_scheduler():
    """Start the call scheduler in a separate thread"""
    try:
        from call_scheduler import CallScheduler
        
        def run_scheduler():
            scheduler = CallScheduler()
            logger.info("Call scheduler started successfully")
            
            # Keep the scheduler running
            while True:
                time.sleep(60)  # Check every minute
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Call scheduler thread started")
        
    except ImportError as e:
        logger.warning(f"Call scheduler not available: {e}")
    except Exception as e:
        logger.error(f"Failed to start call scheduler: {e}")

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'flask',
        'sqlalchemy',
        'python-dotenv',
        'pandas',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing required packages: {', '.join(missing_packages)}")
        logger.error("Please install them with: pip install -r requirements.txt")
        return False
    
    logger.info("All required dependencies are installed")
    return True

def start_web_server(port=5000, debug=True):
    """Start the Flask web server"""
    try:
        from app import app
        
        logger.info(f"Starting web server on port {port}")
        logger.info("=" * 60)
        logger.info("🚀 COLD CALLING AUTOMATION SYSTEM STARTED")
        logger.info("=" * 60)
        logger.info(f"📊 Dashboard: http://localhost:{port}")
        logger.info(f"👥 Leads Management: http://localhost:{port}/leads")
        logger.info(f"📞 Campaigns: http://localhost:{port}/campaigns")
        logger.info(f"📈 Analytics: http://localhost:{port}/analytics")
        logger.info("=" * 60)
        logger.info("💡 Tips:")
        logger.info("- Upload the sample_leads.csv to test bulk import")
        logger.info("- Create a campaign and start bulk calling")
        logger.info("- View call transcriptions and analytics")
        logger.info("- Check scheduled calls and follow-ups")
        logger.info("=" * 60)
        
        app.run(host='0.0.0.0', port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"Failed to start web server: {e}")
        return False

def demo_system():
    """Run a demonstration of the system capabilities"""
    logger.info("🎯 STARTING SYSTEM DEMONSTRATION")
    logger.info("=" * 50)
    
    try:
        from app import app
        from models import Lead, Call, CallCampaign
        from call_manager import CallManager
        from call_scheduler import CallScheduler
        
        with app.app_context():
            # Show system status
            total_leads = Lead.query.count()
            total_campaigns = CallCampaign.query.count()
            total_calls = Call.query.count()
            
            logger.info(f"📊 System Status:")
            logger.info(f"   - Total Leads: {total_leads}")
            logger.info(f"   - Total Campaigns: {total_campaigns}")
            logger.info(f"   - Total Calls: {total_calls}")
            
            if total_leads > 0:
                # Simulate a call
                sample_lead = Lead.query.first()
                logger.info(f"📞 Simulating call to: {sample_lead.full_name} at {sample_lead.company_name}")
                
                call_manager = CallManager()
                call_id = call_manager.initiate_call(sample_lead, "Demo call for system testing")
                
                logger.info(f"✅ Call {call_id} initiated successfully")
                logger.info("   - Transcription generated")
                logger.info("   - Lead status updated")
                logger.info("   - Follow-up scheduled (if needed)")
                
            logger.info("🎯 Demo completed! Access the web interface to see results.")
            
    except Exception as e:
        logger.error(f"Demo failed: {e}")

def main():
    """Main function to start the cold calling automation system"""
    parser = argparse.ArgumentParser(description="Cold Calling Automation System")
    parser.add_argument('--demo', action='store_true', help='Run system demonstration')
    parser.add_argument('--port', type=int, default=5000, help='Web server port (default: 5000)')
    parser.add_argument('--no-scheduler', action='store_true', help='Don\'t start the call scheduler')
    parser.add_argument('--debug', action='store_true', default=True, help='Enable debug mode')
    
    args = parser.parse_args()
    
    logger.info("🤖 Cold Calling Automation System")
    logger.info("==================================")
    
    # Setup environment
    setup_environment()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        logger.error("Failed to initialize database. Exiting.")
        sys.exit(1)
    
    # Start call scheduler (unless disabled)
    if not args.no_scheduler:
        start_call_scheduler()
    
    # Run demo if requested
    if args.demo:
        demo_system()
        print("\n" + "="*60)
        print("Demo completed! Starting web server...")
        print("="*60)
    
    # Start web server
    try:
        start_web_server(port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("\n👋 System shutdown requested")
        logger.info("Stopping all services...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()