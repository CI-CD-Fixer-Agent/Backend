import os
import google.generativeai as genai
from typing import Dict, Any, Optional
import json

class GeminiFixerAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-pro')
        else:
            self.model = None
            print("Warning: No Gemini API key provided. Using fallback analysis.")
    
    def analyze_failure_and_suggest_fix(self, error_logs: str, repo_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze CI/CD failure logs and suggest a fix using Gemini AI.
        
        Args:
            error_logs: The error logs from the failed CI/CD run
            repo_context: Additional context about the repository
            
        Returns:
            Dictionary containing analysis and suggested fix
        """
        
        if self.model:
            return self._analyze_with_gemini(error_logs, repo_context)
        else:
            return self._analyze_with_fallback(error_logs, repo_context)
    
    def _analyze_with_gemini(self, error_logs: str, repo_context: Dict[str, Any]) -> Dict[str, Any]:
        """Use Gemini AI to analyze the failure and suggest fixes."""
        
        prompt = self._build_analysis_prompt(error_logs, repo_context)
        
        try:
            response = self.model.generate_content(prompt)
            
            # Parse the response to extract structured information
            return self._parse_gemini_response(response.text)
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return self._analyze_with_fallback(error_logs, repo_context)
    
    def _build_analysis_prompt(self, error_logs: str, repo_context: Dict[str, Any]) -> str:
        """Build a comprehensive prompt for Gemini analysis with enhanced context."""
        
        # Detect project type from repository context
        project_type = self._detect_project_type(error_logs, repo_context)
        language_hints = self._get_language_specific_hints(project_type)
        
        prompt = f"""
You are an expert CI/CD engineer and DevOps specialist with deep knowledge of {project_type} projects. 
Analyze the following failed CI/CD pipeline and provide a comprehensive, actionable fix.

## Repository Context:
- Repository: {repo_context.get('repo_name', 'Unknown')}
- Owner: {repo_context.get('owner', 'Unknown')}
- Workflow: {repo_context.get('workflow_name', 'Unknown')}
- Status: {repo_context.get('status', 'failed')}
- Run ID: {repo_context.get('run_id', 'Unknown')}
- Detected Project Type: {project_type}

## Error Logs Analysis:
```
{error_logs}
```

## Language-Specific Context:
{language_hints}

## Advanced Analysis Instructions:
1. **Error Classification**: Identify the specific error category and root cause
2. **Context Awareness**: Consider the project type and common patterns
3. **Actionable Solutions**: Provide specific, implementable fixes
4. **Risk Assessment**: Evaluate the safety and complexity of the fix
5. **Prevention Strategy**: Suggest measures to prevent similar issues

## Required Analysis Output:

Please provide your analysis in the following JSON format:

```json
{{
    "error_type": "category of error (e.g., dependency_conflict, build_failure, test_failure, etc.)",
    "root_cause": "clear explanation of what caused the failure",
    "severity": "high|medium|low",
    "confidence": "high|medium|low - how confident you are in this analysis",
    "suggested_fix": {{
        "description": "human-readable description of the fix",
        "steps": [
            "step 1: detailed action to take",
            "step 2: another action",
            "..."
        ],
        "files_to_modify": [
            {{
                "file": "path/to/file",
                "changes": "description of changes needed"
            }}
        ],
        "commands_to_run": [
            "command 1",
            "command 2"
        ]
    }},
    "prevention": "how to prevent this issue in the future",
    "estimated_fix_time": "estimated time to implement the fix (e.g., '5 minutes', '1 hour')",
    "risk_level": "low|medium|high - risk of implementing this fix"
}}
```

Focus on providing actionable, specific fixes. If you see dependency issues, suggest exact version numbers. If you see configuration problems, provide the exact configuration changes needed.
"""
        
        return prompt
    
    def _detect_project_type(self, error_logs: str, repo_context: Dict[str, Any]) -> str:
        """Detect the project type based on error logs and repository context."""
        
        error_logs_lower = error_logs.lower()
        repo_name = repo_context.get('repo_name', '').lower()
        
        # Check for specific technology indicators
        if any(keyword in error_logs_lower for keyword in ['npm', 'yarn', 'package.json', 'node_modules']):
            if 'next' in error_logs_lower or 'react' in error_logs_lower:
                return "Next.js/React"
            elif 'vue' in error_logs_lower:
                return "Vue.js"
            elif 'angular' in error_logs_lower:
                return "Angular"
            else:
                return "Node.js/JavaScript"
                
        elif any(keyword in error_logs_lower for keyword in ['pip', 'python', 'requirements.txt', 'pyproject.toml']):
            if 'django' in error_logs_lower:
                return "Django/Python"
            elif 'flask' in error_logs_lower:
                return "Flask/Python"
            elif 'fastapi' in error_logs_lower:
                return "FastAPI/Python"
            else:
                return "Python"
                
        elif any(keyword in error_logs_lower for keyword in ['docker', 'dockerfile', 'container']):
            return "Docker/Containerized"
            
        elif any(keyword in error_logs_lower for keyword in ['maven', 'gradle', 'java']):
            return "Java/JVM"
            
        elif any(keyword in error_logs_lower for keyword in ['cargo', 'rust']):
            return "Rust"
            
        elif any(keyword in error_logs_lower for keyword in ['go mod', 'golang']):
            return "Go"
            
        elif any(keyword in error_logs_lower for keyword in ['.net', 'dotnet', 'csharp']):
            return ".NET/C#"
            
        # Check repository name for hints
        if any(tech in repo_name for tech in ['react', 'next', 'vue', 'angular']):
            return "Frontend/JavaScript"
        elif any(tech in repo_name for tech in ['api', 'backend', 'server']):
            return "Backend/API"
            
        return "General"
    
    def _get_language_specific_hints(self, project_type: str) -> str:
        """Get language-specific analysis hints and common issues."""
        
        hints = {
            "Next.js/React": """
Common Next.js/React Issues:
- Node version compatibility (check .nvmrc or package.json engines)
- Package.json dependency conflicts and peer dependencies
- Build errors due to TypeScript configuration
- Memory issues during build (increase NODE_OPTIONS=--max-old-space-size)
- Environment variable configuration (.env files)
- Static generation errors and API route issues
            """,
            
            "Node.js/JavaScript": """
Common Node.js Issues:
- npm/yarn dependency resolution conflicts
- Node version mismatches between local and CI
- Package-lock.json vs yarn.lock inconsistencies
- Missing global packages or CLI tools
- File system permission issues
- Memory and timeout issues in CI
            """,
            
            "Python": """
Common Python Issues:
- Python version compatibility (check pyproject.toml or runtime.txt)
- pip dependency conflicts and version pinning
- Missing system dependencies for compiled packages
- Virtual environment activation issues
- Path and PYTHONPATH configuration
- Requirements.txt vs setup.py vs pyproject.toml conflicts
            """,
            
            "Django/Python": """
Common Django Issues:
- Database migration conflicts
- Static files collection errors (STATIC_ROOT configuration)
- Missing environment variables for settings
- Database connection string issues
- Collectstatic permission problems
- Requirements for production vs development
            """,
            
            "Docker/Containerized": """
Common Docker Issues:
- Base image availability and version pinning
- COPY/ADD path issues and file permissions
- Multi-stage build layer caching problems
- Resource limits (memory, disk space)
- Network connectivity during build
- Secret management and environment variables
            """,
            
            "Java/JVM": """
Common Java Issues:
- Java version compatibility (check pom.xml or build.gradle)
- Maven/Gradle dependency conflicts
- Memory configuration (heap size, PermGen)
- Test execution timeouts
- Resource file path issues
- Plugin version compatibility
            """
        }
        
        return hints.get(project_type, """
General CI/CD Issues:
- Environment variable configuration
- File permissions and path issues
- Resource constraints (memory, disk, CPU)
- Network connectivity problems
- Cache invalidation needs
- Tool version mismatches
        """)
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini's response and extract structured data."""
        
        try:
            # Try to extract JSON from the response
            import re
            
            # Look for JSON block in the response
            json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # If no JSON block found, try to parse the entire response
            return json.loads(response_text)
            
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Failed to parse Gemini response as JSON: {e}")
            
            # Return a structured fallback based on the text response
            return {
                "error_type": "unknown",
                "root_cause": "Failed to parse AI analysis",
                "severity": "medium",
                "confidence": "low",
                "suggested_fix": {
                    "description": response_text[:500] + "..." if len(response_text) > 500 else response_text,
                    "steps": ["Review the error logs manually", "Check for common CI/CD issues"],
                    "files_to_modify": [],
                    "commands_to_run": []
                },
                "prevention": "Implement better error handling and monitoring",
                "estimated_fix_time": "30 minutes",
                "risk_level": "medium"
            }
    
    def _analyze_with_fallback(self, error_logs: str, repo_context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback analysis when Gemini API is not available."""
        
        # Simple rule-based analysis for common CI/CD issues
        error_logs_lower = error_logs.lower()
        
        if "npm err" in error_logs_lower or "yarn error" in error_logs_lower:
            return self._analyze_npm_error(error_logs)
        elif "docker" in error_logs_lower and ("build" in error_logs_lower or "push" in error_logs_lower):
            return self._analyze_docker_error(error_logs)
        elif "test" in error_logs_lower and ("failed" in error_logs_lower or "error" in error_logs_lower):
            return self._analyze_test_error(error_logs)
        elif "python" in error_logs_lower or "pip" in error_logs_lower:
            return self._analyze_python_error(error_logs)
        else:
            return self._generic_error_analysis(error_logs)
    
    def _analyze_npm_error(self, error_logs: str) -> Dict[str, Any]:
        """Analyze NPM/Yarn related errors."""
        
        if "peer dep missing" in error_logs.lower():
            return {
                "error_type": "dependency_conflict",
                "root_cause": "Missing peer dependency detected in npm/yarn installation",
                "severity": "medium",
                "confidence": "high",
                "suggested_fix": {
                    "description": "Install missing peer dependencies",
                    "steps": [
                        "Identify the missing peer dependency from the error message",
                        "Install the required peer dependency with correct version",
                        "Update package.json to include the peer dependency"
                    ],
                    "files_to_modify": [
                        {
                            "file": "package.json",
                            "changes": "Add missing peer dependency to dependencies or peerDependencies"
                        }
                    ],
                    "commands_to_run": [
                        "npm install <missing-package>@<version>",
                        "npm audit fix"
                    ]
                },
                "prevention": "Use npm ls --depth=0 to check for peer dependency warnings before committing",
                "estimated_fix_time": "10 minutes",
                "risk_level": "low"
            }
        
        return self._generic_npm_error()
    
    def _analyze_docker_error(self, error_logs: str) -> Dict[str, Any]:
        """Analyze Docker related errors."""
        return {
            "error_type": "docker_build_failure",
            "root_cause": "Docker build or push operation failed",
            "severity": "high",
            "confidence": "medium",
            "suggested_fix": {
                "description": "Fix Docker build configuration",
                "steps": [
                    "Check Dockerfile syntax and commands",
                    "Verify base image availability",
                    "Check for file permission issues",
                    "Ensure all required files are copied into the image"
                ],
                "files_to_modify": [
                    {
                        "file": "Dockerfile",
                        "changes": "Review and fix Dockerfile configuration"
                    }
                ],
                "commands_to_run": [
                    "docker build . --no-cache",
                    "docker run --rm -it <image> sh"
                ]
            },
            "prevention": "Test Docker builds locally before pushing",
            "estimated_fix_time": "30 minutes",
            "risk_level": "medium"
        }
    
    def _analyze_test_error(self, error_logs: str) -> Dict[str, Any]:
        """Analyze test failure errors."""
        return {
            "error_type": "test_failure",
            "root_cause": "One or more tests are failing",
            "severity": "high",
            "confidence": "high",
            "suggested_fix": {
                "description": "Fix failing tests",
                "steps": [
                    "Run tests locally to reproduce the failure",
                    "Review test cases and fix the underlying code issues",
                    "Update test expectations if business logic has changed",
                    "Ensure test environment matches CI environment"
                ],
                "files_to_modify": [],
                "commands_to_run": [
                    "npm test",
                    "npm run test:watch"
                ]
            },
            "prevention": "Run full test suite before pushing changes",
            "estimated_fix_time": "1 hour",
            "risk_level": "medium"
        }
    
    def _analyze_python_error(self, error_logs: str) -> Dict[str, Any]:
        """Analyze Python related errors."""
        return {
            "error_type": "python_dependency_error",
            "root_cause": "Python package installation or import error",
            "severity": "medium",
            "confidence": "medium",
            "suggested_fix": {
                "description": "Fix Python dependency issues",
                "steps": [
                    "Check requirements.txt for correct package versions",
                    "Verify Python version compatibility",
                    "Update pip and setuptools",
                    "Clear pip cache if needed"
                ],
                "files_to_modify": [
                    {
                        "file": "requirements.txt",
                        "changes": "Update package versions or add missing packages"
                    }
                ],
                "commands_to_run": [
                    "pip install --upgrade pip",
                    "pip install -r requirements.txt"
                ]
            },
            "prevention": "Use virtual environments and pin exact package versions",
            "estimated_fix_time": "20 minutes",
            "risk_level": "low"
        }
    
    def _generic_npm_error(self) -> Dict[str, Any]:
        """Generic NPM error analysis."""
        return {
            "error_type": "npm_build_failure",
            "root_cause": "NPM installation or build process failed",
            "severity": "medium",
            "confidence": "medium",
            "suggested_fix": {
                "description": "Fix NPM build issues",
                "steps": [
                    "Clear npm cache: npm cache clean --force",
                    "Delete node_modules and package-lock.json",
                    "Reinstall dependencies: npm install",
                    "Check for Node.js version compatibility"
                ],
                "files_to_modify": [],
                "commands_to_run": [
                    "npm cache clean --force",
                    "rm -rf node_modules package-lock.json",
                    "npm install"
                ]
            },
            "prevention": "Use exact Node.js and npm versions in CI",
            "estimated_fix_time": "15 minutes",
            "risk_level": "low"
        }
    
    def _generic_error_analysis(self, error_logs: str) -> Dict[str, Any]:
        """Generic error analysis when specific patterns aren't found."""
        return {
            "error_type": "general_build_failure",
            "root_cause": "Build process failed - requires manual investigation",
            "severity": "medium",
            "confidence": "low",
            "suggested_fix": {
                "description": "Investigate and fix build failure",
                "steps": [
                    "Review the complete error logs carefully",
                    "Check recent code changes that might have caused the issue",
                    "Verify all configuration files are correct",
                    "Test the build process locally",
                    "Check for environment-specific issues"
                ],
                "files_to_modify": [],
                "commands_to_run": [
                    "# Run build locally to reproduce the issue",
                    "# Check git log for recent changes"
                ]
            },
            "prevention": "Implement comprehensive testing and code review processes",
            "estimated_fix_time": "1 hour",
            "risk_level": "medium"
        }
