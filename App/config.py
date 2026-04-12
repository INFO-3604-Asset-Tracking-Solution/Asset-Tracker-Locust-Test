from datetime import timedelta
import os

def load_config(app, overrides):
    # Load default first as a fallback
    app.config.from_object('App.default_config')

    # Check for custom config (e.g., for local overrides not committed)
    if os.path.exists(os.path.join('./App', 'custom_config.py')):
        app.config.from_object('App.custom_config')

    # Load environment variables (generic ones)
    app.config.from_prefixed_env() # For vars like FLASK_DEBUG

    # === Explicitly handle Production Database ===
    app.config['ENV'] = os.environ.get('ENV', 'DEVELOPMENT') # Get ENV variable

    if app.config['ENV'] == 'production':
        db_url = os.environ.get('POSTGRES_URL')
        db_user = os.environ.get('POSTGRES_USER')
        db_password = os.environ.get('POSTGRES_PASSWORD')
        db_name = os.environ.get('POSTGRES_DB')

        if all([db_url, db_user, db_password, db_name]):
             # Construct the PostgreSQL connection string
             # Render uses 'POSTGRES_URL' for the host, adjust if using external db
             # Ensure the driver is correct (psycopg2)
            database_uri = f"postgresql://{db_user}:{db_password}@{db_url}/{db_name}"
            app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
            print("Production database URI configured.") # Add print for debugging in logs
        else:
            print("Warning: Production ENV set but missing PostgreSQL ENV variables. Falling back to default.")
            # Fallback to default if production vars aren't fully set (shouldn't happen on Render)
            app.config.from_object('App.default_config')
    # else: # Development or other envs will use the default loaded earlier
        # print(f"Non-production ENV ('{app.config['ENV']}'), using default DB URI.")

    # === End Production Database Handling ===


    # Set other standard configs
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.config['UPLOADED_PHOTOS_DEST'] = "App/uploads" # Consider using a persistent disk on Render if uploads need to persist
    app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
    app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
    app.config["JWT_COOKIE_SECURE"] = True # Set to True for HTTPS on Render
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False # Keep False unless you implement CSRF handling
    app.config['FLASK_ADMIN_SWATCH'] = 'darkly'
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)
    app.config["JWT_REFRESH_COOKIE_NAME"] = "refresh_token"

    # Apply overrides last
    for key in overrides:
        app.config[key] = overrides[key]