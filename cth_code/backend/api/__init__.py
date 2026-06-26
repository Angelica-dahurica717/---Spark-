# backend/api/__init__.py
# 创建4个Blueprint对象，供app.py注册使用
from flask import Blueprint

auth_bp     = Blueprint("auth",     __name__, url_prefix="/api/auth")
analysis_bp = Blueprint("analysis", __name__, url_prefix="/api/analysis")
rumors_bp   = Blueprint("rumors",   __name__, url_prefix="/api/rumors")
users_bp    = Blueprint("users",    __name__, url_prefix="/api/users")

from api import auth_routes, analysis, rumors, users
