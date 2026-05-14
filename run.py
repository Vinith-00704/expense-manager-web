import os
from dotenv import load_dotenv

# Load .env FIRST — before anything else reads os.environ
# This ensures GEMINI_API_KEY and all other vars are always available,
# regardless of whether VS Code's terminal env injection is enabled.
load_dotenv(override=False)

from app import create_app

config_name = os.environ.get("FLASK_ENV", "development")
app = create_app(config_name)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=(config_name == "development"),
    )
