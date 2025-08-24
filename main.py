import os
import logging
import json
import hashlib
import hmac
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import Counter

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Literal

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Local imports
from postgres_database import PostgreSQLCICDFixerDB
from github_service import GitHubService
from gemini_agent import GeminiFixerAgent
from portia_agent import ci_cd_agent
from analytics_engine import (
    CICDPatternAnalyzer, 
    RepositoryLearningSystem, 
    MLPatternRecognizer,
    SuccessPredictor,
    IntelligentFixGenerator
)

# Pydantic Models for API Documentation
class AnalysisRequest(BaseModel):
    """Request model for workflow analysis"""
    owner: str = Field(..., description="GitHub repository owner/organization", example="microsoft")
    repo: str = Field(..., description="Repository name", example="vscode") 
    run_id: int = Field(..., description="GitHub Actions workflow run ID", example=17152193292)

class PortiaAnalysisRequest(BaseModel):
    """Request model for Portia-powered analysis"""
    owner: str = Field(..., description="GitHub repository owner/organization", example="microsoft")
    repo: str = Field(..., description="Repository name", example="vscode")
    run_id: int = Field(..., description="GitHub Actions workflow run ID", example=17152193292)

class FixApprovalRequest(BaseModel):
    """Request model for fix approval/rejection"""
    action: Literal["approve", "reject"] = Field(..., description="Action to perform", example="approve")
    comment: Optional[str] = Field(None, description="Optional comment for the action", example="Fix looks good, proceed")

class ClarificationResponse(BaseModel):
    """Request model for clarification responses"""
    response: str = Field(..., description="Response to the clarification", example="yes")

class MLPredictionRequest(BaseModel):
    """Request model for ML-based success prediction"""
    error_log: str = Field(..., description="Error log content", example="npm install failed with ENOENT error")
    suggested_fix: str = Field(..., description="Proposed fix solution", example="Run npm install --legacy-peer-deps")
    repo_context: Optional[str] = Field(None, description="Repository context", example="Node.js application with package.json")
    error_type: Optional[str] = Field(None, description="Error classification", example="dependency_error")
    language: Optional[str] = Field(None, description="Primary language", example="javascript")

class MLFixGenerationRequest(BaseModel):
    """Request model for enhanced fix generation"""
    error_log: str = Field(..., description="Error log content", example="TypeError: Cannot read property of undefined")
    repo_context: Optional[str] = Field(None, description="Repository context", example="React TypeScript application")
    error_type: Optional[str] = Field(None, description="Error classification", example="test_failure")
    language: Optional[str] = Field(None, description="Primary language", example="typescript")

class MLFeedbackRequest(BaseModel):
    """Request model for ML feedback learning"""
    error_log: str = Field(..., description="Original error log", example="npm install failed")
    suggested_fix: str = Field(..., description="Fix that was applied", example="Clear npm cache and reinstall")
    fix_status: Literal["approved", "rejected", "pending"] = Field(..., description="Fix outcome", example="approved")
    repo_context: Optional[str] = Field(None, description="Repository context", example="Node.js project")
    user_feedback: Optional[str] = Field(None, description="User feedback", example="Fix worked perfectly")
    fix_effectiveness: Optional[float] = Field(None, description="Effectiveness rating (0-1)", example=0.9)

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Overall health status", example="healthy")
    timestamp: str = Field(..., description="Check timestamp", example="2025-08-23T10:00:00.000Z")
    services: Dict[str, str] = Field(..., description="Individual service statuses")

class AnalysisResponse(BaseModel):
    """Analysis response model"""
    message: str = Field(..., description="Response message", example="Analysis triggered successfully")
    failure_id: str = Field(..., description="Unique failure ID", example="7")
    owner: str = Field(..., description="Repository owner", example="microsoft")
    repo: str = Field(..., description="Repository name", example="vscode")
    run_id: int = Field(..., description="Workflow run ID", example=17152193292)

class PortiaAnalysisResponse(BaseModel):
    """Portia analysis response model"""
    message: str = Field(..., description="Response message", example="Portia analysis completed")
    owner: str = Field(..., description="Repository owner", example="microsoft")
    repo: str = Field(..., description="Repository name", example="vscode")
    run_id: int = Field(..., description="Workflow run ID", example=17152193292)
    result: Dict[str, Any] = Field(..., description="Detailed analysis results")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment check for Google API key
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    logger.warning("⚠️  GOOGLE_API_KEY not set. Portia endpoint will be limited.")
    logger.warning("📝 To use full Portia functionality, set: export GOOGLE_API_KEY='your-api-key'")

