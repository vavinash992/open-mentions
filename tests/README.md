# Test Scripts for Open Mentions

This directory contains test scripts to verify the LLM Processor, Orchestrator, and API endpoint functionality.

## Prerequisites

1. Ensure you have a `.env` file in the project root with your Azure OpenAI credentials:
   ```bash
   AZURE_OPENAI_API_KEY="your_key_here"
   AZURE_OPENAI_ENDPOINT="https://your-endpoint.cognitiveservices.azure.com"
   AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o-mini"
   AZURE_OPENAI_API_VERSION="2025-01-01-preview"
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

## Test Scripts

### 1. LLM Processor Test (`test_llm_processor.py`)

Tests the LLM processor with a mock ScrapedItem to verify that Azure OpenAI correctly populates:
- `relevance_score`
- `is_relevant`
- `sentiment`
- `emotion`
- `summary`

**Run:**
```bash
uv run python tests/test_llm_processor.py
```

Or:
```bash
python -m tests.test_llm_processor
```

**Expected output:**
- Classification results with all fields populated
- Validation checks for each field
- Summary showing passed/failed checks

---

### 2. Orchestrator Integration Test (`test_orchestrator_manual.py`)

Tests the full orchestrator with a real-world keyword search across all platforms.

**Run:**
```bash
uv run python tests/test_orchestrator_manual.py
```

Or:
```bash
python -m tests.test_orchestrator_manual
```

**Expected output:**
- Total number of mentions found
- Platform breakdown
- Sentiment breakdown
- First 3 classified results with all fields

**Note:** This test may take several minutes as it:
1. Scrapes multiple platforms (Reddit, Hacker News, Dev.to, Stack Exchange)
2. Processes all results through Azure OpenAI
3. Filters to relevant mentions only

**To test with a different company**, edit the `company_name` variable in the script.

---

### 3. API Endpoint Test (`test_api.py`)

Tests the FastAPI `/api/v1/search` endpoint using TestClient.

**Run:**
```bash
uv run python tests/test_api.py
```

Or:
```bash
python -m tests.test_api
```

**Expected output:**
- Status code verification (200 OK)
- Response structure validation
- All expected keys present
- Summary statistics
- First mention preview

**Note:** This test may take several minutes as it makes a real API call that scrapes and classifies mentions.

---

## Running All Tests

To run all tests sequentially:

```bash
# Test 1: LLM Processor
uv run python tests/test_llm_processor.py

# Test 2: Orchestrator (takes longer)
uv run python tests/test_orchestrator_manual.py

# Test 3: API Endpoint (takes longer)
uv run python tests/test_api.py
```

---

## Troubleshooting

### Environment Variables Not Found
If you see errors about missing environment variables:
- Ensure `.env` file exists in the project root
- Check that `.env` contains all required Azure OpenAI variables
- Verify file permissions

### Import Errors
If you see import errors:
- Make sure you're running from the project root directory
- Ensure all dependencies are installed: `uv sync`
- Check that `src/mentions/` directory exists

### Azure OpenAI API Errors
If you see API errors:
- Verify your API key is correct
- Check your endpoint URL (should not have trailing slash)
- Ensure your deployment name matches your Azure resource
- Verify API version compatibility

### Timeouts
Some tests may take a long time:
- LLM processing can take several seconds per item
- Scraping multiple platforms takes time
- Consider reducing `max_results_per_platform` in test scripts for faster testing

---

## Test Output Format

All tests use formatted output with:
- Clear section headers
- Validation check indicators (✓/✗)
- Summary statistics
- Easy-to-read formatting

Tests will show:
- ✓ Green checkmarks for passed checks
- ✗ Red X marks for failed checks
- Detailed error messages when something fails
