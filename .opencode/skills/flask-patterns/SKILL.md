---
name: flask-patterns
description: Flask architecture standards for Python backend development. Covers App Factory pattern, Blueprint structure, SQLAlchemy models, error handling, response format, extensions setup, JWT auth, and environment configuration. Load this before writing any Flask code.
license: MIT
compatibility: opencode
---

## What I cover

Flask project structure, App Factory pattern, Blueprint routing, SQLAlchemy + Flask-Migrate, global error handlers, consistent JSON response shape, JWT authentication, environment variables, and default stack selection per project type.

## When to use me

Load this skill at the start of every backend task before writing any code. Also useful when reviewing Flask code for architectural compliance.

---

## Project Structure

Every Flask project must follow this structure exactly:

```
backend/
├── app/
│   ├── __init__.py          # App factory: create_app()
│   ├── config.py            # Config classes: DevelopmentConfig, ProductionConfig, TestingConfig
│   ├── extensions.py        # All extension instances: db, migrate, jwt, cors
│   ├── models/
│   │   ├── __init__.py      # Re-export all models for easy import
│   │   └── user.py          # One file per domain entity
│   └── routes/
│       ├── __init__.py      # register_blueprints(app) function
│       └── users.py         # One blueprint per domain
├── tests/
│   ├── conftest.py          # App fixture, test client, test DB setup
│   └── test_users.py        # One test file per route module
├── migrations/              # Flask-Migrate auto-generated, do not edit manually
├── .env.example             # All required env vars with placeholder values
├── .env                     # Actual secrets — never commit
├── requirements.txt         # Every imported package, pinned versions
└── run.py                   # Entry point: app = create_app()
```

---

## App Factory Pattern

**Always use `create_app()`. Never instantiate `Flask(__name__)` at module level.**

```python
# app/__init__.py
from flask import Flask
from .config import config
from .extensions import db, migrate, jwt, cors

def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # Register blueprints
    from .routes import register_blueprints
    register_blueprints(app)

    # Register global error handlers
    register_error_handlers(app)

    return app


def register_error_handlers(app):
    from flask import jsonify

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "details": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({"error": "Conflict", "details": str(e)}), 409

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"error": "Validation failed", "details": str(e)}), 422

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"Internal error: {e}")
        return jsonify({"error": "Internal server error"}), 500
```

```python
# run.py
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

---

## Config Classes

```python
# app/config.py
import os

class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///dev.db")

class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")  # Must be set in env

class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = 10

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
```

---

## Extensions

**Always declare extension instances here. Never import from `app/__init__.py`.**

```python
# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
```

---

## Blueprint Pattern

**One blueprint per domain. Never put all routes in a single file.**

```python
# app/routes/__init__.py
from .users import users_bp
from .auth import auth_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
```

```python
# app/routes/users.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.user import User

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

@users_bp.route("/", methods=["GET"])
@jwt_required()
def get_users():
    try:
        users = User.query.all()
        return jsonify({"data": [u.to_dict() for u in users], "message": "OK"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch users", "details": str(e)}), 500

@users_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({"data": user.to_dict(), "message": "OK"}), 200

@users_bp.route("/", methods=["POST"])
def create_user():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Validate required fields explicitly — never trust input
    required = ["email", "password", "name"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": "Validation failed", "details": f"Missing fields: {missing}"}), 422

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    try:
        user = User(email=data["email"], name=data["name"])
        user.set_password(data["password"])
        db.session.add(user)
        db.session.commit()
        return jsonify({"data": user.to_dict(), "message": "User created"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create user", "details": str(e)}), 500
```

---

## Model Pattern

```python
# app/models/user.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password: str) -> None:
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
        }
        # Never include password_hash in to_dict()

# app/models/__init__.py
from .user import User
```

---

## Auth Blueprint (JWT)

```python
# app/routes/auth.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from ..extensions import db
from ..models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password are required"}), 422

    user = User.query.filter_by(email=data["email"]).first()
    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"data": {"token": token, "user": user.to_dict()}, "message": "Login successful"}), 200

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    return jsonify({"data": user.to_dict(), "message": "OK"}), 200
```

---

## Response Format

**Always use this shape. Never return bare strings or inconsistent structures.**

```python
# Success (single object)
return jsonify({"data": obj.to_dict(), "message": "OK"}), 200

# Success (list)
return jsonify({"data": [o.to_dict() for o in items], "total": len(items), "message": "OK"}), 200

# Created
return jsonify({"data": obj.to_dict(), "message": "Created successfully"}), 201

# Validation error
return jsonify({"error": "Validation failed", "details": {"field": "reason"}}), 422

# Not found
return jsonify({"error": "Resource not found"}), 404

# Conflict
return jsonify({"error": "Email already registered"}), 409

# Server error
return jsonify({"error": "Internal server error"}), 500
```

---

## Database Selection

| Scenario | Default |
|---|---|
| PRD or user specifies DB explicitly | Use exactly what is specified |
| Prototype / local tool / low concurrency | **SQLite** (`sqlite:///dev.db`) |
| Production-grade / high concurrency / complex relations | **PostgreSQL** |

---

## Default Stack per Project Type

| Type | Packages |
|---|---|
| REST API only | `flask flask-sqlalchemy flask-migrate flask-cors` |
| REST API + Auth | add `flask-jwt-extended` |
| File uploads | add `werkzeug` (already included) |
| Background tasks | add `celery redis` |

---

## Environment Variables (.env.example)

Every project must ship this file. Never leave fields blank — use placeholder values.

```
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=change-this-in-production
DATABASE_URL=sqlite:///dev.db
CORS_ORIGINS=http://localhost:3000
JWT_SECRET_KEY=change-this-jwt-secret
```

---

## requirements.txt Rules

- Pin major versions: `flask==3.0.*`
- Always include: `flask flask-sqlalchemy flask-migrate flask-cors python-dotenv`
- Add only packages that are actually imported in the codebase
- Regenerate with `pip freeze > requirements.txt` after installing new packages

---

## Self-Verify Checklist (run mentally before every handoff)

- [ ] All imports resolvable — no missing packages, no circular imports
- [ ] `.env.example` lists every `os.environ.get(...)` call in the project
- [ ] Every endpoint has explicit error handling — zero bare `except:` blocks
- [ ] All models imported in `app/models/__init__.py`
- [ ] `requirements.txt` matches all imports
- [ ] `run.py` uses `create_app()`, never `Flask(__name__)` directly
- [ ] No hardcoded secrets, URLs, or credentials anywhere in the codebase