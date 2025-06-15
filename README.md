# Portuguese Sales Agent

A LiveKit voice agent that functions as a Portuguese-speaking sales representative. The agent can handle product inquiries, check availability, calculate discounts, and provide sales assistance in Portuguese.

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env.local` file with your API keys and configuration (see `.env.local.example`)
4. Run the agent:
   ```
   python sales_agent.py
   ```

## Features

- Portuguese language sales conversations
- Product catalog browsing
- Availability checking
- Discount calculation
- Natural Portuguese conversation with cultural context

## Requirements

- Python 3.9+
- OpenAI API key
- LiveKit API key and secret
- Product API endpoint (configurable)

## Configuration

Edit the `.env.local` file to set your API keys and endpoints.

## Customization

- Modify the `LANGUAGE_NUDGE` and `LANGUAGE_EXAMPLES` variables to adapt the Portuguese language style
- Update the tool functions to connect to your actual product database
- Change the voice settings in the `entrypoint` function for better Portuguese pronunciation 