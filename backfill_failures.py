#!/usr/bin/env python3
"""
Backfill script to capture historical workflow failures from repositories with webhooks enabled.
This ensures we have all the real failure data that users expect to see.
"""

import os
import sys
import requests
from datetime import datetime
from postgres_database import PostgreSQLCICDFixerDB

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

def get_workflow_failures(owner: str, repo: str, per_page: int = 50):
    """Get all failed workflow runs from a GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
    params = {
        "status": "failure",
        "per_page": per_page
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("workflow_runs", [])
    except Exception as e:
        print(f"Error fetching workflow runs for {owner}/{repo}: {e}")
        return []

def backfill_repository_failures(db: PostgreSQLCICDFixerDB, owner: str, repo: str):
    """Backfill all missing workflow failures for a repository."""
    print(f"🔍 Checking failures for {owner}/{repo}...")
    
    workflow_runs = get_workflow_failures(owner, repo)
    
    if not workflow_runs:
        print(f"❌ No failed workflows found for {owner}/{repo}")
        return 0
    
    print(f"📋 Found {len(workflow_runs)} failed workflow runs")
    
    added_count = 0
    
    for run in workflow_runs:
        run_id = run.get("id")
        workflow_name = run.get("name", "Unknown Workflow")
        conclusion = run.get("conclusion", "failure")
        status = run.get("status", "completed")
        created_at = run.get("created_at")
        head_sha = run.get("head_sha", "")
        head_branch = run.get("head_branch", "main")
        
        existing = db.get_workflow_run_by_run_id(repo, owner, run_id)
        if existing:
            print(f"⏭️  Run {run_id} already exists, skipping...")
            continue
        
        run_data = {
            'repo_name': repo,
            'owner': owner,
            'run_id': run_id,
            'workflow_name': workflow_name,
            'status': status,
            'conclusion': conclusion,
            'error_log': f"Workflow failed with conclusion: {conclusion}"
        }
        
        try:
            result = db.insert_workflow_run(run_data)
            if result and result != -1:
                print(f"✅ Added failure: {workflow_name} (Run {run_id})")
                added_count += 1
            else:
                print(f"❌ Failed to add run {run_id}")
        except Exception as e:
            print(f"❌ Error adding run {run_id}: {e}")
    
    return added_count

def main():
    """Main backfill function."""
    print("🚀 Starting workflow failures backfill...")
    
    db = PostgreSQLCICDFixerDB()
    
    if not db.is_available():
        print("❌ Database is not available. Exiting.")
        return
    
    try:
        repositories = [
            ("chaitanyak175", "ci-cd-test-repo"),
        ]
        
        total_added = 0
        
        for owner, repo in repositories:
            added = backfill_repository_failures(db, owner, repo)
            total_added += added
            print(f"📊 Added {added} failures for {owner}/{repo}")
            print("-" * 50)
        
        print(f"🎉 Backfill complete! Added {total_added} total failures")
        
        all_failures = db.get_workflow_runs()
        print(f"📈 Database now contains {len(all_failures)} total failures")
        
        repo_counts = {}
        for failure in all_failures:
            repo_key = f"{failure.get('owner', 'unknown')}/{failure.get('repo_name', 'unknown')}"
            repo_counts[repo_key] = repo_counts.get(repo_key, 0) + 1
        
        print("\n📊 Failures by repository:")
        for repo, count in sorted(repo_counts.items()):
            print(f"  {repo}: {count} failures")
            
    except Exception as e:
        print(f"❌ Error during backfill: {e}")

if __name__ == "__main__":
    main()
