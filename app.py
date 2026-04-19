from flask import Flask
from routes.auth import auth_bp
from routes.pages import pages_bp
from routes.api import api_bp
from database.db import connection_pool
from dotenv import load_dotenv

import os

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret")

# register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(pages_bp)
app.register_blueprint(api_bp)

if __name__ == "__main__":
    app.run(debug=True)