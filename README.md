# TripBot - AI Travel Assistant

An interactive trip planning chatbot with conversational interface, booking system, and LLM integration using Flask and vanilla JavaScript.

## Features

- **ChatGPT-like Interface**: Natural conversation flow for trip planning
- **AI-Powered**: Supports OpenAI GPT-4o, Google Gemini, and AWS Bedrock Llama models
- **Complete Booking System**: Cost calculations, booking management, and mock payment processing
- **Real-time Progress Tracking**: Visual progress indicators and trip information display
- **Responsive Design**: Works on desktop and mobile devices
- **Database Storage**: Persistent storage for bookings and chat sessions

## Screenshots

The application features a modern dark theme with:
- Split-screen chat interface
- Progress tracking sidebar
- Trip information display
- Cost breakdown visualization
- Booking confirmation system

## Installation

### Prerequisites

- Python 3.12 or higher
- OpenAI API key OR Google Gemini API key

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd tripbot
   ```

2. **Create and activate a virtual environment using `uv`**
   ```bash
   uv venv 
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```

4. **VS Code Users**

   > **Note:**  
   > If you use VS Code, set your default Python interpreter to the virtual environment:
   > 1. Open Command Palette (`Cmd+Shift+P`)
   > 2. Select **Python: Select Interpreter**
   > 3. Choose `.venv/bin/python` from your workspace folder

   This ensures all Python commands and debugging use your project’s virtual environment.

## Development

To run the app:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 50001
```

5. **Set up environment variables**
   Create a `.env` file or set environment variables:
   ```bash
   # Required: At least one AI service
   OPENAI_API_KEY=sk-your-openai-key-here
   # OR
   GEMINI_API_KEY=your-gemini-key-here
   # OR
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   AWS_DEFAULT_REGION=us-east-1
   
   # Optional: Database and session configuration
   DATABASE_URL=sqlite:///trip_planner.db
   SESSION_SECRET=your-secret-key-here
   ```

6. **Run the application**
   
   Using Uvicorn (development):
   ```bash
   uvicorn main:app --reload
   
   Or using uvocorn (production):
   ```bash
   uvcorn --bind 0.0.0.0:50001 --reuse-port --reload main:app
   ```

7. **Access the application**
   Open your browser and navigate to `http://localhost:50001`

## API Keys Setup

### OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com)
2. Create an account or sign in
3. Navigate to API keys section
4. Create a new API key
5. Copy the key (starts with `sk-`)

### Google Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key for use

