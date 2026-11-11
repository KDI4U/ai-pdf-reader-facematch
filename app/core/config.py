import os
from fastapi.middleware.cors import CORSMiddleware

# Database configuration (optional)
DATABASE_URL = os.getenv("DATABASE_URL", "")

def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
       # allow_origins=["http://localhost:4200"],  # prod me change
        allow_origins=["*"],  # prod me change
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
