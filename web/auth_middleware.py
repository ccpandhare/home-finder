"""
Central Auth Middleware for Home Finder
Checks authentication against auth.chinmaypandhare.uk
"""

import os
from functools import wraps

import httpx
from flask import request, redirect, abort, g

AUTH_SERVICE = os.getenv("AUTH_SERVICE_URL", "https://auth.chinmaypandhare.uk")
SERVICE_NAME = "homefinder"
COOKIE_NAME = "ccp_auth_token"


def require_auth(f):
    """
    Decorator to require authentication for a route.
    Redirects to auth service if not authenticated.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get(COOKIE_NAME)
        
        if not token:
            return redirect_to_login()
        
        # Verify with auth service
        try:
            response = httpx.get(
                f"{AUTH_SERVICE}/api/verify",
                params={"service": SERVICE_NAME},
                cookies={COOKIE_NAME: token},
                timeout=10,
            )
            data = response.json()
            
            if not data.get("valid"):
                reason = data.get("reason", "unknown")
                if reason == "no_access":
                    return abort(403, f"You don't have access to Home Finder. Contact admin.")
                return redirect_to_login()
            
            # Store user info in g
            g.user = data.get("username")
            g.is_admin = data.get("isAdmin", False)
            
        except Exception as e:
            print(f"Auth verification failed: {e}")
            return redirect_to_login()
        
        return f(*args, **kwargs)
    
    return decorated


def redirect_to_login():
    """Redirect to auth service login page."""
    from urllib.parse import quote
    current_url = request.url
    encoded_redirect = quote(current_url, safe='')
    login_url = f"{AUTH_SERVICE}/login?service={SERVICE_NAME}&redirect={encoded_redirect}"
    print(f"[AUTH] Redirecting to: {login_url}")
    return redirect(login_url)


def get_current_user():
    """Get current user from g, or None if not authenticated."""
    return getattr(g, 'user', None)


def is_admin():
    """Check if current user is admin."""
    return getattr(g, 'is_admin', False)