### AWS Bedrock Configuration
1. Go to [AWS Console](https://console.aws.amazon.com/iam/)
2. Create an IAM user with Bedrock access permissions
3. Generate access keys for the user
4. Set the following environment variables:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY` 
   - `AWS_DEFAULT_REGION` (e.g., us-east-1)
5. Ensure Bedrock access is enabled in your AWS region

## Project Structure

```
├── main.py                          # Application entry point
├── src/
│   └── tripbot/
│       ├── __init__.py                # Package initializer
│       ├── app.py                     # FastAPI application setup and configuration
│       ├── models.py                  # Database models (TripBooking, ChatSession)
│       ├── routes.py                  # API endpoints and request handling
│       ├── llm_adapters.py            # AI service integrations (OpenAI, Gemini)
│       ├── booking_service.py         # Trip booking and cost calculation logic
│       ├── database.py                # Database connection and session management
│       ├── signal_handlers.py         # Signal handling for graceful shutdown
│       └── config/
│           ├── __init__.py            # Config package initializer
│           └── logging_config.py      # Logging configuration
├── templates/
│   └── index.html                     # Main chat interface template
├── static/
│   ├── chat.js                        # Frontend JavaScript functionality
│   └── style.css                      # Custom styling and responsive design
├── tests/
│   └── unit/
│       └── mcp_travel/               # Unit tests for MCP modules
├── pyproject.toml                     # Python project dependencies
├── README.md                          # This file
└── tripbot.db                         # SQLite database file
```

## How It Works

### Conversation Flow
1. **Welcome**: Bot greets user and asks for name
2. **Personal Info**: Collects name and email address
3. **Trip Details**: Gathers destination, departure location, dates
4. **Travel Preferences**: Number of travelers, trip type, budget
5. **Special Requests**: Any additional preferences or requirements
6. **Confirmation**: Summarizes trip details for user approval
7. **Booking**: Creates booking and calculates costs
8. **Payment**: Mock payment processing
9. **Confirmation**: Final booking confirmation with details

### Database Models

**TripBooking**
- Stores completed trip bookings
- Includes traveler info, trip details, costs, and payment status
- Tracks booking status and timestamps

**ChatSession**
- Manages conversation state between requests
- Stores collected trip data during conversation
- Tracks current conversation step

### AI Integration

The application uses adapters to support multiple AI services:
- **OpenAI Adapter**: Uses GPT-4o for natural conversations
- **Gemini Adapter**: Google's Gemini Pro for trip planning
- **Bedrock Adapter**: AWS Bedrock with Llama models for trip planning
- **Fallback System**: Gracefully handles API failures and switches between services

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main chat interface |
| `/api/chat` | POST | Send chat message and get response |
| `/api/bookings` | GET | Get user's booking history |
| `/api/booking/<id>` | GET | Get specific booking details |
| `/api/booking/<id>/cancel` | POST | Cancel a booking |
| `/api/reset` | POST | Reset chat session |

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Optional* | OpenAI API key for GPT-4o |
| `GEMINI_API_KEY` | Optional* | Google Gemini API key |
| `AWS_ACCESS_KEY_ID` | Optional* | AWS access key for Bedrock |
| `AWS_SECRET_ACCESS_KEY` | Optional* | AWS secret key for Bedrock |
| `AWS_DEFAULT_REGION` | No | AWS region (default: us-east-1) |
| `DATABASE_URL` | No | Database connection string (default: SQLite) |
| `SESSION_SECRET` | No | Secret key for session management |

*At least one AI service configuration is required

### Database Configuration

By default, the application uses SQLite for simplicity. To use MySQL:

1. Install MySQL connector:
   ```bash
   pip install mysql-connector-python
   ```

2. Set DATABASE_URL:
   ```bash
   DATABASE_URL=mysql://username:password@host:port/database_name
   ```

## Development

### Adding New Features

1. **New Conversation Steps**: Modify `conversation_steps` in `llm_adapters.py`
2. **Database Changes**: Update models in `models.py`
3. **API Endpoints**: Add routes in `routes.py`
4. **Frontend Updates**: Modify `static/chat.js` and `templates/index.html`

### Testing

Run the application locally and test the conversation flow:
1. Start the server
2. Open browser to `http://localhost:5000`
3. Follow the conversation flow
4. Check database records in `trip_planner.db`

## Deployment

### Replit Deployment
The application is configured for Replit deployment:
- Uses Gunicorn with proper port binding
- Configured with proxy fix for HTTPS
- Environment variables through Replit secrets

### Other Platforms
For deployment on other platforms:
1. Set appropriate environment variables
2. Use Gunicorn or similar WSGI server
3. Configure reverse proxy if needed
4. Set up database (PostgreSQL recommended for production)

## Security Considerations

- API keys are stored as environment variables
- Session management with secure secret keys
- Input validation and sanitization
- CSRF protection through Flask's built-in features
- SQL injection protection through SQLAlchemy ORM

## Troubleshooting

### Common Issues

1. **No AI Response**: Check that API keys are set correctly
2. **Database Errors**: Ensure proper permissions and connection string
3. **Static Files Not Loading**: Verify Flask static file configuration
4. **Port Conflicts**: Change port in `main.py` if 5000 is occupied

### Logs

The application uses Python's logging module. Check console output for:
- API connection status
- Database operations
- Error messages and stack traces

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Ensure all API keys are configured correctly
4. Verify database connectivity

---

Built with Flask, OpenAI GPT-4o, Google Gemini, and modern web technologies.