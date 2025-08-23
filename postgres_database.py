import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
import os
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from urllib.parse import urlparse

class PostgreSQLCICDFixerDB:
    def __init__(self, database_url: str = None):
        if database_url is None:
            database_url = os.getenv('DATABASE_URL')
        
        self.database_url = database_url
        self.init_database()
    
    def get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(self.database_url)
    
    def test_connection(self):
        """Test the database connection."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception:
            return False
    
    def init_database(self):
        """Initialize the PostgreSQL database with required tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create workflow_runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    id SERIAL PRIMARY KEY,
                    repo_name VARCHAR(255) NOT NULL,
                    owner VARCHAR(255) NOT NULL,
                    run_id BIGINT NOT NULL,
                    workflow_name TEXT,
                    status VARCHAR(50) NOT NULL,
                    conclusion VARCHAR(50),
                    error_log TEXT,
                    suggested_fix TEXT,
                    fix_status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(repo_name, owner, run_id)
                )
            """)
            
            # Create portia_plans table for tracking agent execution
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portia_plans (
                    id SERIAL PRIMARY KEY,
                    plan_id VARCHAR(255) UNIQUE NOT NULL,
                    workflow_run_id INTEGER,
                    status VARCHAR(50) NOT NULL,
                    steps_completed INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs (id)
                )
            """)
            
            # Create clarifications table for human approvals
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clarifications (
                    id SERIAL PRIMARY KEY,
                    plan_id VARCHAR(255) NOT NULL,
                    question TEXT NOT NULL,
                    response TEXT,
                    response_type VARCHAR(50),
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES portia_plans (plan_id)
                )
            """)
            
            conn.commit()
    
    def insert_workflow_run(self, run_data: Dict[str, Any]) -> int:
        """Insert a new workflow run record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO workflow_runs 
                (repo_name, owner, run_id, workflow_name, status, conclusion, error_log)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (repo_name, owner, run_id) 
                DO UPDATE SET 
                    workflow_name = EXCLUDED.workflow_name,
                    status = EXCLUDED.status,
                    conclusion = EXCLUDED.conclusion,
                    error_log = EXCLUDED.error_log,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (
                run_data.get('repo_name'),
                run_data.get('owner'),
                run_data.get('run_id'),
                run_data.get('workflow_name'),
                run_data.get('status'),
                run_data.get('conclusion'),
                run_data.get('error_log')
            ))
            
            result = cursor.fetchone()
            return result[0] if result else None
    
    def update_workflow_run_fix(self, run_id: int, suggested_fix: str, fix_status: str = 'suggested'):
        """Update workflow run with suggested fix."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE workflow_runs 
                SET suggested_fix = %s, fix_status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (suggested_fix, fix_status, run_id))
            
            conn.commit()
    
    def get_workflow_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all workflow runs with pagination."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM workflow_runs 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_workflow_run_by_id(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific workflow run by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM workflow_runs WHERE id = %s
            """, (run_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def get_workflow_run_by_run_id(self, repo_name: str, owner: str, run_id: int) -> Optional[Dict[str, Any]]:
        """Get workflow run by run ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM workflow_runs 
                WHERE repo_name = %s AND owner = %s AND run_id = %s
            """, (repo_name, owner, run_id))
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def update_fix_status(self, run_id: int, status: str):
        """Update the fix status of a workflow run."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE workflow_runs 
                SET fix_status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, run_id))
            
            conn.commit()
    
    def insert_portia_plan(self, plan_data: Dict[str, Any]) -> int:
        """Insert a new Portia plan record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO portia_plans 
                (plan_id, workflow_run_id, status, total_steps)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                plan_data.get('plan_id'),
                plan_data.get('workflow_run_id'),
                plan_data.get('status', 'active'),
                plan_data.get('total_steps', 0)
            ))
            
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else None
    
    def update_portia_plan(self, plan_id: str, updates: Dict[str, Any]):
        """Update a Portia plan record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build dynamic UPDATE query
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key in ['status', 'steps_completed', 'total_steps', 'error_message']:
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
            
            if set_clauses:
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                values.append(plan_id)
                
                query = f"UPDATE portia_plans SET {', '.join(set_clauses)} WHERE plan_id = %s"
                cursor.execute(query, values)
                conn.commit()
    
    def get_portia_plans(self) -> List[Dict[str, Any]]:
        """Get all Portia plans."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM portia_plans 
                ORDER BY created_at DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def insert_clarification(self, clarification_data: Dict[str, Any]) -> int:
        """Insert a new clarification request."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO clarifications 
                (plan_id, question, response_type)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (
                clarification_data.get('plan_id'),
                clarification_data.get('question'),
                clarification_data.get('response_type', 'approval')
            ))
            
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else None
    
    def update_clarification(self, clarification_id: int, response: str, status: str = 'resolved'):
        """Update a clarification with response."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE clarifications 
                SET response = %s, status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (response, status, clarification_id))
            
            conn.commit()
    
    def get_pending_clarifications(self) -> List[Dict[str, Any]]:
        """Get all pending clarifications."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT c.*, w.repo_name, w.owner, w.run_id 
                FROM clarifications c
                JOIN portia_plans p ON c.plan_id = p.plan_id
                JOIN workflow_runs w ON p.workflow_run_id = w.id
                WHERE c.status = 'pending'
                ORDER BY c.created_at ASC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total runs
            cursor.execute("SELECT COUNT(*) FROM workflow_runs")
            total_runs = cursor.fetchone()[0]
            
            # Runs by status
            cursor.execute("""
                SELECT fix_status, COUNT(*) 
                FROM workflow_runs 
                GROUP BY fix_status
            """)
            status_counts = dict(cursor.fetchall())
            
            # Recent runs (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) FROM workflow_runs 
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            recent_runs = cursor.fetchone()[0]
            
            return {
                'total_runs': total_runs,
                'status_counts': status_counts,
                'recent_runs': recent_runs
            }
    
    def store_failure(self, failure_data: Dict[str, Any]) -> str:
        """Store failure data and return failure ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO workflow_runs (
                    repo_name, owner, run_id, workflow_name, 
                    status, conclusion, error_log, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (repo_name, owner, run_id) 
                DO UPDATE SET 
                    status = EXCLUDED.status,
                    conclusion = EXCLUDED.conclusion,
                    error_log = EXCLUDED.error_log,
                    updated_at = NOW()
                RETURNING id
            """, (
                failure_data.get('repo', '') or failure_data.get('repository', {}).get('name', ''),
                failure_data.get('owner', '') or failure_data.get('repository', {}).get('owner', {}).get('login', ''),
                failure_data.get('run_id', 0),
                failure_data.get('workflow_name', ''),
                failure_data.get('status', 'failed'),
                failure_data.get('conclusion', 'failure'),
                json.dumps(failure_data),
                datetime.utcnow()
            ))
            result = cursor.fetchone()
            return str(result[0]) if result else None
    
    def store_analysis(self, failure_id: str, analysis_result: Dict[str, Any]):
        """Store analysis result for a failure"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE workflow_runs 
                SET analysis_result = %s, updated_at = NOW()
                WHERE id = %s
            """, (json.dumps(analysis_result), failure_id))
    
    def get_pending_fixes(self) -> List[Dict[str, Any]]:
        """Get all pending fixes"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM workflow_runs 
                WHERE status = 'suggested' OR fix_status = 'suggested'
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_fix(self, fix_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific fix by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM workflow_runs WHERE id = %s", (fix_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