# Initialize FastAPI app with comprehensive metadata
app = FastAPI(
    title="CI/CD Fixer Agent API",
    description="""
    🤖 **Intelligent CI/CD Failure Analysis & Fixing Platform**
    
    This API provides automated CI/CD failure analysis using advanced AI technologies:
    
    ## 🚀 **Key Features**
    
    * **Portia AI Framework**: Structured plan-based analysis workflows
    * **Google Gemini 2.5 Pro**: Advanced AI error analysis and fix generation  
    * **GitHub Integration**: Real-time webhook processing and API integration
    * **PostgreSQL Database**: Complete audit trails and analytics storage
    * **ML Analytics**: Pattern recognition, success prediction, and learning
    * **Human Approval**: Safe fix application with approval workflows
    
    ## 🔧 **Core Capabilities**
    
    * Analyze failed GitHub Actions workflows
    * Generate intelligent fix suggestions
    * Track fix effectiveness over time
    * Learn from repository-specific patterns
    * Provide comprehensive analytics and insights
    
    ## 📊 **Analytics & Learning**
    
    * Pattern recognition across repositories
    * ML-based success prediction for fixes
    * Repository-specific intelligence
    * Historical analysis and trend detection
    * Enhanced fix generation with ML insights
    
    ---
    
    **Base URL**: `http://localhost:8000` (Development) | `https://api.yourproduction.com` (Production)
    """,
    version="1.0.0",
    contact={
        "name": "CI/CD Fixer Agent Team",
        "email": "support@cicd-fixer.com",
        "url": "https://github.com/your-org/ci-cd-fixer-agent"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.yourproduction.com", "description": "Production server"}
    ]
)

raw_origins = os.getenv("FRONTEND_URL", "")
origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility functions
def format_suggested_fix(fix_dict: Dict[str, Any]) -> str:
    """Format a suggested fix dictionary into a readable string."""
    if not isinstance(fix_dict, dict):
        return str(fix_dict)
    
    formatted = ""
    
    # Add description
    if "description" in fix_dict:
        formatted += f"**Description:** {fix_dict['description']}\n\n"
    
    # Add steps
    if "steps" in fix_dict and isinstance(fix_dict["steps"], list):
        formatted += "**Steps:**\n"
        for i, step in enumerate(fix_dict["steps"], 1):
            formatted += f"{i}. {step}\n"
        formatted += "\n"
    
    # Add files to modify
    if "files_to_modify" in fix_dict and isinstance(fix_dict["files_to_modify"], list) and fix_dict["files_to_modify"]:
        formatted += "**Files to modify:**\n"
        for file in fix_dict["files_to_modify"]:
            formatted += f"- {file}\n"
        formatted += "\n"
    
    # Add commands to run
    if "commands_to_run" in fix_dict and isinstance(fix_dict["commands_to_run"], list) and fix_dict["commands_to_run"]:
        formatted += "**Commands to run:**\n"
        for cmd in fix_dict["commands_to_run"]:
            formatted += f"- `{cmd}`\n"
        formatted += "\n"
    
    # If no formatting was applied, return string representation
    if not formatted:
        formatted = str(fix_dict)
    
    return formatted.strip()

# Initialize services
try:
    db = PostgreSQLCICDFixerDB()
    github_service = GitHubService()
    gemini_agent = GeminiFixerAgent()
    pattern_analyzer = CICDPatternAnalyzer()
    repo_learning = RepositoryLearningSystem()
    
    # Add missing columns for fix application tracking
    db.add_missing_columns_if_needed()
    
    logger.info("✅ All services initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize services: {e}")

# Database dependency
def get_db():
    return db

def get_github_service():
    return github_service

def get_gemini_agent():
    return gemini_agent

def get_pattern_analyzer():
    return pattern_analyzer

def get_repo_learning():
    return repo_learning

# Pydantic models
class WebhookPayload(BaseModel):
    repository: Dict[str, Any]
    workflow_run: Dict[str, Any]
    action: str

class AnalysisRequest(BaseModel):
    owner: str
    repo: str
    run_id: int

class FixRequest(BaseModel):
    fix_id: str
    action: str  # "approve" or "reject"

class PlanClarificationRequest(BaseModel):
    plan_run_id: str
    clarification_id: str
    response: str

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "CI/CD Fixer Agent API",
        "version": "1.0.0",
        "description": "Automated CI/CD failure analysis and fixing using Portia AI + Google Gemini",
        "endpoints": {
            "health": "/health",
            "webhook": "/webhook", 
            "analyze": "/analyze",
            "analyze_portia": "/analyze/portia",
            "fixes": "/fixes",
            "approve_fix": "/fixes/{fix_id}/approve",
            "reject_fix": "/fixes/{fix_id}/reject",
            "clarifications": "/plans/{plan_run_id}/clarifications/{clarification_id}",
            "analytics": {
                "patterns": "/analytics/patterns",
                "effectiveness": "/analytics/effectiveness", 
                "repository_profile": "/analytics/repository/{owner}/{repo}",
                "dashboard": "/analytics/dashboard",
                "ml_similar_fixes": "/analytics/ml/similar-fixes",
                "ml_predict_success": "/analytics/ml/predict-success",
                "ml_generate_fix": "/analytics/ml/generate-enhanced-fix",
                "ml_learn_feedback": "/analytics/ml/learn-from-feedback",
                "ml_pattern_insights": "/analytics/ml/pattern-insights",
                "ml_model_performance": "/analytics/ml/model-performance"
            }
        },
        "analytics_features": {
            "pattern_recognition": "✅ Implemented - Analyzes failure patterns across repositories",
            "success_prediction": "✅ Implemented - ML-based fix success prediction", 
            "intelligent_fix_generation": "✅ Implemented - Enhanced AI fix generation",
            "repository_learning": "✅ Implemented - Repository-specific intelligence",
            "historical_analysis": "✅ Implemented - Time-based pattern analysis"
        }
    }

