# UI Integration - Pipeline Stages & Spec-Kit Results

## Overview

The SpecAlign UI has been enhanced to:
1. **Display a multi-step loading indicator** showing the analysis pipeline stages
2. **Surface spec-kit results** alongside existing security analysis
3. **Maintain full backwards compatibility** with the existing API

## Features

### 1. Multi-Step Pipeline Indicator

When analyzing a prompt, the UI displays three stages:

```
┌─────────────────────────────┐
│ ○ Spec-kit Analysis         │  ← Step 1: Spec-kit workflow validation
│   Workflow & spec validation│
├─────────────────────────────┤
│ ○ Security Analysis         │  ← Step 2: Dev-spec-kit security rules
│   Dev-spec-kit rules engine │
├─────────────────────────────┤
│ ○ Finalizing                │  ← Step 3: Risk assessment & curation
│   Risk assessment & curation│
└─────────────────────────────┘
```

**Stage States:**
- **Pending** (○): Not started yet
- **Active** (spinner): Currently running
- **Completed** (✓): Finished successfully
- **Warning** (⚠): Completed with issues (spec-kit only)

**Visual Feedback:**
- Active stages have a purple glowing border
- Completed stages have a green border
- The spinner animates while processing
- "Analysis complete ✓" message appears when done

### 2. Spec-Kit Results Panel

When spec-kit is enabled (`USE_SPEC_KIT=true`), a new panel appears showing:

**Success Case:**
```
┌─────────────────────────────────────────┐
│ Spec-kit Analysis            [Success]  │
├─────────────────────────────────────────┤
│ ℹ Spec-kit provides workflow and spec-  │
│   driven development insights. Security │
│   decisions come from the security      │
│   analyzer.                             │
├─────────────────────────────────────────┤
│ Summary: spec-kit completed             │
│                                         │
│ ▶ View raw output                       │
└─────────────────────────────────────────┘
```

**Failure Case:**
```
┌─────────────────────────────────────────┐
│ Spec-kit Analysis            [Failed]   │
├─────────────────────────────────────────┤
│ ℹ Spec-kit provides workflow insights   │
├─────────────────────────────────────────┤
│ ⚠ Spec-kit run failed. Fallback to     │
│   security analysis only. The security  │
│   analyzer has completed successfully.  │
└─────────────────────────────────────────┘
```

**Not Enabled:**
- Panel is hidden when `spec_kit_enabled: false`
- No visual clutter for default users

### 3. Backwards Compatibility

**No changes to existing functionality:**
- ✅ Risk level badge (High/Medium/Low) unchanged
- ✅ Security summary unchanged
- ✅ Issues list unchanged
- ✅ Curated prompt unchanged
- ✅ API endpoint unchanged (`POST /api/analyze`)
- ✅ Response format backwards compatible

**New fields in API response:**
```json
{
  "risk_level": "Low",
  "devspec_findings": [],
  "spec_kit_enabled": false,
  "spec_kit_success": null,
  "spec_kit_raw_output": null,
  "spec_kit_summary": null
}
```

When spec-kit is disabled (default):
- `spec_kit_enabled` = `false`
- All other spec-kit fields = `null`
- UI hides the spec-kit panel

## User Experience Flow

### Default Mode (spec-kit disabled)

1. User enters prompt
2. Clicks "Analyze Prompt" (or Ctrl/Cmd+Enter)
3. Pipeline indicator appears in left column:
   - "Spec-kit Analysis" → Active → Completed (✓)
   - "Security Analysis" → Active → Completed (✓)
   - "Finalizing" → Active → Completed (✓)
4. Results appear in right column:
   - Risk badge
   - Security summary
   - Issues (if any)
   - Curated prompt
5. Pipeline shows "Analysis complete ✓"

### With Spec-Kit Enabled

1. User enters prompt
2. Clicks "Analyze Prompt"
3. Pipeline indicator shows same stages
4. Results include additional "Spec-kit Analysis" panel
5. Panel shows:
   - Success/Failed badge
   - Informational notice
   - Summary text
   - Collapsible raw output

## Implementation Details

### State Management

```javascript
const [stage, setStage] = useState('idle');
// States: 'idle' | 'running_spec' | 'running_security' | 'finalizing' | 'done' | 'error'

const [loading, setLoading] = useState(false);
const [result, setResult] = useState(null);
const [showSpecKitDetails, setShowSpecKitDetails] = useState(false);
```

### Stage Transitions

```javascript
// Stage 1: Start with spec-kit
setStage('running_spec');

// Stage 2: After 650ms → security analysis
setTimeout(() => setStage('running_security'), 650);

// Stage 3: After 1300ms → finalizing
setTimeout(() => setStage('finalizing'), 1300);

// Stage 4: On API response → done
setStage('done');
```

