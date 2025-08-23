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
        Analyze a CI/CD failure using Portia's structured approach.
        
        This method:
        1. Fetches workflow run data
        2. Analyzes error logs
        3. Generates fix suggestions
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
            
            # First, let's try a simple direct analysis approach instead of complex Portia workflow
            # This will help us identify the exact issue
            
            try:
                # Test the individual tools first
                workflow_data = self.github_service.get_workflow_run(owner, repo, run_id)
                if not workflow_data:
                    return {
                        "success": False,
                        "error": f"Could not fetch workflow run data for {owner}/{repo}#{run_id}",
                        "plan_id": None,
                        "plan_run_id": None
                    }
                
                print(f"✅ Successfully fetched workflow data for {owner}/{repo}#{run_id}")
                
                # Get workflow logs
                logs = self.github_service.get_workflow_logs(owner, repo, run_id)
                if logs:
                    print(f"✅ Successfully fetched workflow logs ({len(logs)} characters)")
                    
                    # Use Gemini for analysis
                    analysis = await self.gemini_agent.analyze_workflow_failure(workflow_data, logs)
                    if analysis:
                        print(f"✅ Gemini analysis completed successfully")
                        
                        # Store the results
                        failure_data = {
                            "owner": owner,
                            "repo": repo,
                            "run_id": run_id,
                            "workflow_name": workflow_data.get("name", "Unknown"),
                            "conclusion": "failure",
                            "html_url": workflow_data.get("html_url", ""),
                            "created_at": workflow_data.get("created_at", ""),
                            "updated_at": workflow_data.get("updated_at", "")
                        }
                        
                        failure_id = self.db.store_failure(failure_data)
                        self.db.store_analysis(failure_id, analysis)
                        
                        return {
                            "success": True,
                            "plan_id": f"direct-analysis-{failure_id}",
                            "plan_run_id": f"run-{failure_id}",
                            "state": "completed",
                            "analysis": analysis,
                            "failure_id": failure_id,
                            "message": "Direct analysis completed successfully",
                            "next_action": "review_analysis"
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Gemini analysis failed",
                            "plan_id": None,
                            "plan_run_id": None
                        }
                else:
                    return {
                        "success": False,
                        "error": "Could not fetch workflow logs",
                        "plan_id": None,
                        "plan_run_id": None
                    }
                    
            except Exception as direct_error:
                print(f"❌ Direct analysis failed: {direct_error}")
                
                # Fallback to simple Portia plan if direct analysis fails
                analysis_prompt = f"""
                Analyze the failed CI/CD workflow for repository {owner}/{repo}, run ID {run_id}.
                
                Please fetch the workflow data and logs, then provide an analysis of what went wrong.
                """
                
                print(f"📋 Falling back to simple Portia execution")
                
                try:
                    # Use synchronous execution with proper error handling
                    plan_run = self.portia.run(analysis_prompt)
                    
                    if plan_run:
                        print(f"📋 Plan execution completed with state: {getattr(plan_run, 'state', 'unknown')}")
                        
                        return {
                            "success": True,
                            "plan_id": getattr(plan_run, 'plan_id', None),
                            "plan_run_id": getattr(plan_run, 'id', None),
                            "state": getattr(plan_run, 'state', 'unknown'),
                            "message": "Portia plan executed successfully",
                            "next_action": "complete"
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Portia plan execution returned None",
                            "plan_id": None,
                            "plan_run_id": None
                        }
                        
                except Exception as portia_error:
                    print(f"❌ Portia execution failed: {portia_error}")
                    return {
                        "success": False,
                        "error": f"Portia plan execution failed: {str(portia_error)}",
                        "plan_id": None,
                        "plan_run_id": None
                    }
                    
        except Exception as e:
            print(f"❌ Error in Portia CI/CD analysis: {e}")
            return {
                "success": False,
                "error": f"Error in Portia CI/CD analysis: {e}",
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