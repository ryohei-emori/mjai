# MJAI Backend - FastAPI Application

FastAPI backend for the Japanese text correction AI system with support for multiple LLM providers and Docker deployment.

## Overview

This backend provides:
- RESTful API for session management
- AI-powered text correction via multiple LLM providers
- SQLite database for data persistence
- Docker containerization with ngrok support
- Extensible LLM provider architecture

## Tech Stack

- **Framework**: FastAPI (Python)
- **Database**: SQLite with SQLAlchemy
- **LLM Providers**: Gemini API, Qwen (local), OpenAI (example)
- **Container**: Docker with multi-stage builds
- **API Documentation**: Auto-generated OpenAPI/Swagger
- **Testing**: pytest with mock support

## Quick Start (Docker)

The backend is designed to run as part of the Docker Compose setup:

```bash
# From project root
cd conf
docker-compose up -d backend
```

Access API docs: `https://<BACKEND_NGROK_URL>/docs`

## Local Development

If you need to run the backend locally:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## LLM Provider Architecture

The backend uses an abstracted LLM provider system:

```
app/llm/
├── base.py      # Base LLM provider class
├── gemini.py    # Google Gemini API provider
├── qwen.py      # Qwen local LLM provider
└── openai.py    # OpenAI provider (example)
```

### Available Providers

1. **Gemini API** (Default)
   - Cloud-based, high performance
   - Requires `GEMINI_API_KEY`
   - Automatic JSON response parsing

2. **OpenAI API** (Optional)
   - Cloud-based, high performance
   - Requires `OPENAI_API_KEY`
   - Automatic JSON response parsing

3. **Mock Mode** (Development)
   - No external dependencies
   - Consistent test data
   - Fast development cycles

## Database Architecture

### Hierarchical Data Structure

The application uses a three-tier hierarchical structure for organizing correction data:

```
Session (セッション)
├── History 1 (履歴1) 
│   ├── Proposal 1 (修正提案1)
│   ├── Proposal 2 (修正提案2)
│   ├── Proposal 3 (修正提案3)
│   └── ...
├── History 2 (履歴2)
│   ├── Proposal 1
│   ├── Proposal 2
│   └── ...
└── ...
```

### Table Relationships

| Table | Primary Key | Foreign Key | Purpose | Key Fields |
|-------|-------------|-------------|---------|------------|
| **Sessions** | `sessionId` | - | Session management | `name`, `createdAt`, `correctionCount` |
| **CorrectionHistories** | `historyId` | `sessionId` | Correction history | `originalText`, `targetText`, `combinedComment` |
| **AIProposals** | `proposalId` | `historyId` | Correction proposals | `originalAfterText`, `originalReason`, `isSelected` |

### Data Flow Process

1. **Session Creation**: User creates a new correction session
2. **History Creation**: User inputs original text and target text, generates AI suggestions
3. **Proposal Generation**: AI creates 5 correction proposals with detailed reasons
4. **Proposal Selection**: User selects and optionally modifies proposals
5. **Data Persistence**: All data is saved to SQLite database with full traceability

### Key Features

- **Session Management**: Group multiple correction tasks under one session
- **History Tracking**: Record detailed correction history with timestamps
- **Proposal Management**: Store specific correction points and detailed reasons
- **Selection Tracking**: Track which corrections were adopted and in what order
- **Complete Restoration**: Reconstruct past correction work with full context
- **Modification Support**: Allow users to modify AI suggestions and track changes

## API Endpoints

### Session Management
- `GET /sessions` - List all sessions
- `POST /sessions` - Create new session
- `GET /sessions/{session_id}` - Get session details
- `PUT /sessions/{session_id}` - Update session
- `DELETE /sessions/{session_id}` - Delete session

### Correction History
- `GET /sessions/{session_id}/histories` - Get session histories
- `POST /histories` - Create new history entry

### AI Suggestions
- `POST /suggestions` - Generate AI correction suggestions
- `GET /histories/{history_id}/proposals` - Get proposals for history
- `POST /proposals` - Create new proposal

### Example Request
```json
POST /suggestions
{
  "originalText": "私は学校に行きました",
  "targetText": "私は学校へ行きました", 
  "instructionPrompt": "丁寧語で統一してください",
  "sessionId": "optional-session-id",
  "engine": "gemini"
}
```

### Example Response
```json
{
  "suggestions": [
    {
      "id": "1",
      "original": "私は学校に行きました",
      "reason": "移動の方向を表す場合は「へ」が適切です"
    }
  ],
  "overallComment": "全体的に日本語の表現が自然になりました"
}
```

## Environment Variables

Required environment variables (set in `conf/.env`):
- `GEMINI_API_KEY` - Google Gemini API key
- `GEMINI_MODEL` - Gemini model name (default: gemini-2.0-flash)
- `ENVIRONMENT` - Environment mode (development/production)
- `BACKEND_NGROK_URL` - Backend ngrok URL
- `FRONTEND_NGROK_URL` - Frontend ngrok URL

## Database Schema

### Sessions Table
- `sessionId` (TEXT, PRIMARY KEY)
- `createdAt` (TEXT)
- `updatedAt` (TEXT) 
- `name` (TEXT)
- `correctionCount` (INTEGER)
- `isOpen` (INTEGER)

### CorrectionHistories Table
- `historyId` (TEXT, PRIMARY KEY)
- `sessionId` (TEXT, FOREIGN KEY)
- `timestamp` (TEXT)
- `originalText` (TEXT)
- `instructionPrompt` (TEXT)
- `targetText` (TEXT)
- `combinedComment` (TEXT)
- `selectedProposalIds` (TEXT)
- `customProposals` (TEXT)

### AIProposals Table
- `proposalId` (TEXT, PRIMARY KEY)
- `historyId` (TEXT, FOREIGN KEY)
- `type` (TEXT)
- `originalAfterText` (TEXT)
- `originalReason` (TEXT)
- `modifiedAfterText` (TEXT)
- `modifiedReason` (TEXT)
- `isSelected` (INTEGER)
- `isModified` (INTEGER)
- `isCustom` (INTEGER)
- `selectedOrder` (INTEGER)

## Testing

```bash
# Run all tests
python -m pytest

# Run specific test
python -m pytest test_main.py::test_gemini_suggestions -v

# Run with coverage
python -m pytest --cov=app
```

## Development Notes

### LLM Provider Switching
- Engine selection via `engine` parameter in API requests
- Automatic fallback to mock mode if provider fails
- Easy addition of new providers via base class

### Database Operations
- SQLite with connection pooling
- Automatic schema initialization
- Data persistence across container restarts

### Error Handling
- Graceful LLM provider failures
- JSON parsing fallbacks
- Comprehensive error logging

### Performance
- Async database operations
- Connection pooling
- Efficient LLM response caching

## Deployment

The backend is containerized and deployed via Docker Compose. For production:

1. Set production environment variables
2. Configure proper CORS settings
3. Set up reverse proxy if needed
4. Monitor logs and performance

## Contributing

1. Follow FastAPI best practices
2. Add tests for new endpoints
3. Update API documentation
4. Ensure Docker compatibility 