"""
FastAPI Main Application - RBAC Policy Engine API.
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from src.agent.conversation_agent import ConversationAgent
from src.agent.session_manager import SessionManager
from src.core.policy_builder import PolicyBuilder
from src.core.decision_engine import DecisionEngine
from src.core.schema_cache import SchemaCache
from src.mock_apis import RolesPermissionsAPI, ResourceSchemaAPI, ContextSchemaAPI, PolicyValidatorAPI
from src.models.policy import Policy, PolicyEvaluationRequest, Decision

load_dotenv()

# Ensure output directory exists
Path("output").mkdir(exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="RBAC Policy Engine",
    description="Role-Based Access Control Policy Engine with Natural Language Interface",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize shared components
schema_cache = SchemaCache()
session_manager = SessionManager()
roles_api = RolesPermissionsAPI()
resource_api = ResourceSchemaAPI()
context_api = ContextSchemaAPI()
validator_api = PolicyValidatorAPI(roles_api, resource_api, context_api)

# Store active agents by session ID
active_agents: Dict[str, ConversationAgent] = {}


# ==================== Request/Response Models ====================

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID (creates new if not provided)")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    session_id: str
    type: str
    message: str
    policy: Optional[Dict] = None
    validation_report: Optional[Dict] = None
    needs_more_info: bool = False
    suggestions: Optional[List[str]] = None


class SessionResponse(BaseModel):
    """Response model for session info."""
    id: str
    created_at: str
    updated_at: str
    message_count: int
    has_policy: bool


class PolicyRequest(BaseModel):
    """Request model for policy operations."""
    policy: Dict


class EvaluationRequest(BaseModel):
    """Request model for policy evaluation."""
    role: str
    resource: str
    permission: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class ExportRequest(BaseModel):
    """Request model for policy export."""
    session_id: str


# ==================== Helper Functions ====================

def get_or_create_agent(session_id: Optional[str] = None) -> tuple[str, ConversationAgent]:
    """Get an existing agent or create a new one."""
    if session_id and session_id in active_agents:
        return session_id, active_agents[session_id]
    
    # Create new session
    new_session_id = session_manager.create_session()
    
    try:
        agent = ConversationAgent(schema_cache=schema_cache)
        agent.policy_builder.create_policy(name="RBAC Policy")
        active_agents[new_session_id] = agent
        return new_session_id, agent
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


# ==================== API Endpoints ====================

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "RBAC Policy Engine",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_sessions": len(active_agents)
    }


# ==================== Chat Endpoints ====================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for natural language policy creation.
    Creates a new session if session_id is not provided.
    """
    session_id, agent = get_or_create_agent(request.session_id)
    
    try:
        response = agent.process_message(request.message)
        
        # Get current policy
        policy = agent.get_current_policy()
        policy_dict = policy.to_json() if policy else None
        
        # Save to session
        session_manager.update_session(
            session_id,
            conversation_history=agent.get_conversation_history(),
            policy=policy_dict
        )
        
        return ChatResponse(
            session_id=session_id,
            type=response.get("type", "info"),
            message=response.get("message", ""),
            policy=policy_dict,
            validation_report=response.get("validation_report"),
            needs_more_info=response.get("needs_more_info", False),
            suggestions=response.get("suggestions")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get conversation history for a session."""
    if session_id not in active_agents:
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent = active_agents[session_id]
    return {
        "session_id": session_id,
        "history": agent.get_conversation_history()
    }


# ==================== Session Endpoints ====================

@app.get("/api/sessions")
async def list_sessions():
    """List all active sessions."""
    sessions = session_manager.list_sessions()
    return {"sessions": sessions}


@app.post("/api/sessions")
async def create_session():
    """Create a new session."""
    session_id, agent = get_or_create_agent()
    return {"session_id": session_id}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id in active_agents:
        del active_agents[session_id]
    
    session_manager.delete_session(session_id)
    return {"message": "Session deleted"}


# ==================== Policy Endpoints ====================

@app.get("/api/policy/{session_id}")
async def get_policy(session_id: str):
    """Get the current policy for a session."""
    if session_id not in active_agents:
        # Try to load from session manager
        session = session_manager.get_session(session_id)
        if session and session.get("policy"):
            return session["policy"]
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent = active_agents[session_id]
    policy = agent.get_current_policy()
    
    if not policy:
        return {"message": "No policy created yet", "policy": None}
    
    return policy.to_json()


@app.post("/api/policy/validate/{session_id}")
async def validate_policy(session_id: str):
    """Validate the current policy."""
    if session_id not in active_agents:
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent = active_agents[session_id]
    is_valid, report = agent.validate_current_policy()
    
    return {
        "is_valid": is_valid,
        "validation_report": report
    }


@app.post("/api/policy/export/{session_id}")
async def export_policy(session_id: str):
    """Export the policy and validation report to files."""
    if session_id not in active_agents:
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent = active_agents[session_id]
    policy = agent.get_current_policy()
    
    if not policy:
        raise HTTPException(status_code=400, detail="No policy to export")
    
    # Validate first
    is_valid, validation_report = agent.validate_current_policy()
    
    # Save files
    policy_path = "output/final_policy.json"
    validation_path = "output/validation_report.json"
    
    with open(policy_path, 'w') as f:
        json.dump(policy.to_json(), f, indent=2, default=str)
    
    with open(validation_path, 'w') as f:
        json.dump(validation_report, f, indent=2)
    
    return {
        "message": "Policy exported successfully",
        "policy_file": policy_path,
        "validation_file": validation_path,
        "is_valid": is_valid
    }


@app.get("/api/policy/download/final_policy.json")
async def download_policy():
    """Download the final policy JSON file."""
    path = "output/final_policy.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Policy file not found. Export first.")
    return FileResponse(path, filename="final_policy.json", media_type="application/json")


@app.get("/api/policy/download/validation_report.json")
async def download_validation():
    """Download the validation report JSON file."""
    path = "output/validation_report.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Validation report not found. Export first.")
    return FileResponse(path, filename="validation_report.json", media_type="application/json")


# ==================== Evaluation Endpoints ====================

@app.post("/api/evaluate")
async def evaluate_access(request: EvaluationRequest):
    """Evaluate an access request against the current policy."""
    if not request.session_id or request.session_id not in active_agents:
        raise HTTPException(status_code=400, detail="Valid session_id required")
    
    agent = active_agents[request.session_id]
    policy = agent.get_current_policy()
    
    if not policy:
        raise HTTPException(status_code=400, detail="No policy available for evaluation")
    
    engine = DecisionEngine(policy)
    result = engine.evaluate(
        role=request.role,
        resource=request.resource,
        permission=request.permission,
        context=request.context or {}
    )
    
    return result.model_dump()


@app.post("/api/evaluate/explain")
async def explain_decision(request: EvaluationRequest):
    """Get a detailed explanation of an access decision."""
    if not request.session_id or request.session_id not in active_agents:
        raise HTTPException(status_code=400, detail="Valid session_id required")
    
    agent = active_agents[request.session_id]
    policy = agent.get_current_policy()
    
    if not policy:
        raise HTTPException(status_code=400, detail="No policy available")
    
    engine = DecisionEngine(policy)
    explanation = engine.explain_decision(
        role=request.role,
        resource=request.resource,
        permission=request.permission,
        context=request.context or {}
    )
    
    return explanation


# ==================== Discovery Endpoints ====================

@app.get("/api/discovery/roles")
async def discover_roles():
    """Get all available roles."""
    return roles_api.discover()


@app.get("/api/discovery/resources")
async def discover_resources():
    """Get all available resources."""
    return resource_api.discover()


@app.get("/api/discovery/context")
async def discover_context():
    """Get all available context attributes."""
    return context_api.discover()


@app.get("/api/discovery/all")
async def discover_all():
    """Get all schemas (cached)."""
    schemas = schema_cache.discover_and_cache_schemas(
        roles_api, resource_api, context_api
    )
    return schemas


@app.get("/api/discovery/cache-info")
async def get_cache_info():
    """Get cache status information."""
    return schema_cache.get_cache_info()


# ==================== Startup/Shutdown Events ====================

@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print("🚀 RBAC Policy Engine starting up...")
    
    # Pre-cache schemas
    schemas = schema_cache.discover_and_cache_schemas(
        roles_api, resource_api, context_api
    )
    print(f"✅ Cached schemas: {len(schemas['roles']['roles'])} roles, "
          f"{len(schemas['resources']['resources'])} resources, "
          f"{len(schemas['context']['attributes'])} context attributes")
    
    # Load existing sessions
    sessions = session_manager.list_sessions()
    print(f"📂 Found {len(sessions)} existing sessions")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print("👋 RBAC Policy Engine shutting down...")
    
    # Save all active sessions
    for session_id, agent in active_agents.items():
        policy = agent.get_current_policy()
        if policy:
            session_manager.save_policy(session_id, policy.to_json())
    
    print(f"💾 Saved {len(active_agents)} active sessions")
