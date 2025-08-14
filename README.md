# MJAI - Japanese Text Correction AI Application

An AI application that supports Japanese text correction. It compares original text with target text and proposes natural and polite Japanese corrections.

---

## Quick Start (Docker & ngrok)

### 1. Clone Repository
```bash
git clone <repository-url>
cd mjai
```

### 2. Create Environment Variables
Copy `conf/.env.example` to `conf/.env` and fill in the required API keys and ngrok authtoken.

```bash
cp conf/.env.example conf/.env
# Edit conf/.env with your editor
```

- `GEMINI_API_KEY` ... Gemini API key (get from Google Cloud Console)
- `NGROK_AUTHTOKEN` ... ngrok authtoken (https://dashboard.ngrok.com/get-started/your-authtoken)

### 3. Build & Start Docker Services
```bash
cd conf
# Build images (first time only)
docker-compose build
# Start services
docker-compose up -d
```

### 4. Access via ngrok External URLs
- Frontend: `https://<FRONTEND_NGROK_URL>`
- Backend API: `https://<BACKEND_NGROK_URL>`

> URLs are automatically reflected in `conf/.env` as `FRONTEND_NGROK_URL` and `BACKEND_NGROK_URL`.

### 5. Rebuilding the Frontend after Environment Changes
If you update environment variables (such as ngrok URLs or API keys) in `conf/.env`, you must rebuild the frontend for the changes to take effect.

**To rebuild and restart the frontend:**

```bash
cd conf
docker-compose build frontend
docker-compose up -d frontend
```

- This ensures that all `NEXT_PUBLIC_` environment variables are correctly embedded in the frontend build.
- For local development with `npm run dev`, restart the dev server after changing `.env`.

---

## Main Features
- Session management & history saving
- AI-powered Japanese text correction (Gemini API)
- Custom correction proposal addition
- Data persistence with SQLite

---

## Directory Structure

```
mjai/
├── backend/                          # FastAPI Backend (Python)
│   ├── app/                         # Main application code
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── db_helper.py             # Database operations
│   │   ├── llm/                     # LLM provider abstraction
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base LLM provider class
│   │   │   ├── gemini.py            # Gemini API provider
│   │   │   └── openai.py            # OpenAI provider (example)
│   │   └── models/                  # Pydantic models
│   │       ├── __init__.py
│   │       ├── session.py           # Session models
│   │       ├── history.py           # History models
│   │       └── proposal.py          # Proposal models
│   ├── db/                          # Database files
│   │   ├── app.db                   # SQLite database (persistent)
│   │   ├── schema.sql               # Database schema
│   │   └── init_db.py               # Database initialization
│   ├── requirements.txt             # Python dependencies
│   ├── Dockerfile                   # Backend container config
│   ├── run_cloud.sh                 # Cloud deployment script
│   └── README.md                    # Backend documentation
├── frontend/                        # Next.js Frontend (React/TypeScript)
│   ├── src/                         # Source code
│   │   ├── app/                     # Next.js app directory
│   │   │   ├── page.tsx             # Main application page
│   │   │   ├── api.ts               # API client functions
│   │   │   ├── layout.tsx           # Root layout
│   │   │   ├── globals.css          # Global styles
│   │   │   └── __tests__/           # Test files
│   │   │       └── apiError.test.tsx
│   │   ├── components/              # React components
│   │   │   └── ui/                  # UI components (shadcn/ui)
│   │   └── hooks/                   # Custom React hooks
│   │       └── use-toast.ts
│   ├── public/                      # Static assets
│   ├── package.json                 # Node.js dependencies
│   ├── next.config.js               # Next.js configuration
│   ├── tailwind.config.js           # Tailwind CSS config
│   ├── Dockerfile                   # Frontend container config
│   └── README.md                    # Frontend documentation
├── conf/                            # Configuration & Deployment
│   ├── docker-compose.yml           # Multi-service orchestration
│   ├── .env.example                 # Environment variables template
│   ├── .env                         # Environment variables (create from example)
│   ├── ngrok-docker.yml             # ngrok configuration
│   ├── update-env.sh                # Environment updater script
│   └── start.sh                     # Quick start script
├── venv/                            # Python virtual environment (local dev)
├── .pytest_cache/                   # Python test cache
└── README.md                        # This file
```

---

## Database Architecture

The application uses a hierarchical data structure for organizing correction sessions:

### Data Hierarchy
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

### Database Tables & Relationships

| Table | Primary Key | Foreign Key | Purpose |
|-------|-------------|-------------|---------|
| **Sessions** | `sessionId` | - | Session management |
| **CorrectionHistories** | `historyId` | `sessionId` | Correction history |
| **AIProposals** | `proposalId` | `historyId` | Correction proposals |

### Data Flow
1. **Session Creation**: User creates a new correction session
2. **History Creation**: User inputs original text and target text, generates AI suggestions
3. **Proposal Generation**: AI creates 5 correction proposals with reasons
4. **Proposal Selection**: User selects and modifies proposals
5. **Data Persistence**: All data is saved to SQLite database

### Key Features
- **Session Management**: Group multiple correction tasks
- **History Tracking**: Record detailed correction history
- **Proposal Management**: Store specific correction points and reasons
- **Selection Tracking**: Track which corrections were adopted
- **Complete Restoration**: Reconstruct past correction work

---

## Common Operations

### Stop Services
```bash
cd conf
docker-compose down
```

### Database Persistence
- SQLite database is persisted at `backend/db/app.db` (shared between local and Docker)
- To reset database, delete `backend/db/app.db`

### Skip ngrok Warning Page
- All frontend API requests automatically include `ngrok-skip-browser-warning` header
- If warning page appears, visit ngrok URL in browser and approve "Visit Site"

---

## Troubleshooting

### ngrok URLs Changed/Cannot Access
- Check `FRONTEND_NGROK_URL`/`BACKEND_NGROK_URL` in `conf/.env`
- Use new URLs after service restart

### CORS Errors
- ngrok domains are pre-configured in Next.js `allowedDevOrigins`
- Restart frontend if issues persist

### Database Not Initialized/Not Reflecting
- Check if `backend/db/app.db` exists
- Verify volume mount configuration

### API Returns 404 or Warning Page
- ngrok "Visit Site" warnings are automatically skipped with headers
- If still appearing, visit ngrok URL in browser and approve

---

## Development & Customization
- All main configuration, startup, and environment variables are contained in `conf/` directory
- No need for individual backend/frontend manual setup or startup
- Additional AI engines or DB schema changes are reflected with Docker restart

---

## License
MIT

## Contributing
Pull Requests and Issues welcome 