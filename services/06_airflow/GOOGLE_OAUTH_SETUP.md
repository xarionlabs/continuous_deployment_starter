# Google OAuth Setup for Apache Airflow 3.0

This guide explains how to set up Google OAuth authentication for your Apache Airflow 3.0 deployment.

## Prerequisites

- Google Cloud Platform account
- Access to Google Cloud Console
- Apache Airflow 3.0 running with the configuration files in this directory

## Step 1: Create Google Cloud OAuth2 Application

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project or create a new one
3. Navigate to **APIs & Services** > **Credentials**
4. Click **+ CREATE CREDENTIALS** > **OAuth client ID**
5. If prompted, configure the OAuth consent screen first:
   - Choose **Internal** (for organization use) or **External** (for public use)
   - Fill in the required application information
   - Add your domain to authorized domains if using External
   - Add scopes: `email` and `profile`

## Step 2: Configure OAuth Client ID

1. Choose **Web application** as the application type
2. Give it a descriptive name (e.g., "Airflow OAuth")
3. Add **Authorized redirect URIs**:
   - `https://your-airflow-domain.com/oauth-authorized/google`
   - `http://localhost:8080/oauth-authorized/google` (for local development)
   
   Replace `your-airflow-domain.com` with your actual Airflow domain.

4. Click **Create**
5. Copy the **Client ID** and **Client Secret** - you'll need these for configuration

## Step 3: Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and set:
   ```env
   GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
   GOOGLE_OAUTH_DOMAIN_WHITELIST=yourdomain.com  # Optional: restrict to specific domains
   AIRFLOW_WEB_VIRTUAL_HOST=airflow.yourdomain.com
   ```

## Step 4: Set up Docker Secrets

For production deployments, create Docker secrets for sensitive information:

```bash
# Create the Google OAuth client secret
echo "your-google-client-secret" | docker secret create GOOGLE_OAUTH_CLIENT_SECRET -

# Verify the secret was created
docker secret ls
```

## Step 5: Deploy Airflow with Google OAuth

1. Build and start the services:
   ```bash
   docker-compose up --build -d
   ```

2. Check the logs to ensure OAuth is configured correctly:
   ```bash
   docker-compose logs airflow-webserver
   ```

3. Access Airflow at your configured domain or `http://localhost:8080`

## Step 6: Test Google OAuth Login

1. Navigate to your Airflow web interface
2. You should see a "Sign in with Google" button
3. Click it to authenticate with Google
4. After successful authentication, you should be logged into Airflow

## Troubleshooting

### Common Issues

1. **"Invalid redirect URI"**
   - Ensure your redirect URI in Google Cloud Console matches exactly: `https://your-domain/oauth-authorized/google`
   - Check that your domain is correctly configured

2. **"JWT token is not valid" (Known issue in Airflow 3.0.2)**
   - This is a known issue with Airflow 3.0.2 and Google OAuth
   - Monitor the [Airflow GitHub issue #52226](https://github.com/apache/airflow/issues/52226) for updates
   - Consider using environment variables instead of secrets temporarily

3. **"Unauthorized domain"**
   - Add your domain to the authorized domains in the OAuth consent screen
   - Ensure your domain whitelist is configured correctly

4. **Users can't access after login**
   - Check the `AUTH_USER_REGISTRATION_ROLE` in `webserver_config.py`
   - Verify role mappings in `AUTH_ROLES_MAPPING`
   - Users may need to be manually assigned roles in the Airflow UI

### Debug Steps

1. Enable debug logging by checking the webserver logs:
   ```bash
   docker-compose logs airflow-webserver | grep -i oauth
   ```

2. Verify environment variables are loaded:
   ```bash
   docker-compose exec airflow-webserver env | grep GOOGLE_OAUTH
   ```

3. Check if the webserver_config.py is properly mounted:
   ```bash
   docker-compose exec airflow-webserver cat /opt/airflow/webserver_config.py
   ```

## Security Considerations

1. **Domain Restriction**: Use `GOOGLE_OAUTH_DOMAIN_WHITELIST` to restrict access to specific email domains
2. **HTTPS**: Always use HTTPS in production for OAuth redirects
3. **Secrets Management**: Use Docker secrets or external secret management for the client secret
4. **Role Management**: Regularly review user roles and permissions in Airflow

## Role Management

After users log in via Google OAuth:

1. Go to **Security** > **List Users** in the Airflow UI
2. Find the user and click **Edit**
3. Assign appropriate roles based on their responsibilities:
   - **Viewer**: Read-only access
   - **User**: Can trigger DAGs and view logs  
   - **Op**: Can perform operational tasks
   - **Admin**: Full administrative access

## Additional Configuration

### Custom User Roles

You can customize role mappings in `webserver_config.py`:

```python
AUTH_ROLES_MAPPING = {
    "Viewer": ["Viewer"],
    "User": ["User"], 
    "Op": ["Op"],
    "Admin": ["Admin"],
    # Add custom mappings based on Google Groups or other attributes
}
```

### Session Configuration

Adjust session timeout in `webserver_config.py`:

```python
PERMANENT_SESSION_LIFETIME = 3600  # 1 hour in seconds
```

## References

- [Apache Airflow FAB Authentication Documentation](https://airflow.apache.org/docs/apache-airflow-providers-fab/stable/auth-manager/webserver-authentication.html)
- [Google OAuth2 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Flask-AppBuilder OAuth Documentation](https://flask-appbuilder.readthedocs.io/en/latest/security.html#oauth-authentication)