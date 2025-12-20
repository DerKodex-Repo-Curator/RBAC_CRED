"""
Session Manager - Manages conversation sessions and persistence.
"""

import json
import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path


class SessionManager:
    """
    Manages conversation sessions with persistence.
    Allows recovery of sessions after restart.
    """
    
    SESSIONS_DIR = "data/sessions"
    
    def __init__(self, sessions_dir: str = SESSIONS_DIR):
        self.sessions_dir = sessions_dir
        Path(sessions_dir).mkdir(parents=True, exist_ok=True)
        
        # In-memory session store
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        # Load existing sessions
        self._load_sessions()
    
    def _load_sessions(self) -> None:
        """Load all sessions from disk."""
        if not os.path.exists(self.sessions_dir):
            return
        
        for filename in os.listdir(self.sessions_dir):
            if filename.endswith(".json"):
                session_id = filename[:-5]
                try:
                    with open(os.path.join(self.sessions_dir, filename), 'r') as f:
                        self._sessions[session_id] = json.load(f)
                except Exception as e:
                    print(f"Warning: Could not load session {session_id}: {e}")
    
    def _save_session(self, session_id: str) -> bool:
        """Save a session to disk."""
        if session_id not in self._sessions:
            return False
        
        try:
            filepath = os.path.join(self.sessions_dir, f"{session_id}.json")
            with open(filepath, 'w') as f:
                json.dump(self._sessions[session_id], f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Warning: Could not save session {session_id}: {e}")
            return False
    
    def create_session(self, user_id: Optional[str] = None) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        
        self._sessions[session_id] = {
            "id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "conversation_history": [],
            "policy": None,
            "metadata": {}
        }
        
        self._save_session(session_id)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def update_session(
        self,
        session_id: str,
        conversation_history: Optional[List[Dict]] = None,
        policy: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Update a session's data."""
        if session_id not in self._sessions:
            return False
        
        session = self._sessions[session_id]
        session["updated_at"] = datetime.utcnow().isoformat()
        
        if conversation_history is not None:
            session["conversation_history"] = conversation_history
        
        if policy is not None:
            session["policy"] = policy
        
        if metadata is not None:
            session["metadata"].update(metadata)
        
        return self._save_session(session_id)
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> bool:
        """Add a message to a session's conversation history."""
        if session_id not in self._sessions:
            return False
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._sessions[session_id]["conversation_history"].append(message)
        self._sessions[session_id]["updated_at"] = datetime.utcnow().isoformat()
        
        return self._save_session(session_id)
    
    def save_policy(self, session_id: str, policy: Dict) -> bool:
        """Save a policy to a session."""
        return self.update_session(session_id, policy=policy)
    
    def get_policy(self, session_id: str) -> Optional[Dict]:
        """Get the policy from a session."""
        session = self.get_session(session_id)
        if session:
            return session.get("policy")
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id not in self._sessions:
            return False
        
        del self._sessions[session_id]
        
        filepath = os.path.join(self.sessions_dir, f"{session_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return True
    
    def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by user."""
        sessions = []
        for session_id, session in self._sessions.items():
            if user_id is None or session.get("user_id") == user_id:
                sessions.append({
                    "id": session_id,
                    "user_id": session.get("user_id"),
                    "created_at": session.get("created_at"),
                    "updated_at": session.get("updated_at"),
                    "message_count": len(session.get("conversation_history", [])),
                    "has_policy": session.get("policy") is not None
                })
        
        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return sessions
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Delete sessions older than max_age_hours. Returns count deleted."""
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        deleted = 0
        
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            session = self._sessions[session_id]
            updated_at = session.get("updated_at", "")
            
            try:
                session_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if session_time < cutoff:
                    self.delete_session(session_id)
                    deleted += 1
            except ValueError:
                continue
        
        return deleted
