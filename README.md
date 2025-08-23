# CI/CD Fixer Agent Backend

This backend implements a powerful CI/CD failure analysis and fixing system using:

-   **Portia AI** for orchestrating multi-step agent workflows
-   **Google Gemini** for intelligent failure analysis and fix suggestions
-   **FastAPI** for the REST API server
-   **PostgreSQL (Supabase)** for scalable data persistence
-   **GitHub API** for fetching workflow data and creating issues/PRs

## Features

-   🤖 **Automated Analysis**: Detects CI/CD failures via GitHub webhooks
-   🧠 **AI-Powered Fixes**: Uses Gemini AI to analyze logs and suggest specific fixes
-   👥 **Human-in-the-Loop**: Requests approval before applying fixes
-   📊 **Dashboard Ready**: Provides REST API for frontend dashboard
-   🔒 **Secure**: Webhook signature verification and environment-based configuration
-   📝 **Audit Trail**: Complete logging of all analysis and decisions

## Quick Start

1. **Setup the environment:**

    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```

2. **Configure API keys in `.env`:**

    ```bash
    cp .env.example .env
    # Edit .env with your API keys
    ```

3. **Start the server:**

    ```bash
    chmod +x run.sh
    ./run.sh
    ```

4. **Test with a simulated webhook:**
    ```bash
    chmod +x test_webhook.sh
    ./test_webhook.sh
    ```

## API Endpoints

### Core Endpoints

-   `GET /` - API information
-   `GET /health` - Health check with service status
-   `POST /webhook/github` - GitHub webhook receiver
-   `POST /analyze` - Manual analysis trigger

### Data Endpoints

-   `GET /runs` - List all workflow runs
-   `GET /runs/{id}` - Get specific workflow run
-   `POST /runs/{id}/approve` - Approve a suggested fix
-   `POST /runs/{id}/reject` - Reject a suggested fix

### Clarifications (Human Approval)

-   `GET /clarifications` - Get pending approvals
-   `POST /clarifications/respond` - Respond to approval requests

### Statistics

-   `GET /stats` - Get performance statistics

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Google Gemini API
GOOGLE_API_KEY=your_google_gemini_api_key

# Portia Configuration (optional)
PORTIA_API_KEY=your_portia_api_key

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
FRONTEND_URL=http://localhost:3000
```

### GitHub Setup

1. **Personal Access Token**: Create a token with `repo` and `actions:read` permissions
2. **Webhook**: Configure repository webhook pointing to `/webhook/github`
3. **Events**: Subscribe to `workflow_run` events

## Architecture

### Database Schema

**workflow_runs**: Stores CI/CD run information

-   `id`, `repo_name`, `owner`, `run_id`
-   `status`, `conclusion`, `error_log`
-   `suggested_fix`, `fix_status`

**portia_plans**: Tracks agent execution

-   `plan_id`, `workflow_run_id`, `status`
-   `steps_completed`, `error_message`

**clarifications**: Human approval requests

-   `plan_id`, `question`, `response`
-   `status`, `response_type`

### Agent Workflow

1. **Detection**: GitHub webhook triggers on workflow failure
2. **Data Collection**: Fetch workflow details and error logs
3. **Analysis**: Gemini AI analyzes logs and suggests fixes
4. **Approval**: Human approval via clarification system
5. **Action**: Create GitHub issue or PR with fix (if approved)
6. **Audit**: Log all steps and decisions

## Development

### File Structure

```
backend/
├── main.py              # FastAPI application
├── postgres_database.py # PostgreSQL database operations (Supabase)
├── github_service.py    # GitHub API integration
├── gemini_agent.py      # Gemini AI analysis
├── portia_agent.py      # Portia workflow orchestration
├── requirements.txt     # Python dependencies
├── .env.example        # Environment template
├── setup.sh            # Setup script
├── run.sh              # Development server
└── test_webhook.sh     # Testing script
```

### Adding New Error Types

To extend the AI analysis:

1. Add patterns to `gemini_agent.py` in the fallback analysis methods
2. Update the Gemini prompt to include new error categories
3. Test with sample error logs

### Testing

-   **Unit Tests**: Add tests for individual components
-   **Integration Tests**: Test complete webhook-to-fix flow
-   **Load Tests**: Verify performance with multiple concurrent requests

## Deployment

### Production Considerations

1. **Database**: ✅ Already using PostgreSQL (Supabase) for production scalability
2. **Security**: Use proper webhook secrets and HTTPS
3. **Monitoring**: Add logging, metrics, and error tracking
4. **Scaling**: Consider async processing for heavy workloads

### Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Common Issues

1. **"Import X could not be resolved"**: Install dependencies with `./setup.sh`
2. **"Database not found"**: Run database initialization in setup script
3. **"GitHub API errors"**: Check your `GITHUB_TOKEN` permissions
4. **"Gemini API errors"**: Verify your `GOOGLE_API_KEY` is valid

### Logs

Check server logs for detailed error information:

```bash
# The server logs will show:
# - Webhook processing
# - AI analysis results
# - Database operations
# - Error details
```

## Contributing

1. Follow Python PEP 8 style guidelines
2. Add type hints for all functions
3. Include docstrings for public methods
4. Test your changes with the test scripts
5. Update this README for new features

## License

MIT License - see LICENSE file for details.
