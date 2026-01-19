# Quick Guide: Adding GitHub Secrets

Since you now have collaborator access, follow these steps:

## Step-by-Step Instructions

### 1. Go to the Repository
Navigate to: `https://github.com/vavinash992/open-mentions`

### 2. Open Settings
- Click the **Settings** tab (in the top navigation bar, next to Code, Issues, etc.)
- If you don't see Settings, you may need Admin access (contact vavinash)

### 3. Go to Secrets
- In the left sidebar, scroll down and click **Secrets and variables**
- Click **Actions** (this will take you to the Actions secrets page)

### 4. Add Each Secret

You'll need to add 4 secrets. For each one:

1. Click the **New repository secret** button (green button on the right)
2. Enter the Name (exact name as shown below)
3. Paste the Value
4. Click **Add secret**

#### Secret 1: AZURE_OPENAI_API_KEY
- **Name**: `AZURE_OPENAI_API_KEY`
- **Value**: Your Azure OpenAI API Key (from Azure Portal → Keys and Endpoint → KEY 1 or KEY 2)

#### Secret 2: AZURE_OPENAI_ENDPOINT
- **Name**: `AZURE_OPENAI_ENDPOINT`
- **Value**: Your endpoint URL
  - Format: `https://your-resource-name.cognitiveservices.azure.com`
  - Example: `https://nanda-mkk7puck-eastus2.cognitiveservices.azure.com`

#### Secret 3: AZURE_OPENAI_DEPLOYMENT_NAME
- **Name**: `AZURE_OPENAI_DEPLOYMENT_NAME`
- **Value**: Your deployment name (e.g., `gpt-4o-mini`)

#### Secret 4: AZURE_OPENAI_API_VERSION
- **Name**: `AZURE_OPENAI_API_VERSION`
- **Value**: `2025-01-01-preview`

### 5. Verify
After adding all 4 secrets, you should see them listed on the Secrets page. The values will be masked (shown as `••••••••`).

## Visual Path
```
GitHub Repository
  → Settings (top nav)
    → Secrets and variables (left sidebar)
      → Actions
        → New repository secret (green button)
```

## Finding Your Azure Values

If you need to find your Azure OpenAI values:

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your Azure OpenAI resource
3. **Keys and Endpoint** section:
   - Copy **KEY 1** or **KEY 2** → `AZURE_OPENAI_API_KEY`
   - Copy **Endpoint** → `AZURE_OPENAI_ENDPOINT`
4. **Deployments** section:
   - Copy deployment name → `AZURE_OPENAI_DEPLOYMENT_NAME`

## Test the Workflow

Once secrets are added:

1. Go to the **Actions** tab
2. Find **Periodic Keyword Monitoring** workflow
3. Click **Run workflow** (right side)
4. Select your branch (e.g., `feature/scraper`)
5. Click **Run workflow**

The workflow should now be able to access your Azure OpenAI credentials!

## Troubleshooting

**Can't see Settings tab?**
- You might only have Write access, not Admin access
- Ask vavinash to upgrade your permissions to Admin

**Can't see "Secrets and variables"?**
- Make sure you're in the repository Settings (not your profile settings)
- You need at least Write access with Actions enabled

**Workflow still fails?**
- Double-check secret names match exactly (case-sensitive)
- Verify the API key is correct and active
- Check the workflow logs in Actions tab for specific errors
