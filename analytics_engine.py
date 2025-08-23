"""
Advanced Analytics & Learning Module for CI/CD Fixer Agent

This module implements pattern recognition, success rate tracking,
machine learning-based predictions, and historical analysis for 
improving fix suggestions over time.

Features:
- Pattern Recognition with ML-based similarity detection
- Success Prediction based on historical data
- Intelligent Fix Recommendation engine
- Anomaly Detection for unusual failure patterns
- Adaptive Learning from user feedback
"""

import json
import logging
import pickle
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import re
import math
from dataclasses import dataclass

from postgres_database import PostgreSQLCICDFixerDB

logger = logging.getLogger(__name__)


class CICDPatternAnalyzer:
    """
    Analyzes patterns in CI/CD failures and fixes to improve future suggestions.
    """
    
    def __init__(self):
        self.db = PostgreSQLCICDFixerDB()
    
    def analyze_failure_patterns(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Analyze patterns in workflow failures over the specified time period.
        
        Args:
            days_back: Number of days to look back for analysis
            
        Returns:
            Dictionary containing pattern analysis results
        """
        try:
            # Get all workflow runs from the specified period
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT repo_name, owner, workflow_name, status, conclusion, 
                           error_log, suggested_fix, fix_status, created_at
                    FROM workflow_runs 
                    WHERE created_at >= %s
                    ORDER BY created_at DESC
                """, (cutoff_date,))
                
                runs = cursor.fetchall()
                
            if not runs:
                return {
                    "summary": "No workflow runs found in the specified period",
                    "patterns": {},
                    "recommendations": []
                }
            
            # Analyze patterns
            patterns = self._extract_patterns(runs)
            
            return {
                "analysis_period": f"Last {days_back} days",
                "total_runs": len(runs),
                "patterns": patterns,
                "recommendations": self._generate_recommendations(patterns),
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing failure patterns: {e}")
            return {
                "error": str(e),
                "patterns": {},
                "recommendations": []
            }
    
    def _extract_patterns(self, runs: List[Tuple]) -> Dict[str, Any]:
        """Extract patterns from workflow run data."""
        
        # Initialize pattern counters
        repo_failures = Counter()
        error_types = Counter()
        time_patterns = defaultdict(int)
        fix_success_rates = defaultdict(lambda: {"total": 0, "approved": 0})
        language_patterns = Counter()
        
        for run in runs:
            repo_name, owner, workflow_name, status, conclusion, error_log, suggested_fix, fix_status, created_at = run
            
            # Repository failure patterns
            repo_key = f"{owner}/{repo_name}"
            repo_failures[repo_key] += 1
            
            # Extract error types from logs
            if error_log:
                error_types.update(self._classify_error_types(error_log))
            
            # Time-based patterns (hour of day)
            if created_at:
                hour = created_at.hour
                time_patterns[hour] += 1
            
            # Fix success rates
            if suggested_fix and fix_status:
                fix_success_rates[repo_key]["total"] += 1
                if fix_status == "approved":
                    fix_success_rates[repo_key]["approved"] += 1
            
            # Language/project type patterns
            language = self._detect_project_language(repo_name, error_log)
            if language:
                language_patterns[language] += 1
        
        # Calculate success rates
        success_rates = {}
        for repo, stats in fix_success_rates.items():
            if stats["total"] > 0:
                success_rates[repo] = {
                    "success_rate": stats["approved"] / stats["total"],
                    "total_fixes": stats["total"],
                    "approved_fixes": stats["approved"]
                }
        
        return {
            "most_failing_repos": dict(repo_failures.most_common(10)),
            "common_error_types": dict(error_types.most_common(15)),
            "failure_time_distribution": dict(time_patterns),
            "fix_success_rates": success_rates,
            "language_distribution": dict(language_patterns.most_common(10)),
            "total_unique_repos": len(repo_failures),
            "total_error_types": len(error_types)
        }
    
    def _classify_error_types(self, error_log: str) -> List[str]:
        """Classify error types from error logs."""
        if not error_log:
            return []
        
        error_patterns = {
            "dependency_error": [
                r"npm.*install.*failed",
                r"pip.*install.*error",
                r"package.*not.*found",
                r"dependency.*conflict",
                r"peer.*dependency",
                r"ModuleNotFoundError",
                r"ImportError"
            ],
            "build_failure": [
                r"compilation.*failed",
                r"build.*failed",
                r"webpack.*error",
                r"typescript.*error",
                r"syntax.*error",
                r"compilation error"
            ],
            "test_failure": [
                r"test.*failed",
                r"assertion.*failed",
                r"jest.*failed",
                r"pytest.*failed",
                r"unit.*test.*error",
                r"integration.*test.*failed"
            ],
            "execution_timeout": [
                r"timeout",
                r"exceeded.*time",
                r"job.*cancelled",
                r"process.*killed",
                r"time.*limit.*exceeded"
            ],
            "docker_error": [
                r"docker.*build.*failed",
                r"dockerfile.*error",
                r"container.*failed",
                r"image.*not.*found",
                r"docker.*push.*failed"
            ],
            "linting_error": [
                r"eslint.*error",
                r"pylint.*error",
                r"flake8.*error",
                r"prettier.*error",
                r"code.*style.*violation"
            ],
            "deployment_error": [
                r"deployment.*failed",
                r"publish.*failed",
                r"release.*error",
                r"upload.*failed",
                r"deploy.*timeout"
            ]
        }
        
        detected_errors = []
        error_text = error_log.lower()
        
        for error_type, patterns in error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_text):
                    detected_errors.append(error_type)
                    break  # Only count each error type once per log
        
        return detected_errors
    
    def _detect_project_language(self, repo_name: str, error_log: str) -> Optional[str]:
        """Detect the primary programming language of a project."""
        
        # Language indicators from repo name and error logs
        language_indicators = {
            "javascript": ["package.json", "npm", "yarn", "node", "webpack", "jest", ".js", ".ts"],
            "python": ["requirements.txt", "pip", "pytest", "python", ".py", "virtualenv"],
            "java": ["maven", "gradle", "junit", ".java", "mvn", "pom.xml"],
            "csharp": [".net", "dotnet", "nuget", ".cs", "msbuild"],
            "go": ["go.mod", "go build", ".go", "golang"],
            "rust": ["cargo", ".rs", "rustc", "rust"],
            "ruby": ["gemfile", "bundle", ".rb", "rake"],
            "php": ["composer", ".php", "phpunit"],
            "docker": ["dockerfile", "docker", "container"]
        }
        
        text_to_analyze = f"{repo_name} {error_log or ''}".lower()
        
        language_scores = {}
        for language, indicators in language_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_to_analyze)
            if score > 0:
                language_scores[language] = score
        
        # Return the language with the highest score
        if language_scores:
            return max(language_scores.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _generate_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on patterns."""
        recommendations = []
        
        # Repository-specific recommendations
        if patterns.get("most_failing_repos"):
            top_failing = list(patterns["most_failing_repos"].keys())[0]
            recommendations.append(
                f"Consider creating specialized fix templates for {top_failing} "
                f"which has {patterns['most_failing_repos'][top_failing]} failures"
            )
        
        # Error type recommendations
        if patterns.get("common_error_types"):
            top_error = list(patterns["common_error_types"].keys())[0]
            count = patterns["common_error_types"][top_error]
            recommendations.append(
                f"Focus on improving {top_error} detection and fixes - "
                f"appears in {count} failures"
            )
        
        # Time-based recommendations
        if patterns.get("failure_time_distribution"):
            time_dist = patterns["failure_time_distribution"]
            peak_hour = max(time_dist.items(), key=lambda x: x[1])
            recommendations.append(
                f"Most failures occur at {peak_hour[0]:02d}:00 UTC "
                f"({peak_hour[1]} failures) - consider proactive monitoring"
            )
        
        # Language-specific recommendations
        if patterns.get("language_distribution"):
            top_lang = list(patterns["language_distribution"].keys())[0]
            recommendations.append(
                f"Enhance {top_lang} specific error detection and fix generation"
            )
        
        # Success rate recommendations
        if patterns.get("fix_success_rates"):
            low_success_repos = [
                repo for repo, stats in patterns["fix_success_rates"].items()
                if stats["success_rate"] < 0.5 and stats["total_fixes"] >= 3
            ]
            if low_success_repos:
                recommendations.append(
                    f"Improve fix quality for repositories with low success rates: "
                    f"{', '.join(low_success_repos)}"
                )
        
        return recommendations
    
    def get_fix_effectiveness_stats(self) -> Dict[str, Any]:
        """Get statistics on fix effectiveness and approval rates."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Overall fix statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_fixes,
                        COUNT(CASE WHEN fix_status = 'approved' THEN 1 END) as approved_fixes,
                        COUNT(CASE WHEN fix_status = 'rejected' THEN 1 END) as rejected_fixes,
                        COUNT(CASE WHEN fix_status = 'pending' THEN 1 END) as pending_fixes
                    FROM workflow_runs 
                    WHERE suggested_fix IS NOT NULL
                """)
                
                stats = cursor.fetchone()
                
                if not stats or stats[0] == 0:
                    return {
                        "message": "No fix data available yet",
                        "total_fixes": 0
                    }
                
                total, approved, rejected, pending = stats
                
                # Fix effectiveness by error type
                cursor.execute("""
                    SELECT error_log, fix_status, COUNT(*)
                    FROM workflow_runs 
                    WHERE suggested_fix IS NOT NULL 
                    AND error_log IS NOT NULL
                    GROUP BY error_log, fix_status
                """)
                
                effectiveness_data = cursor.fetchall()
                
                return {
                    "overall_stats": {
                        "total_fixes": total,
                        "approved_fixes": approved,
                        "rejected_fixes": rejected,
                        "pending_fixes": pending,
                        "approval_rate": approved / total if total > 0 else 0,
                        "rejection_rate": rejected / total if total > 0 else 0
                    },
                    "effectiveness_by_type": self._analyze_effectiveness_by_type(effectiveness_data),
                    "generated_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting fix effectiveness stats: {e}")
            return {"error": str(e)}
    
    def _analyze_effectiveness_by_type(self, data: List[Tuple]) -> Dict[str, Any]:
        """Analyze fix effectiveness by error type."""
        type_stats = defaultdict(lambda: {"approved": 0, "rejected": 0, "pending": 0})
        
        for error_log, status, count in data:
            # Classify the error type
            error_types = self._classify_error_types(error_log)
            primary_type = error_types[0] if error_types else "unknown"
            
            type_stats[primary_type][status] += count
        
        # Calculate rates
        effectiveness = {}
        for error_type, stats in type_stats.items():
            total = sum(stats.values())
            if total > 0:
                effectiveness[error_type] = {
                    "total_fixes": total,
                    "approval_rate": stats["approved"] / total,
                    "rejection_rate": stats["rejected"] / total,
                    "pending_rate": stats["pending"] / total
                }
        
        return effectiveness


class RepositoryLearningSystem:
    """
    Builds and maintains a knowledge base for each repository.
    """
    
    def __init__(self):
        self.db = PostgreSQLCICDFixerDB()
    
    def build_repository_profile(self, owner: str, repo_name: str) -> Dict[str, Any]:
        """
        Build a comprehensive profile for a specific repository.
        
        Args:
            owner: Repository owner
            repo_name: Repository name
            
        Returns:
            Repository profile with patterns and recommendations
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all runs for this repository
                cursor.execute("""
                    SELECT workflow_name, status, conclusion, error_log, 
                           suggested_fix, fix_status, created_at
                    FROM workflow_runs 
                    WHERE owner = %s AND repo_name = %s
                    ORDER BY created_at DESC
                """, (owner, repo_name))
                
                runs = cursor.fetchall()
                
            if not runs:
                return {
                    "repository": f"{owner}/{repo_name}",
                    "message": "No data available for this repository",
                    "total_runs": 0
                }
            
            profile = self._analyze_repository_data(runs)
            profile["repository"] = f"{owner}/{repo_name}"
            profile["total_runs"] = len(runs)
            profile["analyzed_at"] = datetime.utcnow().isoformat()
            
            return profile
            
        except Exception as e:
            logger.error(f"Error building repository profile: {e}")
            return {
                "repository": f"{owner}/{repo_name}",
                "error": str(e)
            }
    
    def _analyze_repository_data(self, runs: List[Tuple]) -> Dict[str, Any]:
        """Analyze repository-specific patterns."""
        
        workflow_patterns = Counter()
        error_patterns = Counter()
        fix_patterns = []
        success_trends = []
        
        for run in runs:
            workflow_name, status, conclusion, error_log, suggested_fix, fix_status, created_at = run
            
            # Workflow failure patterns
            if conclusion == "failure":
                workflow_patterns[workflow_name] += 1
            
            # Error pattern analysis
            if error_log:
                analyzer = CICDPatternAnalyzer()
                error_types = analyzer._classify_error_types(error_log)
                error_patterns.update(error_types)
            
            # Fix pattern tracking
            if suggested_fix and fix_status:
                fix_patterns.append({
                    "fix_preview": suggested_fix[:100] + "..." if len(suggested_fix) > 100 else suggested_fix,
                    "status": fix_status,
                    "date": created_at.isoformat() if created_at else None
                })
            
            # Success trends (last 30 runs)
            if len(success_trends) < 30:
                success_trends.append({
                    "date": created_at.isoformat() if created_at else None,
                    "successful": conclusion != "failure"
                })
        
        # Calculate success rate
        successful_runs = sum(1 for trend in success_trends if trend["successful"])
        success_rate = successful_runs / len(success_trends) if success_trends else 0
        
        return {
            "most_failing_workflows": dict(workflow_patterns.most_common(5)),
            "common_error_types": dict(error_patterns.most_common(10)),
            "recent_fixes": fix_patterns[:10],  # Last 10 fixes
            "success_rate": success_rate,
            "success_trend": success_trends,
            "recommendations": self._generate_repo_recommendations(
                workflow_patterns, error_patterns, success_rate
            )
        }
    
    def _generate_repo_recommendations(self, workflow_patterns: Counter, 
                                     error_patterns: Counter, 
                                     success_rate: float) -> List[str]:
        """Generate repository-specific recommendations."""
        recommendations = []
        
        # Workflow-specific recommendations
        if workflow_patterns:
            most_failing_workflow = workflow_patterns.most_common(1)[0]
            recommendations.append(
                f"Focus on stabilizing '{most_failing_workflow[0]}' workflow "
                f"({most_failing_workflow[1]} failures)"
            )
        
        # Error-specific recommendations
        if error_patterns:
            top_error = error_patterns.most_common(1)[0]
            recommendations.append(
                f"Address recurring {top_error[0]} issues "
                f"({top_error[1]} occurrences)"
            )
        
        # Success rate recommendations
        if success_rate < 0.7:
            recommendations.append(
                f"Success rate is {success_rate:.1%} - consider implementing "
                "more robust testing and error prevention"
            )
        elif success_rate > 0.9:
            recommendations.append(
                f"Excellent success rate of {success_rate:.1%} - "
                "consider sharing best practices with other repositories"
            )
        
        return recommendations


@dataclass
class FixPattern:
    """Represents a learned fix pattern for similarity matching."""
    error_signature: str
    fix_template: str
    success_rate: float
    usage_count: int
    repo_contexts: Set[str]
    last_updated: datetime


class MLPatternRecognizer:
    """
    Machine Learning-based pattern recognition for CI/CD failures.
    Uses similarity matching and clustering to identify related issues.
    """
    
    def __init__(self):
        self.db = PostgreSQLCICDFixerDB()
        self.learned_patterns: List[FixPattern] = []
        self.load_learned_patterns()
    
    def extract_error_signature(self, error_log: str) -> str:
        """Extract a normalized signature from error log for similarity matching."""
        if not error_log:
            return ""
        
        # Normalize the error log
        normalized = error_log.lower()
        
        # Extract key error patterns
        patterns = [
            r"error:?\s*(.+?)(?:\n|$)",
            r"failed:?\s*(.+?)(?:\n|$)",
            r"exception:?\s*(.+?)(?:\n|$)",
            r"(\w+error\w*)",
            r"(\w+exception\w*)",
        ]
        
        extracted_parts = []
        for pattern in patterns:
            matches = re.findall(pattern, normalized)
            extracted_parts.extend(matches[:3])  # Limit to 3 matches per pattern
        
        # Remove file paths, line numbers, and timestamps
        cleaned_parts = []
        for part in extracted_parts:
            # Remove file paths
            part = re.sub(r'/[\w/.-]+\.\w+', '<file>', part)
            # Remove line numbers
            part = re.sub(r'line\s+\d+', 'line <num>', part)
            # Remove timestamps
            part = re.sub(r'\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2}', '<time>', part)
            # Remove specific numbers but keep error codes
            part = re.sub(r'\b\d+\b(?![a-z])', '<num>', part)
            
            if len(part.strip()) > 10:  # Only include meaningful parts
                cleaned_parts.append(part.strip())
        
        # Create signature hash
        signature_text = " | ".join(cleaned_parts[:5])  # Limit to 5 parts
        return hashlib.md5(signature_text.encode()).hexdigest()[:16]
    
    def calculate_similarity(self, sig1: str, sig2: str, log1: str, log2: str) -> float:
        """Calculate similarity between two error signatures and logs."""
        if sig1 == sig2:
            return 1.0
        
        # Jaccard similarity for error logs
        words1 = set(re.findall(r'\w+', log1.lower()))
        words2 = set(re.findall(r'\w+', log2.lower()))
        
        if not words1 and not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def find_similar_fixes(self, error_log: str, repo_context: str, 
                          min_similarity: float = 0.3) -> List[Dict[str, Any]]:
        """Find similar fixes based on error patterns and repository context."""
        error_signature = self.extract_error_signature(error_log)
        similar_fixes = []
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get historical fixes with good success rates
                cursor.execute("""
                    SELECT DISTINCT error_log, suggested_fix, fix_status, 
                           repo_name, owner, created_at
                    FROM workflow_runs 
                    WHERE suggested_fix IS NOT NULL 
                    AND fix_status = 'approved'
                    AND error_log IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 500
                """)
                
                historical_fixes = cursor.fetchall()
                
            for fix_data in historical_fixes:
                hist_error, hist_fix, status, repo, owner, created = fix_data
                hist_signature = self.extract_error_signature(hist_error)
                
                similarity = self.calculate_similarity(
                    error_signature, hist_signature, error_log, hist_error
                )
                
                if similarity >= min_similarity:
                    repo_match_bonus = 0.2 if f"{owner}/{repo}" == repo_context else 0
                    adjusted_similarity = min(1.0, similarity + repo_match_bonus)
                    
                    similar_fixes.append({
                        "similarity_score": adjusted_similarity,
                        "historical_fix": hist_fix,
                        "repository": f"{owner}/{repo}",
                        "date": created.isoformat() if created else None,
                        "error_pattern": hist_error[:200] + "..." if len(hist_error) > 200 else hist_error
                    })
            
            # Sort by similarity and return top matches
            similar_fixes.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similar_fixes[:10]
            
        except Exception as e:
            logger.error(f"Error finding similar fixes: {e}")
            return []
    
    def learn_from_feedback(self, error_log: str, suggested_fix: str, 
                           fix_status: str, repo_context: str):
        """Learn from user feedback to improve future recommendations."""
        if fix_status not in ["approved", "rejected"]:
            return
        
        error_signature = self.extract_error_signature(error_log)
        
        # Find existing pattern or create new one
        existing_pattern = None
        for pattern in self.learned_patterns:
            if pattern.error_signature == error_signature:
                existing_pattern = pattern
                break
        
        if existing_pattern:
            existing_pattern.usage_count += 1
            existing_pattern.repo_contexts.add(repo_context)
            existing_pattern.last_updated = datetime.utcnow()
            
            if fix_status == "approved":
                # Improve success rate with weighted average
                total_weight = existing_pattern.usage_count
                existing_pattern.success_rate = (
                    (existing_pattern.success_rate * (total_weight - 1) + 1.0) / total_weight
                )
            else:  # rejected
                total_weight = existing_pattern.usage_count
                existing_pattern.success_rate = (
                    (existing_pattern.success_rate * (total_weight - 1) + 0.0) / total_weight
                )
        
        elif fix_status == "approved":
            # Create new pattern for approved fixes
            new_pattern = FixPattern(
                error_signature=error_signature,
                fix_template=suggested_fix,
                success_rate=1.0,
                usage_count=1,
                repo_contexts={repo_context},
                last_updated=datetime.utcnow()
            )
            self.learned_patterns.append(new_pattern)
        
        # Persist the learned patterns
        self.save_learned_patterns()
    
    def save_learned_patterns(self):
        """Save learned patterns to database for persistence."""
        try:
            # Store as JSON in a simple table
            patterns_data = []
            for pattern in self.learned_patterns:
                patterns_data.append({
                    "error_signature": pattern.error_signature,
                    "fix_template": pattern.fix_template,
                    "success_rate": pattern.success_rate,
                    "usage_count": pattern.usage_count,
                    "repo_contexts": list(pattern.repo_contexts),
                    "last_updated": pattern.last_updated.isoformat()
                })
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS learned_patterns (
                        id SERIAL PRIMARY KEY,
                        patterns_data JSONB,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Clear old data and insert new
                cursor.execute("DELETE FROM learned_patterns")
                cursor.execute(
                    "INSERT INTO learned_patterns (patterns_data) VALUES (%s)",
                    (json.dumps(patterns_data),)
                )
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving learned patterns: {e}")
    
    def load_learned_patterns(self):
        """Load learned patterns from database."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT patterns_data FROM learned_patterns 
                    ORDER BY updated_at DESC LIMIT 1
                """)
                
                result = cursor.fetchone()
                
            if result:
                patterns_data = result[0]
                self.learned_patterns = []
                
                for data in patterns_data:
                    pattern = FixPattern(
                        error_signature=data["error_signature"],
                        fix_template=data["fix_template"],
                        success_rate=data["success_rate"],
                        usage_count=data["usage_count"],
                        repo_contexts=set(data["repo_contexts"]),
                        last_updated=datetime.fromisoformat(data["last_updated"])
                    )
                    self.learned_patterns.append(pattern)
                
                logger.info(f"Loaded {len(self.learned_patterns)} learned patterns")
            
        except Exception as e:
            logger.error(f"Error loading learned patterns: {e}")
            self.learned_patterns = []


class SuccessPredictor:
    """
    Predicts the likelihood of fix success based on historical patterns.
    """
    
    def __init__(self):
        self.db = PostgreSQLCICDFixerDB()
        self.pattern_recognizer = MLPatternRecognizer()
    
    def predict_fix_success(self, error_log: str, suggested_fix: str, 
                          repo_context: str) -> Dict[str, Any]:
        """Predict the likelihood of a fix being successful."""
        try:
            # Base factors for prediction
            factors = {
                "similarity_match": 0.0,
                "repo_history": 0.0,
                "fix_complexity": 0.0,
                "error_type_reliability": 0.0,
                "time_context": 0.0
            }
            
            # Factor 1: Similarity to successful historical fixes
            similar_fixes = self.pattern_recognizer.find_similar_fixes(
                error_log, repo_context, min_similarity=0.2
            )
            
            if similar_fixes:
                avg_similarity = sum(fix["similarity_score"] for fix in similar_fixes[:5]) / min(5, len(similar_fixes))
                factors["similarity_match"] = avg_similarity
            
            # Factor 2: Repository's historical fix success rate
            repo_success_rate = self._get_repo_success_rate(repo_context)
            factors["repo_history"] = repo_success_rate
            
            # Factor 3: Fix complexity (simpler fixes tend to work better)
            fix_complexity = self._assess_fix_complexity(suggested_fix)
            factors["fix_complexity"] = 1.0 - fix_complexity  # Invert (simpler = better)
            
            # Factor 4: Error type reliability
            error_reliability = self._get_error_type_reliability(error_log)
            factors["error_type_reliability"] = error_reliability
            
            # Factor 5: Time context (recent fixes might be more reliable)
            factors["time_context"] = 0.8  # Base value, could be enhanced
            
            # Weighted combination
            weights = {
                "similarity_match": 0.3,
                "repo_history": 0.25,
                "fix_complexity": 0.2,
                "error_type_reliability": 0.15,
                "time_context": 0.1
            }
            
            predicted_success = sum(
                factors[factor] * weights[factor] 
                for factor in factors
            )
            
            # Confidence based on data availability
            confidence = min(1.0, (
                (len(similar_fixes) / 10) * 0.4 +
                (1.0 if repo_success_rate > 0 else 0.0) * 0.3 +
                0.3  # Base confidence
            ))
            
            return {
                "predicted_success_rate": predicted_success,
                "confidence": confidence,
                "factors": factors,
                "recommendations": self._generate_prediction_recommendations(factors, predicted_success),
                "similar_fixes_found": len(similar_fixes)
            }
            
        except Exception as e:
            logger.error(f"Error predicting fix success: {e}")
            return {
                "predicted_success_rate": 0.5,
                "confidence": 0.1,
                "error": str(e)
            }
    
    def _get_repo_success_rate(self, repo_context: str) -> float:
        """Get historical success rate for the repository."""
        try:
            owner, repo = repo_context.split("/") if "/" in repo_context else ("", repo_context)
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN fix_status = 'approved' THEN 1 END) as approved,
                        COUNT(*) as total
                    FROM workflow_runs 
                    WHERE owner = %s AND repo_name = %s 
                    AND suggested_fix IS NOT NULL 
                    AND fix_status IN ('approved', 'rejected')
                """, (owner, repo))
                
                result = cursor.fetchone()
                
            if result and result[1] > 0:
                return result[0] / result[1]
            
            return 0.5  # Default if no history
            
        except Exception as e:
            logger.error(f"Error getting repo success rate: {e}")
            return 0.5
    
    def _assess_fix_complexity(self, fix_text: str) -> float:
        """Assess the complexity of a suggested fix (0=simple, 1=complex)."""
        if not fix_text:
            return 1.0
        
        complexity_indicators = {
            "multiline_changes": len(fix_text.split('\n')) / 50,  # More lines = more complex
            "multiple_files": fix_text.count("file:") / 10,
            "code_deletion": fix_text.lower().count("delete") / 5,
            "configuration_changes": len(re.findall(r'\.(json|yaml|yml|xml|config)', fix_text.lower())) / 5,
            "dependency_changes": len(re.findall(r'(install|upgrade|add.*dependency)', fix_text.lower())) / 3
        }
        
        # Weighted complexity score
        weights = {
            "multiline_changes": 0.3,
            "multiple_files": 0.2,
            "code_deletion": 0.15,
            "configuration_changes": 0.2,
            "dependency_changes": 0.15
        }
        
        complexity = sum(
            min(1.0, complexity_indicators[factor]) * weights[factor]
            for factor in complexity_indicators
        )
        
        return min(1.0, complexity)
    
    def _get_error_type_reliability(self, error_log: str) -> float:
        """Get reliability score for the error type based on historical fix success."""
        analyzer = CICDPatternAnalyzer()
        error_types = analyzer._classify_error_types(error_log)
        
        if not error_types:
            return 0.5
        
        # Reliability scores based on typical fix success rates for different error types
        type_reliability = {
            "dependency_error": 0.8,      # Usually fixable
            "linting_error": 0.9,         # Very fixable
            "test_failure": 0.7,          # Moderately fixable
            "build_failure": 0.6,         # Can be complex
            "docker_error": 0.5,          # Often complex
            "execution_timeout": 0.4,     # Hard to fix
            "deployment_error": 0.5       # Variable complexity
        }
        
        primary_type = error_types[0]
        return type_reliability.get(primary_type, 0.5)
    
    def _generate_prediction_recommendations(self, factors: Dict[str, float], 
                                           predicted_success: float) -> List[str]:
        """Generate recommendations based on prediction factors."""
        recommendations = []
        
        if predicted_success < 0.3:
            recommendations.append("⚠️ Low success probability - consider manual review before applying")
        elif predicted_success > 0.8:
            recommendations.append("✅ High success probability - safe to apply automatically")
        
        if factors["similarity_match"] < 0.2:
            recommendations.append("🔍 No similar historical fixes found - proceed with caution")
        
        if factors["fix_complexity"] < 0.5:  # Remember we inverted this
            recommendations.append("🔧 Complex fix detected - consider breaking into smaller changes")
        
        if factors["repo_history"] < 0.3:
            recommendations.append("📊 Repository has low historical fix success rate")
        
        return recommendations


class IntelligentFixGenerator:
    """
    Enhanced fix generation that learns from patterns and success rates.
    """
    
    def __init__(self):
        self.db = PostgreSQLCICDFixerDB()
        self.pattern_recognizer = MLPatternRecognizer()
        self.success_predictor = SuccessPredictor()
    
    def generate_enhanced_fix(self, error_log: str, repo_context: str, 
                            base_fix: str = None) -> Dict[str, Any]:
        """Generate an enhanced fix recommendation with ML insights."""
        try:
            # Find similar successful fixes
            similar_fixes = self.pattern_recognizer.find_similar_fixes(
                error_log, repo_context, min_similarity=0.3
            )
            
            # Generate fix recommendation
            if similar_fixes and similar_fixes[0]["similarity_score"] > 0.7:
                # High similarity - adapt the historical fix
                recommended_fix = self._adapt_historical_fix(
                    similar_fixes[0]["historical_fix"], 
                    error_log, 
                    repo_context
                )
                strategy = "adapted_from_similar"
            elif base_fix:
                # Enhance the base fix with learned patterns
                recommended_fix = self._enhance_base_fix(base_fix, similar_fixes)
                strategy = "enhanced_base"
            else:
                # Generate new fix from patterns
                recommended_fix = self._generate_from_patterns(error_log, similar_fixes)
                strategy = "pattern_based"
            
            # Predict success probability
            prediction = self.success_predictor.predict_fix_success(
                error_log, recommended_fix, repo_context
            )
            
            return {
                "recommended_fix": recommended_fix,
                "generation_strategy": strategy,
                "similar_fixes_found": len(similar_fixes),
                "top_similar_fixes": similar_fixes[:3],
                "success_prediction": prediction,
                "confidence_level": self._assess_confidence_level(prediction["confidence"]),
                "enhancement_notes": self._generate_enhancement_notes(strategy, similar_fixes)
            }
            
        except Exception as e:
            logger.error(f"Error generating enhanced fix: {e}")
            return {
                "recommended_fix": base_fix or "Unable to generate fix recommendation",
                "generation_strategy": "fallback",
                "error": str(e),
                "success_prediction": {"predicted_success_rate": 0.5, "confidence": 0.1}
            }
    
    def _adapt_historical_fix(self, historical_fix: str, current_error: str, 
                            repo_context: str) -> str:
        """Adapt a historical fix to the current context."""
        # Basic adaptation - in a full ML system, this could be much more sophisticated
        adapted_fix = historical_fix
        
        # Extract repository-specific context
        if "/" in repo_context:
            owner, repo = repo_context.split("/")
            adapted_fix = adapted_fix.replace("<repo>", repo).replace("<owner>", owner)
        
        # Add context-aware note
        adaptation_note = f"\n\n# Adapted from similar fix in repository context\n# Original success rate: High\n# Context: {repo_context}"
        
        return adapted_fix + adaptation_note
    
    def _enhance_base_fix(self, base_fix: str, similar_fixes: List[Dict]) -> str:
        """Enhance a base fix with insights from similar fixes."""
        enhanced_fix = base_fix
        
        if similar_fixes:
            enhancement_note = f"\n\n# Enhanced with insights from {len(similar_fixes)} similar cases\n"
            enhancement_note += "# Additional considerations based on historical patterns:\n"
            
            for i, fix in enumerate(similar_fixes[:2]):
                enhancement_note += f"# {i+1}. From {fix['repository']} (similarity: {fix['similarity_score']:.2f})\n"
            
            enhanced_fix += enhancement_note
        
        return enhanced_fix
    
    def _generate_from_patterns(self, error_log: str, similar_fixes: List[Dict]) -> str:
        """Generate a fix based on learned patterns."""
        if not similar_fixes:
            return "# No similar patterns found\n# Manual investigation recommended\n# Check error logs and repository documentation"
        
        # Create a fix based on common patterns in similar fixes
        pattern_fix = "# Generated from similar patterns:\n\n"
        
        # Extract common commands/approaches from similar fixes
        common_patterns = []
        for fix in similar_fixes[:3]:
            lines = fix["historical_fix"].split('\n')
            for line in lines:
                if any(cmd in line.lower() for cmd in ['npm', 'pip', 'apt', 'yarn', 'mvn', 'gradle']):
                    common_patterns.append(line.strip())
        
        if common_patterns:
            pattern_fix += "# Common fix patterns identified:\n"
            for pattern in set(common_patterns[:5]):  # Remove duplicates, limit to 5
                pattern_fix += f"# {pattern}\n"
        
        pattern_fix += "\n# Recommended action based on patterns:\n"
        pattern_fix += "# 1. Review the error log for specific failure points\n"
        pattern_fix += "# 2. Check dependency versions and compatibility\n"
        pattern_fix += "# 3. Verify configuration files\n"
        
        return pattern_fix
    
    def _assess_confidence_level(self, confidence_score: float) -> str:
        """Convert confidence score to human-readable level."""
        if confidence_score >= 0.8:
            return "Very High"
        elif confidence_score >= 0.6:
            return "High"
        elif confidence_score >= 0.4:
            return "Medium"
        elif confidence_score >= 0.2:
            return "Low"
        else:
            return "Very Low"
    
    def _generate_enhancement_notes(self, strategy: str, similar_fixes: List[Dict]) -> List[str]:
        """Generate notes about the enhancement process."""
        notes = []
        
        if strategy == "adapted_from_similar":
            notes.append(f"✅ Adapted from highly similar fix (top match: {similar_fixes[0]['similarity_score']:.2f} similarity)")
        elif strategy == "enhanced_base":
            notes.append(f"🔧 Enhanced base fix with insights from {len(similar_fixes)} similar cases")
        elif strategy == "pattern_based":
            notes.append(f"🧠 Generated from learned patterns across {len(similar_fixes)} similar fixes")
        
        if similar_fixes:
            unique_repos = len(set(fix["repository"] for fix in similar_fixes))
            notes.append(f"📊 Drew insights from {unique_repos} different repositories")
        
        return notes