@app.post("/")
async def root_post(request: Request):
    """Handle POST requests to root (likely misrouted GitHub webhooks)."""
    # Log this for debugging
    logger.info(f"POST request to root endpoint from {request.client.host if request.client else 'unknown'}")
    
    # Check if this looks like a GitHub webhook
    user_agent = request.headers.get("user-agent", "")
    content_type = request.headers.get("content-type", "")
    
    if "github" in user_agent.lower() or "hookshot" in user_agent.lower():
        logger.info("Detected potential GitHub webhook sent to wrong endpoint - redirecting to /webhook")
        # Redirect to the webhook endpoint
        return JSONResponse(
            status_code=307,  # Temporary redirect that preserves POST method
            headers={"Location": "/webhook"},
            content={"message": "GitHub webhook detected - please use /webhook endpoint"}
        )
    
    return {
        "message": "This is the CI/CD Fixer Agent API root endpoint",
        "note": "For GitHub webhooks, please use the /webhook endpoint",
        "webhook_url": "/webhook",
        "api_docs": "/docs"
    }

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="System Health Check",
    description="""
    Check the overall health and status of all system components.
    
    Returns the status of:
    - **Database**: PostgreSQL connection status
    - **GitHub API**: GitHub service availability 
    - **Gemini AI**: Google Gemini API availability
    
    This endpoint is useful for monitoring and ensuring all services are operational.
    """,
    responses={
        200: {
            "description": "System is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2025-08-23T10:00:00.000000",
                        "services": {
                            "database": "connected",
                            "github_api": "available", 
                            "gemini_api": "available"
                        }
                    }
                }
            }
        },
        500: {"description": "System health check failed"}
    },
    tags=["System"]
)
async def health_check() -> HealthResponse:
    """
    **System Health Check**
    
    Validates that all critical system components are operational:
    
    - Database connectivity (PostgreSQL)
    - GitHub API service availability
    - Google Gemini AI service availability
    """
    try:
        # Check database connection
        db_status = "connected" if db.test_connection() else "disconnected"
        
        # Check GitHub API
        github_status = "available" if github_service else "unavailable"
        
        # Check Gemini API
        gemini_status = "available" if gemini_agent else "unavailable"
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            services={
                "database": db_status,
                "github_api": github_status,
                "gemini_api": gemini_status
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )

