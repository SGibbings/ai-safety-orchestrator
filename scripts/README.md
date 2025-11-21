# Scripts

This directory contains utility scripts for running, testing, and validating the AI Safety Orchestrator.

## 🚀 Startup Scripts

### `start.sh`
Starts both backend and frontend services.
```bash
./scripts/start.sh
```

### `stop.sh`
Stops all running services.
```bash
./scripts/stop.sh
```

### `server.sh`
Starts only the backend API server.
```bash
./scripts/server.sh
```

## 🧪 Testing Scripts

### `test_api.sh`
Tests the API endpoints with various prompts.
```bash
./scripts/test_api.sh
```

### `test_full_stack.sh`
Runs full stack integration tests.
```bash
./scripts/test_full_stack.sh
```

### `test_ui_integration.sh`
Tests UI integration with backend.
```bash
./scripts/test_ui_integration.sh
```

### `validate_dev_progression.sh`
Validates dev progression scenarios implementation.
```bash
./scripts/validate_dev_progression.sh
```

## 📊 Demo Scripts

### `demo_spec_breakdown.sh`
Demonstrates spec breakdown and quality warnings features.
```bash
./scripts/demo_spec_breakdown.sh
```

### `example_usage.py`
Python example showing how to use the API programmatically.
```bash
python scripts/example_usage.py
```

## 💡 Usage Tips

- Make scripts executable: `chmod +x scripts/*.sh`
- Run from project root: `./scripts/script_name.sh`
- Check script output for detailed results
- Scripts handle service startup/shutdown automatically
