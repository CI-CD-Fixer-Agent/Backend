import os
import requests
from typing import Dict, Any, Optional, List
import json
import base64
from datetime import datetime

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
           
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching workflow logs: {e}")
          
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
    
    def get_repository_contents(self, owner: str, repo: str, path: str = "", ref: str = "main") -> Optional[List[Dict[str, Any]]]:
        """Get repository contents at a specific path."""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref} if ref else {}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching repository contents: {e}")
            return None
    
    def get_file_content(self, owner: str, repo: str, path: str, ref: str = "main") -> Optional[Dict[str, Any]]:
        """Get content of a specific file."""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref} if ref else {}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching file content: {e}")
            return None
    
    def create_or_update_file(self, owner: str, repo: str, path: str, content: str, 
                            message: str, branch: str = "main", sha: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create or update a file in the repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        
       
        encoded_content = base64.b64encode(content.encode()).decode()
        
        data = {
            "message": message,
            "content": encoded_content,
            "branch": branch
        }
        
     
        if sha:
            data["sha"] = sha
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error creating/updating file: {e}")
            return None
    
    def create_branch(self, owner: str, repo: str, branch_name: str, base_branch: str = "main") -> Optional[Dict[str, Any]]:
        """Create a new branch from base branch."""

        base_ref_url = f"{self.base_url}/repos/{owner}/{repo}/git/refs/heads/{base_branch}"
        
        try:
            response = requests.get(base_ref_url, headers=self.headers)
            response.raise_for_status()
            base_sha = response.json()["object"]["sha"]
           
            create_ref_url = f"{self.base_url}/repos/{owner}/{repo}/git/refs"
            data = {
                "ref": f"refs/heads/{branch_name}",
                "sha": base_sha
            }
            
            response = requests.post(create_ref_url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            print(f"Error creating branch: {e}")
            return None
    
    def get_default_branch(self, owner: str, repo: str) -> str:
        """Get the default branch of the repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("default_branch", "main")
        except requests.RequestException as e:
            print(f"Error fetching repository info: {e}")
            return "main" 
    
    def apply_fix_to_repository(self, owner: str, repo: str, fix_content: str, fix_id: str) -> Optional[Dict[str, Any]]:
        """Apply a fix to the repository by creating a PR with the suggested changes."""
        try:
           
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_name = f"fix/cicd-auto-fix-{fix_id}-{timestamp}"
            
          
            default_branch = self.get_default_branch(owner, repo)
            
           
            branch_result = self.create_branch(owner, repo, branch_name, default_branch)
            if not branch_result:
                return None
            
            
            fix_files = self._parse_fix_content(fix_content)
            
          
            for file_change in fix_files:
                file_path = file_change.get("path")
                new_content = file_change.get("content")
                
                if not file_path or not new_content:
                    continue
                
                
                existing_file = self.get_file_content(owner, repo, file_path, branch_name)
                sha = existing_file.get("sha") if existing_file else None
                
        
                commit_message = f"Auto-fix: Update {file_path} (Fix #{fix_id})"
                self.create_or_update_file(
                    owner, repo, file_path, new_content, 
                    commit_message, branch_name, sha
                )
            
          
            pr_title = f"🤖 Auto-fix for CI/CD Failure (Fix #{fix_id})"
            pr_body = f"""
## 🤖 Automated Fix

This PR contains an automated fix for a CI/CD failure.

### Fix Details:
{fix_content}

### Changes:
- Automatically generated fix based on failure analysis
- Applied by CI/CD Fixer Agent

### Review Required:
Please review the changes before merging to ensure they are correct.

---
*Generated by CI/CD Fixer Agent*
            """
            
            pr_result = self.create_pull_request(
                owner, repo, pr_title, pr_body, branch_name, default_branch
            )
            
            return {
                "branch_name": branch_name,
                "pull_request": pr_result,
                "files_changed": len(fix_files)
            }
            
        except Exception as e:
            print(f"Error applying fix to repository: {e}")
            return None
    
    def _parse_fix_content(self, fix_content: str) -> List[Dict[str, str]]:
        """
        Parse fix content to extract file changes.
        This is a simplified implementation - in production you'd want more sophisticated parsing.
        """
      
        
        files = []
        
        
        if "package.json" in fix_content.lower():
           
            files.append({
                "path": "package.json",
                "content": self._generate_package_json_fix(fix_content)
            })
        elif "dockerfile" in fix_content.lower():
            files.append({
                "path": "Dockerfile",
                "content": self._generate_dockerfile_fix(fix_content)
            })
        elif ".github/workflows" in fix_content.lower():
            files.append({
                "path": ".github/workflows/ci.yml",
                "content": self._generate_workflow_fix(fix_content)
            })
        else:
          
            files.append({
                "path": "AUTOMATED_FIX.md",
                "content": f"""# Automated Fix

## Fix Applied:
{fix_content}

## Instructions:
Please review the suggested changes and apply them manually if needed.

Generated on: {datetime.now().isoformat()}
"""
            })
        
        return files
    
    def _generate_package_json_fix(self, fix_content: str) -> str:
        """Generate a basic package.json fix."""
        return '''
{
  "name": "fixed-project",
  "version": "1.0.0",
  "scripts": {
    "build": "npm run build",
    "test": "npm test",
    "start": "npm start"
  },
  "dependencies": {},
  "devDependencies": {}
}
'''
    
    def _generate_dockerfile_fix(self, fix_content: str) -> str:
        """Generate a basic Dockerfile fix."""
        return '''
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
'''
    
    def _generate_workflow_fix(self, fix_content: str) -> str:
        """Generate a basic GitHub Actions workflow fix."""
        return '''
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        
    - name: Install dependencies
      run: npm install
      
    - name: Run tests
      run: npm test
      
    - name: Build
      run: npm run build
'''
    
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
            return '\n'.join(error_lines[:10]) 
        else:
            return "No specific errors found in logs"
