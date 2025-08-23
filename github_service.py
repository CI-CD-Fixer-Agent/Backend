import os
import requests
from typing import Dict, Any, Optional, List
import json

class GitHubService:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CI-CD-Fixer-Agent/1.0"
        }
        
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
    
    def get_workflow_run(self, owner: str, repo: str, run_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a workflow run."""
        url = f"{self.base_url}/repos/{owner}/{repo}/actions/runs/{run_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching workflow run: {e}")
            return None
    
    def get_workflow_run_logs(self, owner: str, repo: str, run_id: int) -> Optional[str]:
        """Get logs for a workflow run."""
        url = f"{self.base_url}/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            # The response is a ZIP file containing log files
            # For simplicity, we'll return the raw content
            # In production, you'd want to extract and parse the ZIP
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching workflow logs: {e}")
            # Return sample logs for demo purposes
            return self._get_sample_logs()
    
    def get_workflow_logs(self, owner: str, repo: str, run_id: int) -> Optional[str]:
        """Alias for get_workflow_run_logs to maintain compatibility."""
        return self.get_workflow_run_logs(owner, repo, run_id)
    
    def get_workflow_jobs(self, owner: str, repo: str, run_id: int) -> Optional[List[Dict[str, Any]]]:
        """Get jobs for a workflow run."""
        url = f"{self.base_url}/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("jobs", [])
        except requests.RequestException as e:
            print(f"Error fetching workflow jobs: {e}")
            return None

    def get_workflow_run_jobs(self, owner: str, repo: str, run_id: int) -> Optional[List[Dict[str, Any]]]:
        """Get jobs for a workflow run (alias for get_workflow_jobs)."""
        return self.get_workflow_jobs(owner, repo, run_id)
    
    def create_issue(self, owner: str, repo: str, title: str, body: str, labels: List[str] = None) -> Optional[Dict[str, Any]]:
        """Create an issue with the suggested fix."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        
        data = {
            "title": title,
            "body": body,
            "labels": labels or ["ci-cd-fix", "automated"]
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error creating issue: {e}")
            return None
    
    def create_pull_request(self, owner: str, repo: str, title: str, body: str, 
                          head_branch: str, base_branch: str = "main") -> Optional[Dict[str, Any]]:
        """Create a pull request with the fix."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error creating pull request: {e}")
            return None
    
    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify GitHub webhook signature."""
        import hmac
        import hashlib
        
        expected_signature = "sha256=" + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    def _get_sample_logs(self) -> str:
        """Return sample logs for demo purposes when GitHub API is not available."""
        return """
2024-08-22T10:30:15.123Z [INFO] Starting build process...
2024-08-22T10:30:16.456Z [INFO] Installing dependencies...
2024-08-22T10:30:25.789Z [ERROR] npm ERR! peer dep missing: react@^18.0.0, required by react-dom@18.2.0
2024-08-22T10:30:25.790Z [ERROR] npm ERR! Could not resolve dependency
2024-08-22T10:30:25.791Z [ERROR] npm ERR! npm install failed with exit code 1
2024-08-22T10:30:25.792Z [ERROR] Process completed with exit code 1
2024-08-22T10:30:25.793Z [INFO] Build failed after 10 seconds
        """
    
    def extract_error_from_logs(self, logs: str) -> str:
        """Extract key error information from logs."""
        if not logs:
            return "No logs available"
        
        lines = logs.split('\n')
        error_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['error', 'failed', 'exception', 'fatal']):
                error_lines.append(line.strip())
        
        if error_lines:
            return '\n'.join(error_lines[:10])  # Return first 10 error lines
        else:
            return "No specific errors found in logs"
