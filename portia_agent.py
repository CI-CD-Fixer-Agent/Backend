import os
import asyncio
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

# Portia SDK imports
from portia import (
    Portia, 
    Plan, 
    Clarification, 
    PlanRunState, 
    Config,
    LLMProvider,
    StorageClass,
    MultipleChoiceClarification,
    UserVerificationClarification,
    default_config
)

# Local imports
from postgres_database import PostgreSQLCICDFixerDB
from github_service import GitHubService
from gemini_agent import GeminiFixerAgent
from ci_cd_tools import create_ci_cd_tool_registry


class CICDFixerPortiaAgent:
    """
    Portia-powered CI/CD Fixer Agent that uses structured plans and tools
    for intelligent CI/CD failure analysis and fix suggestions.
    """
    
    def __init__(self):
        self.db = PostgreSQLCICDFixerDB()
        self.github_service = GitHubService()
        self.gemini_agent = GeminiFixerAgent()
        
        # Create Portia configuration
        self.config = self._create_portia_config()
        
        # Create tool registry
        self.tool_registry = create_ci_cd_tool_registry()
        
        # Initialize Portia instance
        self.portia = Portia(
            config=self.config,
            tools=self.tool_registry
        )
    
    def _create_portia_config(self) -> Config:
        """Create Portia configuration with Google Gemini."""
        
        # Get Google API key from environment
        google_api_key = os.getenv("GOOGLE_API_KEY")
        
        if google_api_key:
            # If we have a Google API key, configure Google provider
            try:
                print("✅ Configured Portia with Google Gemini")
                config = Config(
                    llm_provider=LLMProvider.GOOGLE,
                    google_api_key=google_api_key,
                    argument_clarifications_enabled=True,
                    storage_class=StorageClass.MEMORY
                )
                return config
            except Exception as e:
                print(f"❌ Error configuring Google provider: {e}")
                print("🔄 Falling back to default configuration")
                config = default_config()
                config.argument_clarifications_enabled = True
                return config
        else:
            # Fallback to default configuration 
            print("⚠️  Warning: No GOOGLE_API_KEY found. Using default Portia configuration.")
            print("   Set GOOGLE_API_KEY environment variable for better AI analysis.")
            config = default_config()
            config.argument_clarifications_enabled = True
            return config
    
    async def analyze_ci_failure(self, owner: str, repo: str, run_id: int) -> Dict[str, Any]:
        """
        Analyze CI/CD failure using Portia's plan-based approach.
        
        This creates a structured plan that:
        1. Fetches workflow run details
        2. Extracts error logs
        3. Analyzes with AI
        4. Stores suggested fixes
        5. Awaits human approval
        
        Args:
            owner: GitHub repository owner
            repo: Repository name
            run_id: GitHub Actions workflow run ID
            
        Returns:
            Dictionary with plan execution results
        """
        
        try:
            print(f"🚀 Starting Portia-powered CI/CD analysis for {owner}/{repo} run #{run_id}")
            
            # Create a simpler, more specific analysis prompt for Portia
            analysis_prompt = f"""
            You are a CI/CD analysis expert. Please analyze the failed workflow run {run_id} for the repository {owner}/{repo}.
            
            Steps to follow:
            1. Use the fetch_workflow_run tool to get workflow run details for owner="{owner}", repo="{repo}", run_id={run_id}
            2. If the workflow run data is available, use fetch_workflow_logs tool to get the logs 
            3. If you get logs, use the analyze_errors tool to analyze what went wrong
            4. Generate a fix suggestion using the generate_fix tool
            5. Store the analysis using store_analysis tool
            
            Be thorough but practical in your analysis.
            """
            
            # Execute the plan using Portia with better error handling
            print(f"📋 Executing Portia plan for {owner}/{repo}#{run_id}")
            
            plan_run = await asyncio.to_thread(self.portia.run, analysis_prompt)
            
            print(f"📋 Plan execution completed with state: {plan_run.state}")
            print(f"📋 Plan outputs: {plan_run.outputs}")
            
            # Extract results from plan execution
            result = {
                "success": plan_run.state == PlanRunState.COMPLETE,
                "plan_id": plan_run.plan_id,
                "plan_run_id": plan_run.id,
                "state": plan_run.state.value if plan_run.state else "unknown",
                "final_output": getattr(plan_run, 'final_output', None),
                "clarifications": [],
                "message": f"Plan execution {plan_run.state.value if plan_run.state else 'completed'}",
                "next_action": "complete"
            }
            
            # Check for clarifications
            try:
                clarifications = plan_run.get_outstanding_clarifications()
                if clarifications:
                    result["clarifications"] = [c.model_dump() for c in clarifications]
                    result["next_action"] = "check_clarifications"
            except Exception as e:
                print(f"⚠️ Error getting clarifications: {e}")
            
            # Try to get outputs
            try:
                if hasattr(plan_run, 'outputs') and plan_run.outputs:
                    result["outputs"] = str(plan_run.outputs)
            except Exception as e:
                print(f"⚠️ Error getting outputs: {e}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error in Portia CI/CD analysis: {str(e)}"
            print(f"💥 {error_msg}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "error": error_msg,
                "plan_id": None,
                "plan_run_id": None
            }
    
    async def handle_clarification(self, plan_run_id: str, clarification_id: str, response: Any) -> Dict[str, Any]:
        """
        Handle human responses to clarifications (approvals, rejections, etc.)
        
        Args:
            plan_run_id: ID of the plan run
            clarification_id: ID of the clarification to respond to
            response: Human response to the clarification
            
        Returns:
            Dictionary with clarification handling result
        """
        
        try:
            print(f"🙋 Handling clarification {clarification_id} for plan run {plan_run_id}")
            
            # Resume plan execution with the human response
            plan_run = self.portia.resume_plan_run(
                plan_run_id, 
                clarification_id, 
                response
            )
            
            print(f"📋 Plan resumed with state: {plan_run.state}")
            
            return {
                "success": True,
                "plan_run_id": plan_run_id,
                "clarification_id": clarification_id,
                "plan_state": plan_run.state.value,
                "final_output": plan_run.final_output,
                "message": f"Clarification handled, plan state: {plan_run.state.value}"
            }
            
        except Exception as e:
            error_msg = f"Error handling clarification: {str(e)}"
            print(f"💥 {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "plan_run_id": plan_run_id,
                "clarification_id": clarification_id
            }
    
    async def approve_and_apply_fix(self, workflow_run_id: int) -> Dict[str, Any]:
        """
        Approve and apply a suggested fix using Portia's plan execution.
        
        This creates a plan that:
        1. Creates a GitHub issue with the approved fix
        2. Optionally creates a pull request (future enhancement)
        
        Args:
            workflow_run_id: Database ID of the workflow run
            
        Returns:
            Dictionary with fix application results
        """
        
        try:
            print(f"✅ Applying approved fix for workflow run {workflow_run_id}")
            
            # Create fix application prompt
            fix_prompt = f"""
            Apply the approved CI/CD fix for workflow run with database ID {workflow_run_id}.
            
            Please:
            1. Create a GitHub issue with the detailed fix suggestion
            2. Update the database to reflect that the fix has been applied
            
            Database ID: {workflow_run_id}
            """
            
            # Execute the fix application plan
            plan_run = self.portia.run(fix_prompt)
            
            print(f"📝 Fix application completed with state: {plan_run.state}")
            
            return {
                "success": plan_run.state == PlanRunState.COMPLETE,
                "plan_id": plan_run.plan_id,
                "plan_run_id": plan_run.id,
                "state": plan_run.state.value,
                "final_output": plan_run.final_output,
                "message": f"Fix application {plan_run.state.value}"
            }
            
        except Exception as e:
            error_msg = f"Error applying fix: {str(e)}"
            print(f"💥 {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "workflow_run_id": workflow_run_id
            }
    
    async def get_plan_run_status(self, plan_run_id: str) -> Dict[str, Any]:
        """
        Get the current status of a plan run.
        
        Args:
            plan_run_id: ID of the plan run to check
            
        Returns:
            Dictionary with plan run status information
        """
        
        try:
            plan_run = self.portia.get_plan_run(plan_run_id)
            
            return {
                "success": True,
                "plan_run_id": plan_run_id,
                "state": plan_run.state.value,
                "current_step": plan_run.current_step_index,
                "clarifications": [c.model_dump() for c in plan_run.get_outstanding_clarifications()],
                "outputs": str(plan_run.outputs) if plan_run.outputs else None,
                "final_output": getattr(plan_run, 'final_output', None),
                "message": f"Plan run status: {plan_run.state.value}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting plan run status: {str(e)}",
                "plan_run_id": plan_run_id
            }
    
    async def list_pending_clarifications(self) -> Dict[str, Any]:
        """
        List all pending clarifications that require human input.
        
        Returns:
            Dictionary with pending clarifications
        """
        
        try:
            # This would typically query Portia's storage for pending clarifications
            # For now, we'll return database-based pending approvals
            runs = self.db.get_workflow_runs(limit=50)
            pending_runs = [run for run in runs if run['fix_status'] == 'suggested']
            
            clarifications = []
            for run in pending_runs:
                clarifications.append({
                    "type": "approval_required",
                    "workflow_run_id": run['id'],
                    "repository": f"{run['owner']}/{run['repo_name']}",
                    "run_id": run['run_id'],
                    "suggested_fix": run.get('suggested_fix', ''),
                    "question": f"Apply the suggested fix for {run['owner']}/{run['repo_name']} run #{run['run_id']}?",
                    "options": ["approve", "reject", "request_revision"]
                })
            
            return {
                "success": True,
                "pending_clarifications": clarifications,
                "count": len(clarifications),
                "message": f"Found {len(clarifications)} pending clarifications"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error listing clarifications: {str(e)}"
            }


# Create a global instance for use in the FastAPI app
ci_cd_agent = CICDFixerPortiaAgent()
