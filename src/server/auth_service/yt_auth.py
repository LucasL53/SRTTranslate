
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

from ..file_service.main import app

config_data = Config(".env")

oauth = OAuth(config_data)
oauth.register(
    name='google',
    client_id=config_data("GOOGLE_CLIENT_ID"),
    client_secret=config_data("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        # Scope includes YouTube Data API and basic profile info
        'scope': 'openid email profile https://www.googleapis.com/auth/youtube.force-ssl'
    }
)

# Endpoint to initiate the OAuth flow
@app.get("/auth/login")
async def login(request: Request):
    """
    Redirects the user to Google OAuth 2.0 consent screen.
    """
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

# Endpoint to handle the OAuth callback
@app.get("/auth/callback")
async def auth_callback(request: Request):
    """
    Handles the callback from Google after user consent, exchanges the
    authorization code for an access token, and retrieves user info.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth authorization failed: {str(e)}")

    # Parse the ID token to get user info
    try:
        user = await oauth.google.parse_id_token(request, token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse user info: {str(e)}")

    # At this point you have a valid token and user information.
    # You can now create your own session, issue your own token, etc.
    # For simplicity, we return the token and user info directly.
    return JSONResponse({
        "access_token": token.get("access_token"),
        "refresh_token": token.get("refresh_token"),
        "expires_in": token.get("expires_in"),
        "user": user
    })