**Note:** Stage transitions are client-side UX polish. The backend pipeline runs in parallel, but we simulate stages for better user feedback.

### Component Structure

```
App.jsx
├── Left Column
│   ├── Prompt Input Panel
│   │   ├── Textarea (disabled while loading)
│   │   ├── Analyze Button (disabled while loading)
│   │   └── API Info
│   └── Pipeline Panel (shown when analyzing or done)
│       ├── Stage 1: Spec-kit Analysis
│       ├── Stage 2: Security Analysis
│       ├── Stage 3: Finalizing
│       └── Complete/Error Message
└── Right Column
    ├── Risk Badge
    ├── Security Summary
    ├── Issues Panel
    ├── Spec-Kit Panel (if enabled)
    └── Curated Prompt
```

## Styling

### Pipeline Indicator Colors

- **Purple** (`#8b5cf6`): Active stage border & spinner
- **Green** (`#22c55e`): Completed stages
- **Yellow** (`#f59e0b`): Warning icon (spec-kit failed)
- **Gray** (`#4a4a4a`): Pending stages

### Spec-Kit Panel Colors

- **Purple** (`#8b5cf6`): Panel border, info icon, toggle button
- **Green** (`#22c55e`): Success badge
- **Yellow** (`#f59e0b`): Warning badge, failure notice

### Animations

```css
@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinner-small {
  animation: spin 0.6s linear infinite;
}

.pipeline-stage.active {
  transition: all 0.3s ease;
  box-shadow: 0 0 12px rgba(139, 92, 246, 0.3);
}
```

## Testing

### Test Scenarios

**1. Default Mode (spec-kit off)**
```bash
# Backend already running on :8000
# Frontend on :3000

# Submit a safe prompt:
"Build a secure API with OAuth2, HTTPS, and bcrypt"

# Expected:
✓ Pipeline shows all 3 stages completing
✓ Risk level: Low
✓ No spec-kit panel visible
✓ Security analysis completes normally
```

**2. With Spec-Kit Enabled**
```bash
# Stop backend
# Restart with: USE_SPEC_KIT=true uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Submit same prompt

# Expected:
✓ Pipeline shows all 3 stages completing
✓ Stage 1 shows ✓ (not ⚠) if spec-kit succeeds
✓ Spec-kit panel appears with "Success" badge
✓ Summary shows: "spec-kit completed"
✓ Security analysis identical (same risk/findings)
```

**3. Error Handling**
```bash
# Stop backend

# Submit prompt

# Expected:
✓ Pipeline shows "Analysis failed ✕"
✓ Error message displayed
✓ Prompt input not cleared (can retry)
✓ Submit button re-enabled
```

### Manual Testing

```bash
# Terminal 1: Backend
cd /workspaces/ai-safety-orchestrator
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd /workspaces/ai-safety-orchestrator/ui
npm run dev

# Browser: http://localhost:3000
# Test with various prompts
```

### Automated Test
```bash
cd /workspaces/ai-safety-orchestrator
bash test_ui_integration.sh
```

## Deployment Considerations

### Environment Variables

**Backend:**
```bash
# Default (spec-kit disabled)
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Enable spec-kit
USE_SPEC_KIT=true uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**Frontend:**
- No environment variables needed
- Auto-detects backend URL from current origin
- Works in Codespaces and localhost

### Build for Production

```bash
cd ui
npm run build

# Serve with static file server
npm run preview
```

## Troubleshooting

### Pipeline stages not appearing
- **Cause:** Backend not responding
- **Fix:** Check `http://localhost:8000/health`

### Spec-kit panel always hidden
- **Cause:** `USE_SPEC_KIT` not set on backend
- **Fix:** Restart backend with `USE_SPEC_KIT=true`

### Stages complete too fast
- **Cause:** Backend response < 650ms
- **Note:** This is fine! Stages will still show completed state

### Frontend shows old version
- **Cause:** Browser cache
- **Fix:** Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

## Future Enhancements

Possible improvements:
- [ ] WebSocket connection for real-time stage updates
- [ ] Elapsed time counter for each stage
- [ ] Animated progress bar between stages
- [ ] Stage-specific error messages
- [ ] Export analysis results (PDF/JSON)

## References

- Backend Integration: [SPEC_KIT_INTEGRATION.md](../SPEC_KIT_INTEGRATION.md)
- API Documentation: http://localhost:8000/docs
- Frontend Code: `ui/src/App.jsx`
- Styles: `ui/src/App.css`
