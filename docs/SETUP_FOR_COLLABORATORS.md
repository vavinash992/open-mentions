# Setting Up GitHub Secrets - For Repository Collaborators

Since this repository is owned by **vavinash**, here are your options for setting up the required GitHub Secrets:

## Option 1: Ask Repository Owner to Add Secrets (Recommended)

### Steps for Repository Owner (vavinash):

1. Go to the repository: `https://github.com/vavinash992/open-mentions`
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Add all 4 secrets:
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_DEPLOYMENT_NAME`
   - `AZURE_OPENAI_API_VERSION`

### What You Need to Provide:

Send vavinash the following information so they can add the secrets:

```
Secret Name: AZURE_OPENAI_API_KEY
Value: [Your Azure OpenAI API Key]

Secret Name: AZURE_OPENAI_ENDPOINT
Value: [Your Azure OpenAI Endpoint URL]

Secret Name: AZURE_OPENAI_DEPLOYMENT_NAME
Value: [Your Deployment Name, e.g., gpt-4o-mini]

Secret Name: AZURE_OPENAI_API_VERSION
Value: 2025-01-01-preview
```

**Important**: Share these values securely (e.g., through encrypted message, not in public chat).

## Option 2: Get Admin/Collaborator Access

If vavinash gives you **Admin** or **Write** access to the repository:

1. Ask vavinash to:
   - Go to repository **Settings** → **Collaborators**
   - Add you as a collaborator with **Admin** or **Write** permissions
2. Once added, follow the steps in `GITHUB_SECRETS_SETUP.md` to add secrets yourself

## Option 3: Fork the Repository (Personal Use)

If you want to run your own monitoring without modifying the main repo:

### Steps:

1. **Fork the repository**:
   - Go to `https://github.com/vavinash992/open-mentions`
   - Click the **Fork** button (top right)
   - This creates a copy in your GitHub account

2. **Add secrets to your fork**:
   - Go to **Your Fork** → **Settings** → **Secrets and variables** → **Actions**
   - Add all 4 secrets as described in `GITHUB_SECRETS_SETUP.md`

3. **Update the workflow** (optional):
   - The workflow will run in your fork
   - Database updates will be committed to your fork, not the original repo

4. **Pull changes from upstream** (to keep your fork updated):
   ```bash
   # Add upstream remote
   git remote add upstream https://github.com/vavinash992/open-mentions.git

   # Pull updates
   git fetch upstream
   git merge upstream/feature/scraper
   ```

## Recommended Approach

**For shared development**: Ask vavinash to add the secrets (Option 1)
- Keeps the monitoring centralized
- All collaborators benefit
- Single source of truth

**For personal testing**: Fork the repo (Option 3)
- Test changes without affecting main repo
- Use your own API keys
- Good for experimentation

## Quick Message Template

Send this to vavinash:

```
Hi! I need to set up GitHub Secrets for the automated monitoring workflow.
Could you please add these 4 secrets to the repository?

1. AZURE_OPENAI_API_KEY: [value]
2. AZURE_OPENAI_ENDPOINT: [value]
3. AZURE_OPENAI_DEPLOYMENT_NAME: [value]
4. AZURE_OPENAI_API_VERSION: 2025-01-01-preview

Or if you prefer, you could give me admin access and I can add them myself.

Thanks!
```

## Security Notes

- Never commit secrets to the repository code
- Share secret values through secure channels only
- Consider using Azure Key Vault or similar for enterprise setups
- Rotate keys periodically