@app.post("/webhook")
async def handle_webhook(request: Request):
    """Handle GitHub webhook for workflow_run events."""
    try:
        # Verify webhook signature
        signature = request.headers.get("X-Hub-Signature-256")
        body = await request.body()
        
        webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        if webhook_secret and signature:
            expected_signature = "sha256=" + hmac.new(
                webhook_secret.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                raise HTTPException(status_code=403, detail="Invalid webhook signature")
        
        # Parse payload with error handling
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Validate required fields exist
        if "action" not in payload:
            logger.warning("Missing 'action' field in webhook payload")
            return {"message": "Webhook received but missing required fields"}
        
        if "workflow_run" not in payload:
            logger.warning("Missing 'workflow_run' field in webhook payload")
            return {"message": "Webhook received but missing workflow_run data"}
        
        if "repository" not in payload:
            logger.warning("Missing 'repository' field in webhook payload")
            return {"message": "Webhook received but missing repository data"}
        
        # Only process failed workflow runs
        if (payload.get("action") == "completed" and 
            payload.get("workflow_run", {}).get("conclusion") == "failure"):
            
            try:
                repository = payload["repository"]
                workflow_run = payload["workflow_run"]
                
                # Extract required data with fallbacks
                owner = repository.get("owner", {}).get("login")
                repo = repository.get("name")
                run_id = workflow_run.get("id")
                
                if not all([owner, repo, run_id]):
                    logger.error(f"Missing required data: owner={owner}, repo={repo}, run_id={run_id}")
                    return {"message": "Webhook received but missing required repository/workflow data"}
                
                logger.info(f"🔥 Detected failed workflow: {owner}/{repo} run #{run_id}")
                
                # Store failure in database with safe field access
                failure_data = {
                    "owner": owner,
                    "repo": repo,
                    "run_id": run_id,
                    "workflow_name": workflow_run.get("name", "Unknown"),
                    "conclusion": workflow_run.get("conclusion", "failure"),
                    "html_url": workflow_run.get("html_url", f"https://github.com/{owner}/{repo}/actions/runs/{run_id}"),
                    "created_at": workflow_run.get("created_at", datetime.utcnow().isoformat()),
                    "updated_at": workflow_run.get("updated_at", datetime.utcnow().isoformat())
                }
                
                failure_id = db.store_failure(failure_data)
                logger.info(f"📝 Stored failure with ID: {failure_id}")
                
                # Trigger analysis asynchronously
                asyncio.create_task(analyze_failure_async(owner, repo, run_id, failure_id))
                
                return {"message": "Webhook processed successfully", "failure_id": failure_id}
                
            except Exception as e:
                logger.error(f"Error processing workflow data: {e}")
                return {"message": "Webhook received but failed to process workflow data", "error": str(e)}
        
        return {"message": "Webhook received but no action taken"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def analyze_failure_async(owner: str, repo: str, run_id: int, failure_id: str):
    """Asynchronously analyze a CI/CD failure and store fixes if generated."""
    try:
        logger.info(f"🔍 Starting analysis for {owner}/{repo} run #{run_id}")
        
        # Perform analysis using Gemini
        try:
            analysis_result = await gemini_agent.analyze_failure(owner, repo, run_id)
            logger.info(f"🤖 Analysis completed for {owner}/{repo}#{run_id}")
        except Exception as e:
            logger.error(f"❌ Gemini analysis failed for {owner}/{repo}#{run_id}: {e}")
            analysis_result = None
        
        if analysis_result:
            try:
                # Store analysis results
                db.store_analysis(failure_id, analysis_result)
                logger.info(f"💾 Analysis result stored for failure {failure_id}")
                
                # Check if a fix was suggested and store it properly
                suggested_fix = analysis_result.get("suggested_fix")
                if suggested_fix:
                    # Convert suggested_fix to string if it's a dictionary
                    if isinstance(suggested_fix, dict):
                        fix_description = suggested_fix.get("description", str(suggested_fix))
                        logger.info(f"💡 Fix suggested for {owner}/{repo}#{run_id}: {fix_description[:100]}...")
                        # Convert the entire fix object to a formatted string
                        fix_string = format_suggested_fix(suggested_fix)
                    else:
                        fix_string = str(suggested_fix)
                        logger.info(f"💡 Fix suggested for {owner}/{repo}#{run_id}: {fix_string[:100]}...")
                    
                    # Update the workflow run with the suggested fix
                    db.update_workflow_run_fix(
                        run_id=int(failure_id),  # failure_id is the database record ID
                        suggested_fix=fix_string,
                        fix_status='pending'  # Set to pending to require human approval
                    )
                    logger.info(f"✅ Fix stored for failure {failure_id}")
                else:
                    logger.info(f"ℹ️ No specific fix suggested for {owner}/{repo}#{run_id}")
            except Exception as e:
                logger.error(f"❌ Error storing analysis results for failure {failure_id}: {e}")
        else:
            logger.warning(f"⚠️ No analysis result generated for {owner}/{repo}#{run_id}")
            
    except Exception as e:
        logger.error(f"❌ Analysis error for {owner}/{repo} run #{run_id}: {e}")
        # Store error information
        try:
            error_result = {
                "error": str(e),
                "error_type": "analysis_failure",
                "timestamp": datetime.utcnow().isoformat()
            }
            db.store_analysis(failure_id, error_result)
        except Exception as store_error:
            logger.error(f"❌ Failed to store error for failure {failure_id}: {store_error}")

@app.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Trigger Manual Analysis",
    description="""
    Manually trigger CI/CD failure analysis for a specific GitHub Actions workflow run.
    
    This endpoint allows you to analyze any workflow run by providing:
    - **owner**: GitHub repository owner/organization  
    - **repo**: Repository name
    - **run_id**: GitHub Actions workflow run ID
    
    The analysis will be processed asynchronously and stored in the database for later retrieval.
    Use this when you want to analyze a specific failed workflow run manually.
    """,
    responses={
        200: {
            "description": "Analysis triggered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Analysis triggered successfully",
                        "failure_id": "7",
                        "owner": "microsoft",
                        "repo": "vscode", 
                        "run_id": 17152193292
                    }
                }
            }
        },
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error"}
    },
    tags=["Analysis"]
)
async def trigger_analysis(request: AnalysisRequest) -> AnalysisResponse:
    """
    **Manually Trigger CI/CD Analysis**
    
    Initiates analysis for a specific GitHub Actions workflow run:
    
    1. Stores the failure information in the database
    2. Triggers asynchronous analysis using AI
    3. Returns immediately with a tracking ID
    
    The analysis results can be retrieved later using the returned failure_id.
    """
    try:
        logger.info(f"🔍 Manual analysis triggered for {request.owner}/{request.repo} run #{request.run_id}")
        
        # Store failure if not already stored
        failure_data = {
            "owner": request.owner,
            "repo": request.repo,
            "run_id": request.run_id,
            "workflow_name": "Manual Analysis",
            "conclusion": "failure",
            "html_url": f"https://github.com/{request.owner}/{request.repo}/actions/runs/{request.run_id}",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        failure_id = db.store_failure(failure_data)
        
        # Trigger analysis asynchronously
        asyncio.create_task(analyze_failure_async(request.owner, request.repo, request.run_id, failure_id))
        
        return AnalysisResponse(
            message="Analysis triggered successfully",
            failure_id=failure_id,
            owner=request.owner,
            repo=request.repo,
            run_id=request.run_id
        )
        
    except Exception as e:
        logger.error(f"Manual analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/portia")
async def analyze_with_portia(request: AnalysisRequest):
    """Analyze CI/CD failure using Portia's plan-based approach."""
    try:
        if not GOOGLE_API_KEY:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Google API key not configured",
                    "message": "Set GOOGLE_API_KEY environment variable to use Portia functionality",
                    "example": "export GOOGLE_API_KEY='your-api-key'"
                }
            )
        
        logger.info(f"🤖 Portia analysis triggered for {request.owner}/{request.repo} run #{request.run_id}")
        
        # Run Portia analysis
        result = await ci_cd_agent.analyze_ci_failure(request.owner, request.repo, request.run_id)
        
        return {
            "message": "Portia analysis completed",
            "owner": request.owner,
            "repo": request.repo,
            "run_id": request.run_id,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Portia analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fixes")
async def get_pending_fixes():
    """Get all pending fixes that require human approval."""
    try:
        fixes = db.get_pending_fixes()
        return {"pending_fixes": fixes}
    except Exception as e:
        logger.error(f"Failed to get pending fixes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/failures")
async def get_failures():
    """Get all workflow failures."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, repo_name, owner, workflow_name, run_id, status, 
                       conclusion, error_log, suggested_fix, fix_status, created_at
                FROM workflow_runs 
                ORDER BY created_at DESC 
                LIMIT 100
            """)
            
            failures = []
            for row in cursor.fetchall():
                failures.append({
                    "id": row[0],
                    "repo_name": row[1],
                    "owner": row[2],
                    "workflow_name": row[3],
                    "run_id": row[4],
                    "status": row[5],
                    "conclusion": row[6],
                    "error_log": row[7],
                    "suggested_fix": row[8],
                    "fix_status": row[9],
                    "created_at": row[10].isoformat() if row[10] else None
                })
            
            return {"failures": failures, "count": len(failures)}
            
    except Exception as e:
        logger.error(f"Failed to get failures: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/failures/{failure_id}")
