#!/bin/bash

# Test script to simulate a GitHub webhook for failed workflow run

echo "🧪 Testing CI/CD Fixer Agent with simulated webhook..."

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Error: Backend server is not running on localhost:8000"
    echo "Please start the server with: ./run.sh"
    exit 1
fi

# Send a test webhook payload
echo "📡 Sending test webhook payload..."

curl -X POST "http://localhost:8000/webhook/github" \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: workflow_run" \
  -d '{
    "action": "completed",
    "workflow_run": {
      "id": 12345678,
      "name": "CI",
      "status": "completed",
      "conclusion": "failure",
      "run_number": 42,
      "head_branch": "main",
      "triggering_actor": {
        "login": "developer"
      }
    },
    "repository": {
      "name": "test-repo",
      "owner": {
        "login": "test-owner"
      }
    }
  }'

echo ""
echo ""
echo "✅ Test webhook sent!"
echo "📋 Check the server logs to see the processing"
echo "🌐 View results at: http://localhost:8000/runs"
