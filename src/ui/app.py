"""
Streamlit Chat UI for RBAC Policy Engine.
"""

import streamlit as st
import requests
import json
import os
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="RBAC Policy Engine",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Clean light theme with proper contrast
st.markdown("""
<style>
    /* Force light mode background */
    .stApp {
        background-color: #FFFFFF !important;
    }
    
    /* Main content area */
    .main .block-container {
        background-color: #FFFFFF !important;
        color: #262730 !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #F8F9FA !important;
    }
    [data-testid="stSidebar"] * {
        color: #262730 !important;
    }
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: #262730 !important;
    }
    
    /* Sidebar buttons */
    [data-testid="stSidebar"] button {
        background-color: #FFFFFF !important;
        color: #262730 !important;
        border: 1px solid #DEE2E6 !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #E9ECEF !important;
        border-color: #FF6B6B !important;
    }
    
    /* Chat messages */
    .stChatMessage {
        background-color: #F8F9FA !important;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
    }
    .stChatMessage * {
        color: #262730 !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #262730 !important;
    }
    
    /* All text elements */
    p, span, div, label, li {
        color: #262730 !important;
    }
    
    /* Info/success/warning boxes */
    .stAlert {
        background-color: #E3F2FD !important;
        color: #262730 !important;
    }
    .stAlert * {
        color: #262730 !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #F8F9FA !important;
        color: #262730 !important;
    }
    .streamlit-expanderContent {
        background-color: #FFFFFF !important;
        color: #262730 !important;
    }
    
    /* Code blocks and inline code - light background for visibility */
    .stCodeBlock, pre {
        background-color: #F1F3F4 !important;
        color: #262730 !important;
        border: 1px solid #DEE2E6 !important;
        border-radius: 6px !important;
    }
    
    /* Inline code styling */
    code {
        background-color: #E8F4FC !important;
        color: #0066CC !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-weight: 500 !important;
    }
    
    /* JSON viewer - light theme */
    .stJson {
        background-color: #F8F9FA !important;
        border: 1px solid #DEE2E6 !important;
        border-radius: 6px !important;
    }
    .stJson * {
        color: #262730 !important;
    }
    
    /* Chat input */
    .stChatInput input, .stChatInput textarea {
        background-color: #FFFFFF !important;
        color: #262730 !important;
        border: 2px solid #DEE2E6 !important;
    }
    
    /* Markdown in sidebar */
    [data-testid="stSidebar"] .stMarkdown {
        color: #262730 !important;
    }
    
    /* Column dividers */
    [data-testid="column"] {
        background-color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "policy" not in st.session_state:
        st.session_state.policy = None
    if "validation_status" not in st.session_state:
        st.session_state.validation_status = None


def create_session():
    """Create a new API session."""
    try:
        response = requests.post(f"{API_URL}/api/sessions")
        if response.status_code == 200:
            data = response.json()
            st.session_state.session_id = data["session_id"]
            st.session_state.messages = []
            st.session_state.policy = None
            return True
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot connect to API server. Make sure to run `make run-api` first.")
        return False
    except Exception as e:
        st.error(f"Error creating session: {e}")
        return False


def send_message(message: str):
    """Send a message to the API and get a response."""
    try:
        response = requests.post(
            f"{API_URL}/api/chat",
            json={
                "message": message,
                "session_id": st.session_state.session_id
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.session_id = data.get("session_id", st.session_state.session_id)
            st.session_state.policy = data.get("policy")
            return data
        else:
            return {"type": "error", "message": f"API Error: {response.text}"}
    except requests.exceptions.ConnectionError:
        return {"type": "error", "message": "Cannot connect to API server. Make sure it's running."}
    except Exception as e:
        return {"type": "error", "message": str(e)}


def validate_policy():
    """Validate the current policy."""
    if not st.session_state.session_id:
        return None
    
    try:
        response = requests.post(f"{API_URL}/api/policy/validate/{st.session_state.session_id}")
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def export_policy():
    """Export the policy to files."""
    if not st.session_state.session_id:
        return None
    
    try:
        response = requests.post(f"{API_URL}/api/policy/export/{st.session_state.session_id}")
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def render_sidebar():
    """Render the sidebar with controls and info."""
    with st.sidebar:
        st.markdown("# 🔐 RBAC Policy Engine")
        st.markdown("---")
        
        # Session info
        if st.session_state.session_id:
            st.markdown(f"**Session:** `{st.session_state.session_id[:8]}...`")
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 New Session", use_container_width=True):
                if create_session():
                    st.rerun()
        with col2:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        st.markdown("---")
        
        # Validation
        st.markdown("### 📋 Validation")
        if st.button("✅ Validate Policy", use_container_width=True):
            result = validate_policy()
            if result:
                st.session_state.validation_status = result
                if result.get("is_valid"):
                    st.success("Policy is valid!")
                else:
                    st.error("Policy has issues")
        
        if st.session_state.validation_status:
            report = st.session_state.validation_status.get("validation_report", {})
            errors = report.get("error_count", 0)
            warnings = report.get("warning_count", 0)
            st.markdown(f"- Errors: **{errors}**")
            st.markdown(f"- Warnings: **{warnings}**")
        
        st.markdown("---")
        
        # Export
        st.markdown("### 📦 Export")
        if st.button("💾 Export Policy", use_container_width=True):
            result = export_policy()
            if result:
                st.success(f"Exported to `output/` folder")
        
        st.markdown("---")
        
        # Quick commands
        st.markdown("### ⚡ Quick Commands")
        quick_commands = [
            "list roles",
            "list resources",
            "list permissions",
            "show policy",
            "validate",
            "help"
        ]
        
        for cmd in quick_commands:
            if st.button(cmd, key=f"cmd_{cmd}", use_container_width=True):
                st.session_state.quick_command = cmd
                st.rerun()
        
        st.markdown("---")
        
        # Help
        with st.expander("💡 Tips"):
            st.markdown("""
            **Example Commands:**
            - "Admins can do everything"
            - "Viewers can only read invoices"
            - "Deny delete to guests"
            - "Allow operators to edit orders in production"
            
            **Context Conditions:**
            - environment: production, staging
            - time_of_day: business_hours
            - mfa_verified: true/false
            """)


def render_policy_preview():
    """Render the policy preview panel."""
    st.markdown("### 📄 Policy Preview")
    
    if st.session_state.policy:
        policy = st.session_state.policy
        
        # Policy header
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**{policy.get('name', 'Untitled Policy')}**")
        with col2:
            default = policy.get('default_decision', 'DENY')
            color = "🟢" if default == "ALLOW" else "🔴"
            st.markdown(f"Default: {color} {default}")
        
        # Rules
        rules = policy.get('rules', [])
        if rules:
            st.markdown(f"**Rules ({len(rules)}):**")
            
            for rule in rules:
                effect = rule.get('effect', 'ALLOW')
                effect_color = "🟢" if effect == "ALLOW" else "🔴"
                
                with st.expander(f"{effect_color} {rule.get('name', 'Unnamed Rule')}", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Roles:**")
                        st.code(", ".join(rule.get('roles', ['*'])) or "*")
                        
                        st.markdown("**Resources:**")
                        st.code(", ".join(rule.get('resources', ['*'])) or "*")
                    
                    with col2:
                        st.markdown("**Permissions:**")
                        st.code(", ".join(rule.get('permissions', ['*'])) or "*")
                        
                        if rule.get('conditions'):
                            st.markdown("**Conditions:**")
                            st.json(rule.get('conditions'))
        else:
            st.info("No rules defined yet. Start chatting to create rules!")
        
        # Raw JSON view
        with st.expander("📝 Raw JSON"):
            st.json(policy)
    else:
        st.info("No policy yet. Start chatting to create one!")


def render_chat():
    """Render the main chat interface."""
    st.markdown("### 💬 Chat")
    
    # Display messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Check for quick command
    if "quick_command" in st.session_state and st.session_state.quick_command:
        prompt = st.session_state.quick_command
        st.session_state.quick_command = None
    else:
        prompt = st.chat_input("Describe your access rule...")
    
    if prompt:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = send_message(prompt)
            
            message = response.get("message", "I couldn't process that request.")
            st.markdown(message)
            
            # Show suggestions if any
            suggestions = response.get("suggestions", [])
            if suggestions:
                st.markdown("**Suggestions:**")
                for sug in suggestions:
                    st.markdown(f"- {sug}")
        
        # Add assistant message
        st.session_state.messages.append({"role": "assistant", "content": message})
        
        st.rerun()


def main():
    """Main application entry point."""
    init_session_state()
    
    # Create initial session if needed
    if not st.session_state.session_id:
        create_session()
    
    # Render sidebar
    render_sidebar()
    
    # Main content
    col1, col2 = st.columns([3, 2])
    
    with col1:
        render_chat()
    
    with col2:
        render_policy_preview()


if __name__ == "__main__":
    main()
