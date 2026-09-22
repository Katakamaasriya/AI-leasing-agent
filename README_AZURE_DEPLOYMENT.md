# Azure Cloud Deployment Guide

This guide will help you deploy the AI Leasing Agent to Microsoft Azure using your Azure credits and Azure OpenAI service.

## Prerequisites

- Azure account with credits
- Azure OpenAI resource
- Microsoft 365 tenant (for calendar integration)
- Basic Azure knowledge

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Azure Front Door                         │
│                   (Load Balancer & CDN)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐      ┌────────▼────────┐
│  Azure Web Apps │      │  Azure Functions│
│  (Streamlit UI) │      │  (Webhooks)     │
└────────┬────────┘      └────────┬────────┘
         │                        │
         └──────────┬─────────────┘
                    │
         ┌──────────▼──────────┐
         │  Azure Container   │
         │  Instances (FastAPI)│
         └──────────┬──────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌───▼────┐    ┌────▼────┐    ┌────▼────┐
│Azure   │    │Azure    │    │Azure    │
│OpenAI  │    │SQL      │    │Blob     │
│Service │    │Database │    │Storage  │
└────────┘    └─────────┘    └─────────┘
```

## Step 1: Set Up Azure Resources

### 1.1 Create Azure OpenAI Resource

```bash
# Create resource group
az group create --name leasing-agent-rg --location eastus

# Create Azure OpenAI resource
az cognitiveservices account create \
  --name leasing-openai \
  --resource-group leasing-agent-rg \
  --kind OpenAI \
  --sku S0 \
  --location eastus

# Deploy GPT-4o-mini model
az cognitiveservices account deployment create \
  --name leasing-openai \
  --resource-group leasing-agent-rg \
  --deployment-name gpt4o-mini \
  --model-name gpt-4o-mini \
  --model-version "2024-07-18" \
  --model-format OpenAI \
  --capacity 10
```

### 1.2 Create Azure SQL Database

```bash
# Create SQL server
az sql server create \
  --name leasing-sql-server \
  --resource-group leasing-agent-rg \
  --location eastus \
  --admin-user leasingadmin \
  --admin-password YourStrongPassword123!

# Create SQL database
az sql db create \
  --name leasing-db \
  --server leasing-sql-server \
  --resource-group leasing-agent-rg \
  --edition GeneralPurpose \
  --family Gen5 \
  --capacity 2
```

### 1.3 Create Azure Storage Account

```bash
# Create storage account
az storage account create \
  --name leasingstorage \
  --resource-group leasing-agent-rg \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2
```

## Step 2: Configure Environment Variables

Create a `.env.production` file:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://leasing-openai.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_MODEL=gpt-4o-mini

# Azure SQL Database
DATABASE_URL=postgresql+psycopg2://leasingadmin:YourPassword@leasing-sql-server.postgres.database.azure.com:5432/leasing-db

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=your_storage_connection_string
AZURE_STORAGE_CONTAINER=leasing-uploads

# Microsoft 365 Integration
MICROSOFT_TENANT_ID=your_tenant_id
MICROSOFT_CLIENT_ID=your_client_id
MICROSOFT_CLIENT_SECRET=your_client_secret

# Email Configuration (SendGrid recommended for Azure)
SENDGRID_API_KEY=your_sendgrid_key
SMTP_FROM=noreply@yourdomain.com

# Application Configuration
APP_NAME=AI Leasing Agent
APP_ENVIRONMENT=production
LOG_LEVEL=INFO
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

## Step 3: Deploy Backend to Azure Container Instances

### 3.1 Build Docker Image

```dockerfile
# Dockerfile for FastAPI backend
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.2 Build and Push to Azure Container Registry

```bash
# Create ACR
az acr create --name leasingacr --resource-group leasing-agent-rg --sku Basic

# Build image
az acr build --registry leasingacr --image leasing-api:latest .

# Push image
az acr login --name leasingacr
```

### 3.3 Deploy to Container Instances

```bash
az container create \
  --resource-group leasing-agent-rg \
  --name leasing-api \
  --image leasingacr.azurecr.io/leasing-api:latest \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --environment-variables \
    AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY \
    AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT \
    DATABASE_URL=$DATABASE_URL
```

## Step 4: Deploy Frontend to Azure Web Apps

### 4.1 Create Web App

```bash
# Create web app
az webapp create \
  --resource-group leasing-agent-rg \
  --name leasing-frontend \
  --plan leasing-app-service-plan \
  --runtime "PYTHON:3.11"
```

### 4.2 Configure Web App

```bash
# Set environment variables
az webapp config appsettings set \
  --resource-group leasing-agent-rg \
  --name leasing-frontend \
  --settings \
    LEASING_API_URL=https://leasing-api.azurecontainer.io \
    AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY
```

