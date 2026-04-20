#!/usr/bin/env python3
"""
Agentic CI/CD Pipeline Manager
Kaggle 5-Day Intensive Agent Course - Capstone Project

Orchestrates Code Review, Security Audit, and QA Testing on a GitHub PR,
and pauses for human approval before merging to 'vermasang/jobBot'.
"""

import os
import requests
import subprocess
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# ── 1. DEFINE PIPELINE STATE ─────────────────────────────────────────────────
class CICDState(TypedDict):
    repo_name: str
    pr_number: int
    code_diff: str
    review_comments: str
    security_report: str
    qa_status: str
    human_approved: bool
    final_status: str

# ── 2. DEFINE AGENT NODES ────────────────────────────────────────────────────
def fetch_pr_details(state: CICDState) -> dict:
    """Node: Fetches real PR diff from GitHub using the REST API."""
    repo_name = state['repo_name']
    pr_number = state['pr_number']
    print(f"\n[fetch_pr] Fetching PR #{pr_number} from {repo_name}...")
    
    url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}"
    headers = {"Accept": "application/vnd.github.v3.diff"}
    
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
        
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        print(f"[fetch_pr] Successfully fetched diff ({len(response.text)} bytes).")
        return {"code_diff": response.text}
    except requests.exceptions.RequestException as e:
        print(f"❌ [fetch_pr] Error fetching PR diff: {e}")
        return {"code_diff": f"Error fetching diff: {e}"}

def code_review_agent(state: CICDState) -> dict:
    """Agent node: Reviews the code for best practices and quality."""
    print(f"[code_review] Reviewing code changes...")
    # In production, pass state['code_diff'] to an LLM (e.g., Claude/OpenAI)
    return {"review_comments": "Code is clean, but 'TODO' left in auth function."}

def security_audit_agent(state: CICDState) -> dict:
    """Agent node: Scans code for vulnerabilities and secrets."""
    print(f"[security_audit] Scanning for vulnerabilities...")
    # In production, prompt LLM to act as a strict AppSec engineer
    return {"security_report": "PASS. No hardcoded secrets detected."}

def qa_testing_agent(state: CICDState) -> dict:
    """Agent node: Runs real unit tests using pytest."""
    print(f"[qa_testing] Running real QA tests via pytest...")
    
    try:
        # Run pytest and capture the output
        result = subprocess.run(
            ["pytest", "-v"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0:
            status = f"✅ PASS\n{result.stdout.strip()}"
        else:
            status = f"❌ FAIL (exit code {result.returncode})\n{result.stdout.strip()}\n{result.stderr.strip()}"
            
        return {"qa_status": status}
    except FileNotFoundError:
        return {"qa_status": "⚠️ pytest command not found. Make sure it is installed."}

def human_approval(state: CICDState) -> dict:
    """
    Dummy node for LangGraph to pause before. 
    Execution suspends before entering this node until resumed.
    """
    print(f"\n[human_approval] Processing human decision...")
    return {}

def merge_code_agent(state: CICDState) -> dict:
    """Final node: Pushes to github/merges PR based on human approval."""
    approved = state.get("human_approved", False)
    
    if approved:
        print(f"✅ [merge_code] APPROVED! Merging PR #{state['pr_number']} into {state['repo_name']} main branch...")
        # In production, trigger GitHub API to merge PR
        return {"final_status": "Merged successfully"}
    else:
        print(f"❌ [merge_code] REJECTED! Closing PR #{state['pr_number']} without merging.")
        return {"final_status": "Rejected by manager"}

# ── 3. BUILD LANGGRAPH WORKFLOW ──────────────────────────────────────────────
def build_pipeline():
    workflow = StateGraph(CICDState)

    # Add Nodes
    workflow.add_node("fetch_pr", fetch_pr_details)
    workflow.add_node("code_review", code_review_agent)
    workflow.add_node("security_audit", security_audit_agent)
    workflow.add_node("qa_testing", qa_testing_agent)
    workflow.add_node("human_approval", human_approval)
    workflow.add_node("merge_code", merge_code_agent)

    # Define Flow (Edges)
    workflow.add_edge(START, "fetch_pr")
    workflow.add_edge("fetch_pr", "code_review")
    workflow.add_edge("code_review", "security_audit")
    workflow.add_edge("security_audit", "qa_testing")
    workflow.add_edge("qa_testing", "human_approval")
    workflow.add_edge("human_approval", "merge_code")
    workflow.add_edge("merge_code", END)

    # Compile with memory checkpointer (required for human-in-the-loop pauses)
    memory = MemorySaver()
    
    # We interrupt the graph exactly BEFORE it hits the 'human_approval' node
    app = workflow.compile(
        checkpointer=memory, 
        interrupt_before=["human_approval"]
    )
    
    return app

# ── 4. EXECUTION SIMULATION ──────────────────────────────────────────────────
if __name__ == "__main__":
    pipeline_app = build_pipeline()
    
    # Thread configuration to track this specific workflow execution state
    thread_config = {"configurable": {"thread_id": "pr-1-run"}}
    
    initial_state = {

        "repo_name": "SangVerma/capstone",
        "pr_number": 1,
        "human_approved": False
    }
    
    print("🚀 Starting Agentic CI/CD Pipeline...")
    
    # Generate and save a visual graph of the workflow
    try:
        with open("workflow_visual.png", "wb") as f:
            f.write(pipeline_app.get_graph().draw_mermaid_png())
        print("📸 Saved pipeline visualization to 'workflow_visual.png'")
    except Exception as e:
        print(f"⚠️ Note: Could not save graph image (make sure required dependencies are installed): {e}")

    # 1. Run the graph until it hits the interrupt (human approval)
    for event in pipeline_app.stream(initial_state, thread_config, stream_mode="values"):
        pass

    # Verify we paused
    state = pipeline_app.get_state(thread_config)
    if state.next and state.next[0] == "human_approval":
        print("\n" + "="*50)
        print("🛑 PIPELINE PAUSED FOR MANAGER APPROVAL")
        print("Review Comments:", state.values.get("review_comments"))
        print("Security Audit:", state.values.get("security_report"))
        print("QA Status:", state.values.get("qa_status"))
        print("="*50)
        
        # Check if we are running in an automated CI environment (like GitHub Actions)
        if os.environ.get("CI") == "true":
            print("\n🤖 CI Environment detected. Auto-approving for CI simulation purposes.")
            is_approved = True
        else:
            # Simulate a human reviewing the terminal output and pressing 'Y'
            user_input = input("\nApprove this PR for merge to 'vermasang/jobBot'? (y/n): ")
            is_approved = user_input.strip().lower() == 'y'
        
        # Update the state with the human's decision, acting as the human_approval node
        pipeline_app.update_state(
            thread_config, 
            {"human_approved": is_approved},
            as_node="human_approval"
        )
        
        # Resume graph execution from where it left off
        print("\n▶️ Resuming pipeline...")
        for event in pipeline_app.stream(None, thread_config, stream_mode="values"):
            pass
        
    print("\n🏁 Pipeline Finished.")