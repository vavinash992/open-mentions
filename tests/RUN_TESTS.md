# Quick Reference: Running Tests

## Commands to Run Tests

### 1. Test LLM Processor (Fast - ~30 seconds)
```bash
uv run python tests/test_llm_processor.py
```
OR
```bash
python -m tests.test_llm_processor
```

**What it does:**
- Creates a mock Reddit post about OpenAI
- Tests Azure OpenAI classification
- Verifies all fields are populated correctly

---

### 2. Test Orchestrator (Medium - ~2-5 minutes)
```bash
uv run python tests/test_orchestrator_manual.py
```
OR
```bash
python -m tests.test_orchestrator_manual
```

**What it does:**
- Searches for "Nvidia" across all platforms
- Processes results through LLM
- Shows first 3 classified results
- Displays summary statistics

---

### 3. Test API Endpoint (Medium - ~2-5 minutes)
```bash
uv run python tests/test_api.py
```
OR
```bash
python -m tests.test_api
```

**What it does:**
- Sends POST request to `/api/v1/search`
- Verifies response structure
- Checks all expected keys
- Shows first mention preview

---

## Quick Test All (Sequential)

```bash
# Run all three tests
uv run python tests/test_llm_processor.py && \
uv run python tests/test_orchestrator_manual.py && \
uv run python tests/test_api.py
```

---

## Prerequisites

Make sure you have:
1. `.env` file in project root with Azure OpenAI credentials
2. Dependencies installed: `uv sync`

---

## Expected Test Duration

- **test_llm_processor**: ~30 seconds (single item classification)
- **test_orchestrator_manual**: ~2-5 minutes (scrapes 4 platforms)
- **test_api**: ~2-5 minutes (full API request)
