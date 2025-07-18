# MJAI Frontend - Next.js Application

Frontend application for the Japanese text correction AI system built with Next.js 15, React, and TypeScript.

## Overview

This frontend provides a modern web interface for:
- Session management (create, view, delete sessions)
- Text correction workflow (original text → target text → AI suggestions)
- Custom correction proposals
- History viewing and management
- Real-time AI suggestions via Gemini API

## Tech Stack

- **Framework**: Next.js 15.3.4 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui components
- **State Management**: React hooks (useState, useEffect)
- **API Client**: Custom fetch wrapper with ngrok support
- **Development**: Turbopack for fast refresh

## Quick Start (Docker)

The frontend is designed to run as part of the Docker Compose setup:

```bash
# From project root
cd conf
docker-compose up -d frontend
```

Access via ngrok URL: `https://<FRONTEND_NGROK_URL>`

## Local Development

If you need to run the frontend locally:

```bash
cd frontend
npm install
npm run dev
```

**Note**: You'll need to update `src/app/api.ts` to point to your backend URL.

## Key Features

### Session Management
- Create new correction sessions
- View session history and saved corrections
- Delete sessions
- Session persistence via backend API

### Text Correction Interface
- Input original text (source material)
- Input target text (text to be corrected)
- Generate AI suggestions via Gemini API
- Select and modify correction proposals
- Add custom correction proposals
- Save correction history

### UI Components
- Modern, responsive design with shadcn/ui
- Toast notifications for user feedback
- Loading states and error handling
- Mobile-friendly interface

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── page.tsx           # Main application page
│   │   ├── api.ts             # API client functions
│   │   ├── layout.tsx         # Root layout component
│   │   ├── globals.css        # Global styles
│   │   └── __tests__/         # Test files
│   ├── components/            # React components
│   │   └── ui/               # shadcn/ui components
│   └── hooks/                # Custom React hooks
├── public/                   # Static assets
├── package.json             # Dependencies
├── next.config.js           # Next.js configuration
├── tailwind.config.js       # Tailwind CSS config
└── Dockerfile              # Container configuration
```

## API Integration

The frontend communicates with the FastAPI backend through:
- RESTful API endpoints for CRUD operations
- WebSocket-like real-time updates (future)
- Automatic ngrok warning page handling

### Key API Functions
- `sessionAPI` - Session management
- `historyAPI` - Correction history
- `proposalAPI` - AI/custom proposals
- `suggestionsAPI` - AI suggestion generation

## Environment Variables

Required environment variables (set in `conf/.env`):
- `BACKEND_NGROK_URL` - Backend API URL
- `FRONTEND_NGROK_URL` - Frontend ngrok URL
- `NEXT_PUBLIC_API_BASE_URL` - Public API base URL

## Development Notes

### ngrok Integration
- Automatic `ngrok-skip-browser-warning` header inclusion
- CORS configuration for ngrok domains
- Environment-based URL switching

### State Management
- Local state with React hooks
- Session data persistence via backend
- Optimistic updates for better UX

### Error Handling
- Toast notifications for user feedback
- Graceful API error handling
- Loading states for async operations

## Testing

```bash
npm test
```

Tests cover API error handling and user interactions.

## Deployment

The frontend is containerized and deployed via Docker Compose. For production deployment:

1. Build the Docker image
2. Set production environment variables
3. Deploy with your preferred container orchestration

## Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation as needed
4. Ensure ngrok compatibility for external access
