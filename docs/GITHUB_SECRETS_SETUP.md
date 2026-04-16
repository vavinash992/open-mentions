# Setting Up GitHub Secrets for Automated Monitoring

This guide explains how to set up the required GitHub Secrets for the automated keyword monitoring workflow.

## Important: Repository Ownership

If the repository is owned by someone else (e.g., a friend or organization), you'll need to either:
1. **Ask the repository owner** to add the secrets (recommended for shared projects)
2. **Get collaborator/admin access** from the owner to add secrets yourself
3. **Fork the repository** and set up secrets in your own fork (for personal use)

## Required Secrets

The following secrets need to be configured in your GitHub repository:

1. `AZURE_OPENAI_API_KEY` - Your Azure OpenAI API key
2. `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint URL
3. `AZURE_OPENAI_DEPLOYMENT_NAME` - Your Azure OpenAI deployment name
4. `AZURE_OPENAI_API_VERSION` - The API version to use

## Step-by-Step Instructions

### 1. Navigate to Repository Settings

1. Go to your GitHub repository on GitHub.com
2. Click on the **Settings** tab (located in the top navigation bar)
3. Make sure you have admin/write access to the repository (you'll need it to add secrets)

### 2. Access Secrets and Variables

1. In the left sidebar, click on **Secrets and variables**
2. Click on **Actions** (this takes you to the Actions secrets page)

### 3. Add Each Secret

For each of the 4 secrets, follow these steps:

1. Click the **New repository secret** button (green button on the right)
2. Enter the secret name (e.g., `AZURE_OPENAI_API_KEY`) exactly as shown
3. Enter the secret value (paste your actual API key/endpoint/etc.)
4. Click **Add secret**

Repeat this for all 4 secrets:
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT_NAME`
- `AZURE_OPENAI_API_VERSION`

### 4. Verify Secrets Are Added

After adding all secrets, you should see them listed on the Secrets page. The values will be masked (shown as `••••••••`).

## Where to Find Your Azure OpenAI Values

### AZURE_OPENAI_API_KEY
- Log into Azure Portal
- Go to your Azure OpenAI resource
- Navigate to **Keys and Endpoint** section
- Copy either **KEY 1** or **KEY 2**

### AZURE_OPENAI_ENDPOINT
- In the same **Keys and Endpoint** section
- Copy the **Endpoint** URL (e.g., `https://your-resource.cognitiveservices.azure.com`)

### AZURE_OPENAI_DEPLOYMENT_NAME
- Go to **Deployments** section in your Azure OpenAI resource
- Copy the name of your deployment (e.g., `gpt-4o-mini`)

### AZURE_OPENAI_API_VERSION
- Check the API documentation or use: `2025-01-01-preview` (or your preferred version)

## Alternative: Using Repository Variables

If you prefer to use Repository Variables instead of Secrets (for non-sensitive data), you can:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click on the **Variables** tab
3. Click **New repository variable**
4. Add variables (note: variables are visible in logs, so only use for non-sensitive data)

**Note:** For API keys and endpoints, always use **Secrets**, not Variables, as they contain sensitive information.

## Testing the Setup

After adding the secrets, you can test the workflow:

1. Go to the **Actions** tab in your repository
2. Find the **Periodic Keyword Monitoring** workflow
3. Click on it, then click **Run workflow**
4. Select the branch (e.g., `feature/scraper`)
5. Click **Run workflow**

The workflow will use the secrets you've configured.

## Troubleshooting

### Secrets Not Available
- Ensure you have write/admin access to the repository
- Verify the secret names match exactly (case-sensitive)
- Check that you're in the correct repository

### Workflow Fails with Authentication Error
- Double-check that the API key is correct
- Verify the endpoint URL is properly formatted
- Ensure the deployment name exists and is active

### Secrets Not Visible in Logs
- This is expected behavior - GitHub masks secrets in logs
- If you need to debug, check the workflow error messages
- Make sure the secret values are pasted correctly (no extra spaces)

## Security Best Practices

1. **Never commit secrets to code** - Always use GitHub Secrets
2. **Rotate keys regularly** - Update secrets periodically
3. **Use least privilege** - Only give necessary permissions
4. **Monitor access** - Review who has access to secrets
5. **Use branch protection** - Protect your main/master branch

## Next Steps

Once secrets are configured:
1. The workflow will automatically run every 6 hours
2. You can manually trigger it via the Actions tab
3. Add tracked keywords to your database using the `TrackedKeyword` model
4. Monitor the workflow runs and logs in the Actions tab
