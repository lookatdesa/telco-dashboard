"""
Simple Authentication System
========================================
"""

import streamlit as st
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# ============================================================================
# CONFIGURATION
# ============================================================================

USERNAME = "kearney_user"
PASSWORD_HASH = "d082eec54eb76af5dd25400494fadba55edeb842d2acb2fabe268527bfe2517f" 
SESSION_TIMEOUT_HOURS = 24
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME_MINUTES = 15

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password with SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hash_value: str) -> bool:
    """Verify password against hash."""
    return hmac.compare_digest(hash_password(password), hash_value)

def is_session_valid() -> bool:
    """Check if current session is valid."""
    if not st.session_state.get("authenticated", False):
        return False
    
    login_time = st.session_state.get("login_timestamp")
    if not login_time:
        return False
    
    try:
        login_datetime = datetime.fromisoformat(login_time)
        expire_time = login_datetime + timedelta(hours=SESSION_TIMEOUT_HOURS)
        return datetime.now() < expire_time
    except (ValueError, TypeError):
        return False

def is_locked_out() -> bool:
    """Check if user is locked out."""
    lockout_until = st.session_state.get("lockout_until")
    if not lockout_until:
        return False
    
    try:
        lockout_datetime = datetime.fromisoformat(lockout_until)
        return datetime.now() < lockout_datetime
    except (ValueError, TypeError):
        return False

def attempt_login(username: str, password: str) -> Dict[str, Any]:
    """Attempt user login."""
    if is_locked_out():
        remaining = get_lockout_remaining()
        return {"success": False, "message": f"Account locked. Try again in {remaining} minutes."}
    
    attempts = st.session_state.get("login_attempts", 0)
    
    if username == USERNAME and verify_password(password, PASSWORD_HASH):
        # Success
        st.session_state["authenticated"] = True
        st.session_state["username"] = username
        st.session_state["login_timestamp"] = datetime.now().isoformat()
        st.session_state["login_attempts"] = 0
        if "lockout_until" in st.session_state:
            del st.session_state["lockout_until"]
        return {"success": True, "message": f"Welcome, {username}!"}
    else:
        # Failed
        attempts += 1
        st.session_state["login_attempts"] = attempts
        
        if attempts >= MAX_LOGIN_ATTEMPTS:
            lockout_until = datetime.now() + timedelta(minutes=LOCKOUT_TIME_MINUTES)
            st.session_state["lockout_until"] = lockout_until.isoformat()
            return {"success": False, "message": f"Too many failed attempts. Locked for {LOCKOUT_TIME_MINUTES} minutes."}
        else:
            remaining = MAX_LOGIN_ATTEMPTS - attempts
            return {"success": False, "message": f"Invalid credentials. {remaining} attempts remaining."}

def get_lockout_remaining() -> int:
    """Get remaining lockout time in minutes."""
    if not is_locked_out():
        return 0
    
    lockout_until = st.session_state.get("lockout_until")
    try:
        lockout_datetime = datetime.fromisoformat(lockout_until)
        remaining = lockout_datetime - datetime.now()
        return max(0, int(remaining.total_seconds() / 60))
    except (ValueError, TypeError):
        return 0

def logout_user():
    """Logout current user."""
    keys_to_clear = ["authenticated", "username", "login_timestamp", "login_attempts", "lockout_until"]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def get_current_user() -> Optional[str]:
    """Get current authenticated user."""
    if is_session_valid():
        return st.session_state.get("username")
    return None

# ============================================================================
# MAIN AUTHENTICATION CHECK
# ============================================================================

def require_authentication() -> bool:
    """
    Main authentication function. Call at the start of each page.
    Returns True if authenticated, shows login page if not.
    """
    if is_session_valid():
        return True
    
    # Show login page
    show_login_page()
    return False

def show_login_page():
    """Display login page."""
    # Hide sidebar during login
    st.markdown("""
        <style>
        .css-1d391kg {display: none;}
        .css-1rs6os {display: none;}
        .css-17ziqus {display: none;}
        section[data-testid="stSidebar"] {display: none;}
        </style>
    """, unsafe_allow_html=True)
    
    # Custom CSS
    st.markdown("""
        <style>
        .login-container {
            max-width: 450px;
            margin: 3rem auto;
            padding: 2rem;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .login-title {
            text-align: center;
            color: #2c3e50;
            margin-bottom: 1.5rem;
            font-size: 2.2rem;
            font-weight: 600;
        }
        .login-subtitle {
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 2rem;
        }
        .stButton > button {
            width: 100%;
            background-color: #3498db;
            color: white;
            border: none;
            padding: 0.6rem 1rem;
            border-radius: 5px;
            font-weight: 600;
        }
        .stButton > button:hover {
            background-color: #2980b9;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.markdown("<h1 class='login-title'>🏠 Contract Management</h1>", unsafe_allow_html=True)
    st.markdown("<p class='login-subtitle'>Strategic Procurement Intelligence Dashboard</p>", unsafe_allow_html=True)
    
    # Check lockout
    if is_locked_out():
        remaining = get_lockout_remaining()
        st.error(f"🔒 Account locked. Try again in {remaining} minutes.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()
    
    # Login form
    with st.form("login_form", clear_on_submit=True):
        st.markdown("### 🔐 Please Sign In")
        
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        login_button = st.form_submit_button("🚀 Sign In")
        
        if login_button:
            if not username or not password:
                st.error("⚠️ Please enter both username and password")
            else:
                with st.spinner("🔄 Authenticating..."):
                    result = attempt_login(username, password)
                
                if result["success"]:
                    st.success(result["message"])
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ {result['message']}")
    
    # Help section
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #7f8c8d; font-size: 0.9rem;'>
            <p>🛡️ Secure access • Session expires after 24 hours</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

def show_user_info_sidebar():
    """Show user info in sidebar."""
    if not is_session_valid():
        return
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 👤 User Session")
        
        username = st.session_state.get("username", "Unknown")
        st.success(f"**{username}**")
        
        # Logout button
        if st.button("🚪 Logout", key="logout_btn"):
            logout_user()
            st.rerun()
        
        st.markdown("---")