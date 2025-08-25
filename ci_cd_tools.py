"""
Portia CI/CD Tools for GitHub Actions workflow analysis and fixing.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

from portia import Tool, ToolRegistry, ToolRunContext
from github_service import GitHubService
from gemini_agent import GeminiFixerAgent
from postgres_database import PostgreSQLCICDFixerDB

logger = logging.getLogger(__name__)

github_service = GitHubService()
gemini_agent = GeminiFixerAgent()
db = PostgreSQLCICDFixerDB()

class WorkflowRunInput(BaseModel):
    owner: str = Field(description="Repository owner") 
    repo: str = Field(description="Repository name")
    run_id: int = Field(description="GitHub Actions workflow run ID")

class ErrorAnalysisInput(BaseModel):
    logs: str = Field(description="Workflow logs to analyze")
    repo: str = Field(description="Repository name for context")

class FixGenerationInput(BaseModel):
    analysis: str = Field(description="Error analysis results")
    repo: str = Field(description="Repository name")

class FixApplicationInput(BaseModel):
    fix_details: str = Field(description="Fix implementation details")
    owner: str = Field(description="Repository owner")
    repo: str = Field(description="Repository name")

class ApprovalCheckInput(BaseModel):
    workflow_run_id: int = Field(description="Database workflow run ID")

class AnalysisStorageInput(BaseModel):
    analysis_result: Dict[str, Any] = Field(description="Analysis results to store")
    failure_id: str = Field(description="Workflow failure ID")


class FetchWorkflowRunTool(Tool):
    id: str = "fetch_workflow_run"
    name: str = "fetch_workflow_run" 
    description: str = "Fetches detailed information about a GitHub Actions workflow run"
    args_schema: type[BaseModel] = WorkflowRunInput
    output_schema: tuple[str, str] = ("dict", "Workflow run data with success status")

    def run(self, context: ToolRunContext, owner: str, repo: str, run_id: int) -> Dict[str, Any]:
        """Fetch workflow run details from GitHub API."""
        try:
            run_data = github_service.get_workflow_run(owner, repo, run_id)
            
            if run_data:
                logger.info(f"Successfully fetched workflow run {run_id} for {owner}/{repo}")
                return {
                    "success": True,
                    "data": run_data,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Workflow run {run_id} not found"
                }
                
        except Exception as e:
            logger.error(f"Error fetching workflow run {run_id}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

class FetchWorkflowLogsTool(Tool):
    id: str = "fetch_workflow_logs"
    name: str = "fetch_workflow_logs"
    description: str = "Retrieves detailed logs from a GitHub Actions workflow run for analysis"
    args_schema: type[BaseModel] = WorkflowRunInput
    output_schema: tuple[str, str] = ("str", "Complete workflow logs for error analysis")

    def run(self, context: ToolRunContext, owner: str, repo: str, run_id: int) -> str:
        """Fetch workflow logs from GitHub API."""
        try:
            logs = github_service.get_workflow_run_logs(owner, repo, run_id)
            
            jobs = github_service.get_workflow_run_jobs(owner, repo, run_id)
            
            complete_logs = f"=== Workflow Run {run_id} Logs ===\n"
            complete_logs += f"Repository: {owner}/{repo}\n\n"
            
            if jobs:
                complete_logs += "=== Job Details ===\n"
                for job in jobs.get('jobs', []):
                    complete_logs += f"Job: {job.get('name', 'Unknown')}\n"
                    complete_logs += f"Status: {job.get('status', 'Unknown')}\n"
                    complete_logs += f"Conclusion: {job.get('conclusion', 'Unknown')}\n\n"
            
            if logs:
                complete_logs += "=== Raw Logs ===\n"
                complete_logs += logs
            else:
                complete_logs += "No logs available or logs could not be retrieved.\n"
            
            logger.info(f"Successfully fetched logs for workflow run {run_id}")
            return complete_logs
            
        except Exception as e:
            logger.error(f"Error fetching workflow logs {run_id}: {e}")
            return f"Error fetching logs: {str(e)}"

class AnalyzeErrorsTool(Tool):
    id: str = "analyze_errors"
    name: str = "analyze_errors"
    description: str = "Analyzes CI/CD workflow errors and identifies root causes using AI"
    args_schema: type[BaseModel] = ErrorAnalysisInput
    output_schema: tuple[str, str] = ("str", "Detailed error analysis with root causes and recommendations")

    def run(self, context: ToolRunContext, logs: str, repo: str) -> str:
        """Analyze workflow errors using Gemini AI."""
        try:
            logger.info(f"Starting error analysis for repository {repo}")
            
            prompt = f"""
            Analyze the following CI/CD workflow failure logs and provide:
            1. Root cause analysis
            2. Specific error identification
            3. Recommended fixes
            4. Prevention strategies

            Repository: {repo}
            
            Logs:
            {logs}
            """
            
            analysis = gemini_agent.analyze_ci_failure(prompt)
            
            if analysis:
                logger.info("Error analysis completed successfully")
                return analysis
            else:
                return "Error: Analysis could not be completed"
                
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            return f"Error during analysis: {str(e)}"

class GenerateFixTool(Tool):
    id: str = "generate_fix"
    name: str = "generate_fix"
    description: str = "Generates automated fixes for identified CI/CD issues"
    args_schema: type[BaseModel] = FixGenerationInput
    output_schema: tuple[str, str] = ("str", "Generated fix implementation details")

    def run(self, context: ToolRunContext, analysis: str, repo: str) -> str:
        """Generate fix suggestions based on error analysis."""
        try:
            logger.info(f"Generating fix for repository {repo}")
            
            prompt = f"""
            Based on the following error analysis, generate specific, actionable fixes:
            
            Repository: {repo}
            Analysis: {analysis}
            
            Provide:
            1. Step-by-step fix instructions
            2. Code changes (if applicable)
            3. Configuration updates
            4. Testing recommendations
            """
            
            fix = gemini_agent.generate_fix(prompt)
            
            if fix:
                logger.info("Fix generation completed successfully")
                return fix
            else:
                return "Error: Fix could not be generated"
                
        except Exception as e:
            logger.error(f"Error generating fix: {e}")
            return f"Error generating fix: {str(e)}"

class ApplyFixTool(Tool):
    id: str = "apply_fix"
    name: str = "apply_fix"
    description: str = "Applies automated fixes to the repository (simulation only)"
    args_schema: type[BaseModel] = FixApplicationInput
    output_schema: tuple[str, str] = ("str", "Fix application results and status")

    def run(self, context: ToolRunContext, fix_details: str, owner: str, repo: str) -> str:
        """Apply fixes to the repository (simulation)."""
        try:
            logger.info(f"Simulating fix application for {owner}/{repo}")
            
            result = f"""
            Fix Application Simulation for {owner}/{repo}
            
            Proposed Changes:
            {fix_details}
            
            Status: ✅ Ready for review
            
            Next Steps:
            1. Create pull request with proposed changes
            2. Run automated tests
            3. Request human review and approval
            4. Merge after approval
            
            Note: This is a simulation. Actual implementation would require human approval.
            """
            
            logger.info("Fix application simulation completed")
            return result
            
        except Exception as e:
            logger.error(f"Error applying fix: {e}")
            return f"Error applying fix: {str(e)}"

class CheckApprovalTool(Tool):
    id: str = "check_approval"
    name: str = "check_approval"
    description: str = "Checks if a proposed fix has been approved by humans"
    args_schema: type[BaseModel] = ApprovalCheckInput
    output_schema: tuple[str, str] = ("str", "Approval status and message")

    def run(self, context: ToolRunContext, workflow_run_id: int) -> str:
        """Check approval status for a fix."""
        try:
            logger.info(f"Checking approval status for workflow run {workflow_run_id}")
            
          
            
            return f"Approval check for workflow run {workflow_run_id}: Pending human review"
            
        except Exception as e:
            logger.error(f"Error checking approval: {e}")
            return f"Error checking approval: {str(e)}"

class StoreAnalysisTool(Tool):
    id: str = "store_analysis"
    name: str = "store_analysis"
    description: str = "Stores analysis results in the database for tracking"
    args_schema: type[BaseModel] = AnalysisStorageInput
    output_schema: tuple[str, str] = ("str", "Storage confirmation with ID")

    def run(self, context: ToolRunContext, analysis_result: Dict[str, Any], failure_id: str) -> str:
        """Store analysis results in database."""
        try:
            logger.info(f"Storing analysis results for failure {failure_id}")
            
           
            db.store_analysis(failure_id, analysis_result)
            
            return f"Analysis stored successfully for failure ID: {failure_id}"
            
        except Exception as e:
            logger.error(f"Error storing analysis: {e}")
            return f"Error storing analysis: {str(e)}"

def create_ci_cd_tool_registry() -> List[Tool]:
    """Create and return the CI/CD tool registry."""
    tools = [
        FetchWorkflowRunTool(),
        FetchWorkflowLogsTool(),
        AnalyzeErrorsTool(),
        GenerateFixTool(),
        ApplyFixTool(),
        CheckApprovalTool(),
        StoreAnalysisTool(),
    ]
    
    logger.info(f"Created CI/CD tool registry with {len(tools)} tools")
    return tools


ci_cd_tool_registry = create_ci_cd_tool_registry()