### 4.3 Deploy Streamlit App

```bash
# Deploy using local git
az webapp deployment source config-local-git \
  --resource-group leasing-agent-rg \
  --name leasing-frontend \
  --repo-url https://github.com/yourusername/leasing-agent
```

## Step 5: Set Up Microsoft 365 Integration

### 5.1 Register App in Azure AD

```bash
# Create app registration
az ad app create \
  --display-name "Leasing Agent Integration" \
  --web-redirect-uris "https://leasing-frontend.azurewebsites.net/auth/callback" \
  --required-resource-accesses @manifest.json
```

### 5.2 Configure Permissions

Add these API permissions:
- `Calendars.ReadWrite`
- `Mail.Send`
- `User.Read`

### 5.3 Get Client Secret

```bash
# Create client secret
az ad app credential reset \
  --id $APP_ID \
  --append
```

## Step 6: Set Up Monitoring and Logging

### 6.1 Azure Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app leasing-agent-insights \
  --location eastus \
  --resource-group leasing-agent-rg \
  --application-type web
```

### 6.2 Configure Logging

Add to your application:

```python
from azure.monitor.opentelemetry import configure_azure_monitor

configure_azure_monitor(
    connection_string="InstrumentationKey=your-instrumentation-key"
)
```

## Step 7: Configure Custom Domain and SSL

### 7.1 Add Custom Domain

```bash
az webapp config hostname add \
  --webapp leasing-frontend \
  --resource-group leasing-agent-rg \
  --hostname leasing.yourdomain.com
```

### 7.2 Configure SSL Certificate

```bash
az webapp config ssl bind \
  --certificate-thumbprint $THUMBPRINT \
  --ssl-type SNI \
  --name leasing-frontend \
  --resource-group leasing-agent-rg
```

## Step 8: Set Up CI/CD Pipeline

### 8.1 GitHub Actions

Create `.github/workflows/azure-deploy.yml`:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Login to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Build and deploy API
        run: |
          az acr build --registry leasingacr --image leasing-api:latest .
          az container create --resource-group leasing-agent-rg --name leasing-api --image leasingacr.azurecr.io/leasing-api:latest
      
      - name: Deploy frontend
        run: |
          az webapp up --name leasing-frontend --resource-group leasing-agent-rg
```

## Step 9: Testing and Validation

### 9.1 Health Checks

```bash
# Test API health
curl https://leasing-api.azurecontainer.io/health

# Test frontend
curl https://leasing-frontend.azurewebsites.net
```

### 9.2 Monitor Performance

```bash
# View logs
az webapp log tail --name leasing-frontend --resource-group leasing-agent-rg

# View metrics
az monitor metrics list \
  --resource leasing-agent-rg \
  --metric "CPU Percentage,response-time"
```

## Cost Optimization

### Azure Cost Management

1. **Use Azure OpenAI Wisely**:
   - Use gpt-4o-mini for most conversations
   - Implement caching for common queries
   - Set rate limits to control costs

2. **Database Optimization**:
   - Use serverless tier for development
   - Scale up only for production
   - Implement connection pooling

3. **Storage Costs**:
   - Use lifecycle policies for old data
   - Compress logs and backups
   - Use appropriate storage tiers

## Security Best Practices

1. **Use Managed Identities** instead of credentials
2. **Enable Azure Defender** for threat protection
3. **Implement Azure Key Vault** for secrets
4. **Use Virtual Network** for isolation
5. **Enable DDOS Protection** for public endpoints

## Troubleshooting

### Common Issues

**Issue**: Azure OpenAI rate limits
**Solution**: Implement exponential backoff and caching

**Issue**: Database connection timeouts
**Solution**: Use connection pooling and retry logic

**Issue**: Container instance cold starts
**Solution**: Use reserved instances or scale to Azure App Service

## Scaling Considerations

- **Horizontal Scaling**: Add more container instances
- **Vertical Scaling**: Increase CPU/memory allocation
- **Geographic Distribution**: Use multiple regions
- **Load Balancing**: Implement Azure Front Door

## Backup and Disaster Recovery

1. **Database Backups**: Configure automated backups
2. **Geo-replication**: Set up secondary region
3. **Restore Testing**: Regular disaster recovery drills

## Support and Maintenance

- **Monitoring**: Set up alerts for critical metrics
- **Logging**: Centralized logs with Log Analytics
- **Updates**: Regular dependency updates
- **Testing**: Automated testing pipeline

## Next Steps

1. Set up Azure resources using the commands above
2. Configure environment variables
3. Deploy applications
4. Test integrations
5. Set up monitoring
6. Configure custom domain
7. Set up CI/CD pipeline

For detailed Azure documentation, visit: https://docs.microsoft.com/azure/