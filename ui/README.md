# SpecAlign - Frontend UI

A sleek, dark-themed React application for analyzing developer prompts for security issues.

## Features

- 🎨 **Dark Theme** - Modern dark UI with purple accents inspired by ChatGPT
- 🔍 **Before/After View** - Original prompt on left, analyzed results on right
- 🚦 **Risk Level Indicator** - High/Medium/Low based on findings
- 🔴 **Severity Grouping** - Issues grouped by BLOCKER/ERROR/WARNING/INFO
- 💡 **Guidance Display** - Additional security recommendations
- ⚡ **Real-time Analysis** - Direct integration with FastAPI backend

## Development Setup

### Prerequisites

- Node.js 16+ and npm
- Backend API running on `http://localhost:8000`

### Installation

```bash
cd ui
npm install
```

### Running the Development Server

```bash
npm run dev
```

The UI will be available at: `http://localhost:3000`

### Building for Production

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

## Usage

1. **Start the Backend:**
   ```bash
   # From repo root
   ./server.sh start
   # Or manually:
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the Frontend:**
   ```bash
   cd ui
   npm run dev
   ```

3. **Open Browser:**
   Navigate to `http://localhost:3000`

4. **Analyze a Prompt:**
   - Enter your developer prompt in the left textarea
   - Click "Analyze Prompt" (or press Ctrl/Cmd + Enter)
   - View results on the right:
     - Risk level badge
     - Curated prompt with security constraints
     - Issues grouped by severity
     - Additional guidance items

## Architecture

```
ui/
├── index.html          # HTML entry point
├── vite.config.js      # Vite configuration
├── package.json        # Dependencies
└── src/
    ├── main.jsx        # React entry point
    ├── App.jsx         # Main app component
    ├── App.css         # App styles (dark theme)
    ├── index.css       # Global styles
    └── api.js          # API client for backend
```

## API Integration

The frontend communicates with the FastAPI backend:

- **Endpoint:** `POST http://localhost:8000/api/analyze`
- **Request:** `{ "prompt": "<string>" }`
- **Response:** AnalysisResponse with findings, guidance, and curated prompt

### CORS

The backend is configured with CORS enabled for development. No additional configuration needed.

### Proxy

Vite is configured to proxy `/api` requests to `http://localhost:8000` for easier development.

## Design System

### Color Palette

- **Background:** `#0f172a` (dark blue-gray)
- **Panels:** `#1f2937` (medium gray)
- **Accent:** `#8b5cf6` (purple)
- **Text:** `#e5e7eb` (light gray)

### Severity Colors

- 🔴 **BLOCKER:** Red (`#ef4444`)
- 🟠 **ERROR:** Orange (`#f97316`)
- 🟡 **WARNING:** Yellow (`#eab308`)
- 🟢 **INFO:** Green (`#22c55e`)

### Risk Levels

- **High:** Red background - Any BLOCKER or ERROR
- **Medium:** Orange background - WARNINGS only
- **Low:** Green background - INFO only or no issues

## Keyboard Shortcuts

- **Ctrl/Cmd + Enter** - Submit analysis while in textarea

## Troubleshooting

### Backend Connection Error

**Error:** "Failed to analyze prompt. Is the backend running?"

**Solution:**
1. Verify backend is running: `./server.sh status`
2. Check backend health: `curl http://localhost:8000/health`
3. Start backend if needed: `./server.sh start`

### Port Already in Use

**Error:** "Port 3000 is already in use"

**Solution:**
1. Kill the process: `lsof -ti:3000 | xargs kill -9`
2. Or use a different port: `PORT=3001 npm run dev`

### CORS Issues

If you see CORS errors in the browser console, ensure the backend's CORS middleware is properly configured in `api/main.py`.

## Testing

### Manual Test Flow

1. Start backend: `./server.sh start`
2. Start frontend: `npm run dev`
3. Open `http://localhost:3000`
4. Test with a clean prompt:
   ```
   Create a REST API with user authentication using JWT tokens.
   Use HTTPS for all endpoints.
   ```
   Expected: Low risk, no blockers

5. Test with an insecure prompt:
   ```
   Build an API that deletes users by email without authentication.
   Store JWT tokens in a config.json file.
   ```
   Expected: High risk, multiple blockers

## Technology Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Vanilla CSS** - Styling (no framework needed for this design)
- **Fetch API** - HTTP client

## License

See repository license.