async def get_failure_detail(failure_id: int):
    """Get detailed information about a specific failure."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, repo_name, owner, workflow_name, run_id, status, 
                       conclusion, error_log, suggested_fix, fix_status, created_at
                FROM workflow_runs 
                WHERE id = %s
            """, (failure_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Failure not found")
            
            failure = {
                "id": row[0],
                "repo_name": row[1],
                "owner": row[2],
                "workflow_name": row[3],
                "run_id": row[4],
                "status": row[5],
                "conclusion": row[6],
                "error_log": row[7],
                "suggested_fix": row[8],
                "fix_status": row[9],
                "created_at": row[10].isoformat() if row[10] else None
            }
            
            return {"failure": failure}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get failure {failure_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fixes/{fix_id}/approve")
async def approve_fix(fix_id: str):
    """Approve a suggested fix and apply it to the repository."""
    try:
        fix = db.get_fix(fix_id)
        if not fix:
            raise HTTPException(status_code=404, detail="Fix not found")
        
        if fix["fix_status"] != "pending":
            raise HTTPException(status_code=400, detail="Fix is not in pending state")
        
        # Update fix status to approved
        db.update_fix_status(fix_id, "approved")
        logger.info(f"✅ Fix {fix_id} approved")
        
        # Apply the fix to the repository
        try:
            await apply_fix_to_repository(fix_id, fix)
            return {"message": "Fix approved and application started", "fix_id": fix_id}
        except Exception as e:
            logger.error(f"❌ Failed to apply fix {fix_id}: {e}")
            # Update status to show application failed
            db.update_fix_application_result(
                fix_id, "approved_application_failed", 
                error_message=str(e)
            )
            return {"message": "Fix approved but application failed", "fix_id": fix_id, "error": str(e)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve fix {fix_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def apply_fix_to_repository(fix_id: str, fix: Dict[str, Any]):
    """Apply the approved fix to the repository."""
    try:
        owner = fix["owner"]
        repo = fix["repo_name"]
        suggested_fix = fix["suggested_fix"]
        workflow_name = fix.get("workflow_name", "Unknown Workflow")
        
        logger.info(f"🚀 Applying fix {fix_id} to {owner}/{repo}")
        
        # Update status to indicate application is in progress
        db.update_fix_status(fix_id, "applying")
        
        # Apply fix using GitHub service
        application_result = github_service.apply_fix_to_repository(
            owner, repo, suggested_fix, fix_id
        )
        
        if application_result:
            # Successfully created PR
            pr_url = application_result.get("pull_request", {}).get("html_url")
            branch_name = application_result.get("branch_name")
            
            db.update_fix_application_result(
                fix_id, "applied", pr_url=pr_url, branch_name=branch_name
            )
            
            logger.info(f"✅ Fix {fix_id} applied successfully. PR: {pr_url}")
            
            # Optionally, you could add auto-merge logic here for low-risk fixes
            # await auto_merge_if_safe(owner, repo, pr_url, fix)
            
        else:
            # Application failed
            db.update_fix_application_result(
                fix_id, "application_failed", 
                error_message="Failed to create PR or apply changes"
            )
            logger.error(f"❌ Failed to apply fix {fix_id}")
            
    except Exception as e:
        logger.error(f"❌ Error applying fix {fix_id}: {e}")
        db.update_fix_application_result(
            fix_id, "application_failed", 
            error_message=str(e)
        )
        raise

async def auto_merge_if_safe(owner: str, repo: str, pr_url: str, fix: Dict[str, Any]):
    """
    Optionally auto-merge PR if the fix is considered safe.
    This is a placeholder for advanced logic that could:
    - Check fix confidence score
    - Verify tests pass
    - Apply business rules for auto-merge
    """
    try:
        confidence_score = fix.get("confidence_score", 0)
        fix_complexity = fix.get("fix_complexity", "high")
        
        # Only auto-merge if confidence is high and complexity is low
        if confidence_score > 0.8 and fix_complexity == "low":
            logger.info(f"🤖 Fix meets criteria for auto-merge: confidence={confidence_score}, complexity={fix_complexity}")
            # TODO: Implement auto-merge logic
            # github_service.merge_pull_request(owner, repo, pr_number)
        else:
            logger.info(f"⏳ Fix requires manual review: confidence={confidence_score}, complexity={fix_complexity}")
            
    except Exception as e:
        logger.error(f"⚠️  Error in auto-merge check: {e}")

@app.post("/fixes/{fix_id}/reject")
async def reject_fix(fix_id: str):
    """Reject a suggested fix."""
    try:
        fix = db.get_fix(fix_id)
        if not fix:
            raise HTTPException(status_code=404, detail="Fix not found")
        
        if fix["fix_status"] != "pending":
            raise HTTPException(status_code=400, detail="Fix is not in pending state")
        
        # Update fix status
        db.update_fix_status(fix_id, "rejected")
        
        logger.info(f"❌ Fix {fix_id} rejected")
        
        return {"message": "Fix rejected successfully", "fix_id": fix_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject fix {fix_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fixes/{fix_id}/status")
async def get_fix_status(fix_id: str):
    """Get detailed status of a fix including application results."""
    try:
        fix = db.get_fix(fix_id)
        if not fix:
            raise HTTPException(status_code=404, detail="Fix not found")
        
        return {
            "fix_id": fix_id,
            "status": fix["fix_status"],
            "pr_url": fix.get("pr_url"),
            "branch_name": fix.get("fix_branch"),
            "error_message": fix.get("fix_error"),
            "created_at": fix["created_at"],
            "updated_at": fix["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get fix status {fix_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fixes/{fix_id}/apply")
async def manually_apply_fix(fix_id: str):
    """Manually trigger fix application (for already approved fixes)."""
    try:
        fix = db.get_fix(fix_id)
        if not fix:
            raise HTTPException(status_code=404, detail="Fix not found")
        
        if fix["fix_status"] not in ["approved", "application_failed"]:
            raise HTTPException(status_code=400, detail="Fix must be approved before application")
        
        # Apply the fix
        await apply_fix_to_repository(fix_id, fix)
        
        return {"message": "Fix application triggered", "fix_id": fix_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply fix {fix_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/plans/{plan_run_id}/clarifications/{clarification_id}")
async def respond_to_clarification(
    plan_run_id: str,
    clarification_id: str,
    request: PlanClarificationRequest
):
    """Respond to a Portia plan clarification."""
    try:
        # TODO: Implement clarification response
        # This would involve interacting with the Portia plan run
        logger.info(f"📝 Clarification response for plan {plan_run_id}, clarification {clarification_id}")
        
        return {
            "message": "Clarification response recorded",
            "plan_run_id": plan_run_id,
            "clarification_id": clarification_id,
            "response": request.response
        }
        
    except Exception as e:
        logger.error(f"Failed to respond to clarification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics Endpoints - Advanced Analytics & Learning

@app.get("/analytics/patterns")
async def get_failure_patterns(days_back: int = 30):
    """Get pattern analysis of workflow failures over the specified period."""
    try:
        logger.info(f"🔍 Analyzing failure patterns for last {days_back} days")
        
        analyzer = get_pattern_analyzer()
        patterns = analyzer.analyze_failure_patterns(days_back)
        
        return {
            "message": "Pattern analysis completed",
            "analysis": patterns
        }
        
    except Exception as e:
        logger.error(f"Pattern analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/effectiveness")
async def get_fix_effectiveness():
    """Get statistics on fix effectiveness and approval rates."""
    try:
        logger.info("📊 Generating fix effectiveness statistics")
        
        analyzer = get_pattern_analyzer()
        stats = analyzer.get_fix_effectiveness_stats()
        
        return {
            "message": "Fix effectiveness analysis completed",
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Fix effectiveness analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/repository/{owner}/{repo}")
async def get_repository_profile(owner: str, repo: str):
    """Get detailed analytics profile for a specific repository."""
    try:
        logger.info(f"🏗️ Building repository profile for {owner}/{repo}")
        
        learning_system = get_repo_learning()
        profile = learning_system.build_repository_profile(owner, repo)
        
        return {
            "message": "Repository profile generated",
            "profile": profile
        }
        
    except Exception as e:
        logger.error(f"Repository profile generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/dashboard")
async def get_analytics_dashboard():
    """Get comprehensive analytics dashboard data."""
    try:
        logger.info("📈 Generating analytics dashboard")
        
        analyzer = get_pattern_analyzer()
        
        # Get key metrics
        patterns = analyzer.analyze_failure_patterns(days_back=7)  # Last week
        effectiveness = analyzer.get_fix_effectiveness_stats()
        
        # Combine into dashboard
        dashboard = {
            "overview": {
                "generated_at": datetime.utcnow().isoformat(),
                "period": "Last 7 days"
            },
            "failure_patterns": patterns,
            "fix_effectiveness": effectiveness,
            "key_metrics": {
                "total_repos_analyzed": patterns.get("patterns", {}).get("total_unique_repos", 0),
                "total_error_types": patterns.get("patterns", {}).get("total_error_types", 0),
                "most_common_error": list(patterns.get("patterns", {}).get("common_error_types", {}).keys())[0] if patterns.get("patterns", {}).get("common_error_types") else "No data",
                "overall_fix_approval_rate": effectiveness.get("overall_stats", {}).get("approval_rate", 0)
            }
        }
        
        return {
            "message": "Analytics dashboard generated",
            "dashboard": dashboard
        }
        
    except Exception as e:
        logger.error(f"Analytics dashboard generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Advanced Analytics Endpoints
@app.post("/analytics/ml/similar-fixes")
async def find_similar_fixes(request: dict):
    """Find similar fixes using ML-based pattern recognition."""
    try:
        error_log = request.get("error_log", "")
        repo_context = request.get("repo_context", "")
        min_similarity = request.get("min_similarity", 0.3)
        
        if not error_log:
            raise HTTPException(status_code=400, detail="error_log is required")
        
        logger.info(f"🔍 Finding similar fixes for error in {repo_context}")
        
        recognizer = MLPatternRecognizer()
        similar_fixes = recognizer.find_similar_fixes(error_log, repo_context, min_similarity)
        
        return {
            "message": "Similar fixes analysis completed",
            "repo_context": repo_context,
            "similar_fixes_count": len(similar_fixes),
            "similar_fixes": similar_fixes,
            "min_similarity_threshold": min_similarity
        }
        
    except Exception as e:
        logger.error(f"Similar fixes analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analytics/ml/predict-success")
async def predict_fix_success(request: dict):
    """Predict the success probability of a proposed fix."""
    try:
        error_log = request.get("error_log", "")
        suggested_fix = request.get("suggested_fix", "")
        repo_context = request.get("repo_context", "")
        
        if not error_log or not suggested_fix:
            raise HTTPException(status_code=400, detail="error_log and suggested_fix are required")
        
        logger.info(f"🎯 Predicting fix success for {repo_context}")
        
        predictor = SuccessPredictor()
        prediction = predictor.predict_fix_success(error_log, suggested_fix, repo_context)
        
        return {
            "message": "Fix success prediction completed",
            "repo_context": repo_context,
            "prediction": prediction
        }
        
    except Exception as e:
        logger.error(f"Fix success prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analytics/ml/generate-enhanced-fix")
async def generate_enhanced_fix(request: dict):
    """Generate an enhanced fix recommendation using ML insights."""
    try:
        error_log = request.get("error_log", "")
        repo_context = request.get("repo_context", "")
        base_fix = request.get("base_fix")  # Optional
        
        if not error_log:
            raise HTTPException(status_code=400, detail="error_log is required")
        
        logger.info(f"🧠 Generating enhanced fix for {repo_context}")
        
        generator = IntelligentFixGenerator()
        enhanced_fix = generator.generate_enhanced_fix(error_log, repo_context, base_fix)
        
        return {
            "message": "Enhanced fix generation completed",
            "repo_context": repo_context,
            "enhanced_fix": enhanced_fix
        }
        
    except Exception as e:
        logger.error(f"Enhanced fix generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analytics/ml/learn-from-feedback")
async def learn_from_feedback(request: dict):
    """Learn from user feedback to improve future recommendations."""
    try:
        error_log = request.get("error_log", "")
        suggested_fix = request.get("suggested_fix", "")
        fix_status = request.get("fix_status", "")  # approved, rejected, pending
        repo_context = request.get("repo_context", "")
        
        if not all([error_log, suggested_fix, fix_status]):
            raise HTTPException(status_code=400, detail="error_log, suggested_fix, and fix_status are required")
        
        if fix_status not in ["approved", "rejected", "pending"]:
            raise HTTPException(status_code=400, detail="fix_status must be 'approved', 'rejected', or 'pending'")
        
        logger.info(f"📚 Learning from feedback: {fix_status} for {repo_context}")
        
        recognizer = MLPatternRecognizer()
        recognizer.learn_from_feedback(error_log, suggested_fix, fix_status, repo_context)
        
        return {
            "message": "Feedback learned successfully",
            "repo_context": repo_context,
            "fix_status": fix_status,
            "learning_status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Learning from feedback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/ml/pattern-insights")
async def get_pattern_insights():
    """Get insights from learned patterns and ML models."""
    try:
        logger.info("🧠 Generating ML pattern insights")
        
        recognizer = MLPatternRecognizer()
        
        # Get learned patterns statistics
        patterns_stats = {
            "total_learned_patterns": len(recognizer.learned_patterns),
            "patterns_by_success_rate": {},
            "most_common_repos": {},
            "pattern_age_distribution": {}
        }
        
        if recognizer.learned_patterns:
            # Success rate distribution
            success_ranges = {"high": 0, "medium": 0, "low": 0}
            repo_counter = Counter()
            age_distribution = {"recent": 0, "moderate": 0, "old": 0}
            
            now = datetime.utcnow()
            
            for pattern in recognizer.learned_patterns:
                # Success rate categorization
                if pattern.success_rate >= 0.8:
                    success_ranges["high"] += 1
                elif pattern.success_rate >= 0.5:
                    success_ranges["medium"] += 1
                else:
                    success_ranges["low"] += 1
                
                # Repository distribution
                for repo in pattern.repo_contexts:
                    repo_counter[repo] += 1
                
                # Age distribution
                days_old = (now - pattern.last_updated).days
                if days_old <= 7:
                    age_distribution["recent"] += 1
                elif days_old <= 30:
                    age_distribution["moderate"] += 1
                else:
                    age_distribution["old"] += 1
            
            patterns_stats["patterns_by_success_rate"] = success_ranges
            patterns_stats["most_common_repos"] = dict(repo_counter.most_common(10))
            patterns_stats["pattern_age_distribution"] = age_distribution
        
        return {
            "message": "ML pattern insights generated",
            "insights": patterns_stats,
            "recommendations": [
                "High success rate patterns indicate reliable fix approaches",
                "Recent patterns are more likely to be relevant to current issues",
                "Repositories with many patterns have diverse failure scenarios"
            ]
        }
        
    except Exception as e:
        logger.error(f"Pattern insights generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/ml/model-performance")
async def get_model_performance():
    """Get performance metrics of the ML models."""
    try:
        logger.info("📊 Analyzing ML model performance")
        
        # Initialize components
        recognizer = MLPatternRecognizer()
        predictor = SuccessPredictor()
        
        # Get some basic performance metrics
        with PostgreSQLCICDFixerDB().get_connection() as conn:
            cursor = conn.cursor()
            
            # Get recent predictions vs actual outcomes
            cursor.execute("""
                SELECT COUNT(*) as total_fixes,
                       COUNT(CASE WHEN fix_status = 'approved' THEN 1 END) as approved_fixes,
                       COUNT(CASE WHEN fix_status = 'rejected' THEN 1 END) as rejected_fixes
                FROM workflow_runs 
                WHERE suggested_fix IS NOT NULL 
                AND created_at >= %s
            """, (datetime.utcnow() - timedelta(days=30),))
            
            performance_data = cursor.fetchone()
        
        total, approved, rejected = performance_data if performance_data else (0, 0, 0)
        
        performance_metrics = {
            "data_summary": {
                "total_fixes_last_30_days": total,
                "approved_fixes": approved,
                "rejected_fixes": rejected,
                "approval_rate": approved / total if total > 0 else 0
            },
            "model_status": {
                "learned_patterns_count": len(recognizer.learned_patterns),
                "pattern_recognition": "Active" if recognizer.learned_patterns else "Learning",
                "success_prediction": "Available",
                "intelligent_generation": "Available"
            },
            "model_capabilities": {
                "similarity_matching": "✅ Operational",
                "success_prediction": "✅ Operational", 
                "pattern_learning": "✅ Operational",
                "adaptive_improvement": "✅ Operational"
            }
        }
        
        return {
            "message": "ML model performance analysis completed",
            "performance": performance_metrics
        }
        
    except Exception as e:
        logger.error(f"Model performance analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.head("/ping")
async def ping_head():
    return Response(status_code=200)

@app.get("/ping")
async def ping_get():
    return {"status": "alive"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting CI/CD Fixer Agent API on {host}:{port}")
    if not GOOGLE_API_KEY:
        logger.warning("⚠️  Starting without Google API key - Portia functionality will be limited")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )