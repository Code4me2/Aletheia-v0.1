# n8n Credential Setup

Since n8n doesn't have a direct API for credential import, you have two options:

## Option 1: Manual Configuration (Recommended)
The Hierarchical Summarization node supports manual database configuration:
1. In the node settings, set "Database Configuration" to "Manual"
2. The database credentials will be automatically filled from environment variables

## Option 2: Manual Credential Creation
1. Access n8n at http://localhost:5678
2. Go to Credentials → New → PostgreSQL
3. Use these values:
   - Name: PostgreSQL - Aletheia
   - Host: db
   - Database: aletheia_db
   - User: aletheia_user
   - Password: (check your .env file)
   - SSL: Disable

## Option 3: Use Workflow Template
Import the workflow template at `workflow_json/hierarchical-summarization-template.json`
which includes the database configuration.

## Future Automation
When n8n adds API support for credential management, we can automate this process.
