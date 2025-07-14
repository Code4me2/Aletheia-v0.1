# n8n Workflows for Court Processor

## FLP Enhancement Workflow

The `flp_enhancement_workflow.json` provides an n8n workflow for enhancing court opinions with Free Law Project tools.

### What it does:

1. **Gets Pending Opinions**: Fetches up to 10 opinions that haven't been enhanced yet
2. **Rate Limits**: Processes one opinion every 2 seconds to avoid overwhelming the API
3. **Enhances Each Opinion**: Calls the FLP enhancement API for each opinion
4. **Summarizes Results**: Counts successful vs failed enhancements
5. **Gets Stats**: Retrieves overall enhancement statistics

### How to use:

1. Import the workflow into n8n:
   - Go to n8n interface (http://localhost:8080/n8n/)
   - Click "Import from File"
   - Select `flp_enhancement_workflow.json`

2. Configure the workflow:
   - Update URLs if court-processor is on a different host
   - Adjust rate limiting if needed (default: 2 seconds between requests)
   - Change batch size (default: 10 opinions per run)

3. Run the workflow:
   - Click "Execute Workflow" to run manually
   - Or set up a schedule trigger to run periodically

### Scheduling Enhancement

To run enhancements automatically, replace the manual trigger with a Cron node:

```json
{
  "parameters": {
    "triggerTimes": {
      "item": [
        {
          "mode": "everyX",
          "value": 1,
          "unit": "hours"
        }
      ]
    }
  },
  "name": "Every Hour",
  "type": "n8n-nodes-base.cron",
  "typeVersion": 1
}
```

### Monitoring

The workflow provides:
- Number of opinions processed
- Success/failure counts
- Overall enhancement statistics

### Advanced Usage

#### Process Specific Source

Modify the "Get Pending Opinions" node to process only Juriscraper or CourtListener opinions:

```json
"qs": {
  "source": "opinions",  // or "cl_opinions" 
  "limit": "10"
}
```

#### Email Notifications

Add an Email node after "Get Enhancement Stats" to send results:

```json
{
  "parameters": {
    "fromEmail": "court-processor@example.com",
    "toEmail": "admin@example.com",
    "subject": "FLP Enhancement Report",
    "text": "Processed {{ $node['Summarize Results'].json.total_processed }} opinions.\n\nSuccessful: {{ $node['Summarize Results'].json.successful }}\n\nStats:\n{{ JSON.stringify($json, null, 2) }}"
  },
  "name": "Send Report",
  "type": "n8n-nodes-base.emailSend"
}
```

#### Error Handling

Add an Error Trigger node to catch and report failures:

```json
{
  "parameters": {},
  "name": "On Error",
  "type": "n8n-nodes-base.errorTrigger",
  "typeVersion": 1
}
```

### Integration with Other Workflows

This workflow can be triggered by other workflows using the Execute Workflow node:

```json
{
  "parameters": {
    "workflowId": "flp_enhancement_001"
  },
  "name": "Run FLP Enhancement",
  "type": "n8n-nodes-base.executeWorkflow"
}
```