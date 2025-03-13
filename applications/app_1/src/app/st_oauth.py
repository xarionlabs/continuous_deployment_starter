import os
import streamlit as st

from streamlit.runtime.secrets import secrets_singleton


def setup():
    virtual_host = os.getenv("VIRTUAL_HOST", "localhost:8080")
    protocol = "http" if "localhost" in virtual_host else "https"
    redirect_uri = f"{protocol}://{virtual_host}/oauth2callback"

    oauth_client_id = os.getenv("STREAMLIT_OAUTH_CLIENT_ID", None)
    oauth_client_secret = os.getenv("STREAMLIT_OAUTH_CLIENT_SECRET", None)
    oauth_cookie_secret = os.getenv("STREAMLIT_OAUTH_COOKIE_SECRET", None)

    assert oauth_client_id, "STREAMLIT_OAUTH_CLIENT_ID must be set either in the environment or in the Github Secrets of the environment"
    assert oauth_client_secret, "STREAMLIT_OAUTH_CLIENT_SECRET must be set either in the environment or in the Github Secrets of the environment"
    assert oauth_cookie_secret, "STREAMLIT_OAUTH_COOKIE_SECRET must be set either in the environment or in the Github Secrets of the environment"

    secrets_singleton._secrets = {"auth":
                                      {"redirect_uri": redirect_uri,
                                       "client_id": oauth_client_id,
                                       "client_secret": oauth_client_secret,
                                       "cookie_secret": oauth_cookie_secret,
                                       "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration"}
                                  }
