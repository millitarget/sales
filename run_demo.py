import subprocess
import time
import sys
import os

def start_mock_server():
    print("Starting mock product server...")
    server_process = subprocess.Popen([sys.executable, "mock_product_server.py"])
    # Give the server a moment to start
    time.sleep(2)
    return server_process

def start_sales_agent():
    print("Starting Portuguese sales agent...")
    # Update the environment to point to the local mock server
    env = os.environ.copy()
    env["PRODUCTS_API_URL"] = "http://localhost:5000/products"
    agent_process = subprocess.Popen([sys.executable, "sales_agent.py"], env=env)
    return agent_process

def main():
    print("=== Portuguese Sales Agent Demo ===")
    print("Make sure you have set up your .env.local file with the necessary API keys")
    
    # Start the mock server first
    server = start_mock_server()
    
    try:
        # Then start the sales agent
        agent = start_sales_agent()
        
        print("\nBoth services are now running.")
        print("Press Ctrl+C to stop all services...")
        
        # Wait for both processes
        agent.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Clean up processes
        server.terminate()
        print("Demo stopped.")

if __name__ == "__main__":
    main() 