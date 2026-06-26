# backend/api/auth_routes.py
# >>>【登录注册路由 身份认证接口】<<<
# 认证相关 HTTP 接口：登录 POST /api/auth/login、注册 POST /api/auth/register、获取当前用户信息 GET /api/auth/me

# request：获取 HTTP 请求数据；jsonify：把字典序列化为 JSON 响应
from flask import request, jsonify
# auth_bp：认证模块的 Blueprint 蓝图对象（在 api/__init__.py 中定义）
from api import auth_bp
# generate_token：生成 JWT；decode_token：解析 JWT
from auth import generate_token
# 从用户管理模块导入运行时维护的用户字典（包含新增/修改的用户）
from api.users import _users as USERS


# >>>【用户登录接口 POST /api/auth/login】<<<
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    用户登录接口
    请求体（JSON）：{"username": "xxx", "password": "xxx"}
    成功响应：{"code": 200, "data": {"token": "...", "username": "...", "role": "...", "name": "..."}}
    失败响应：{"code": 401, "msg": "用户名或密码错误"}
    """
    # get_json()：解析请求体中的 JSON 数据，or {} 防止请求体为空时返回 None
    data = request.get_json() or {}
    # .get() 取字段值，默认为空字符串；.strip() 去除两端空白字符
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    # 在用户字典中查找该用户名对应的用户信息
    user = USERS.get(username)
    # 用户不存在 或 密码不匹配，返回 401 未授权
    if not user or user["password"] != password:
        return jsonify({"code": 401, "msg": "用户名或密码错误"}), 401

    # 验证通过：生成携带用户名和角色信息的 JWT Token
    token = generate_token(username, user["role"])
    # 返回 Token 和用户基本信息，前端存入 localStorage 用于后续请求鉴权
    return jsonify({
        "code": 200,
        "msg": "登录成功",
        "data": {
            "token": token,
            "username": username,
            "role": user["role"],   # "admin" 或 "viewer"
            "name": user["name"]    # 显示名称
        }
    })


# >>>【获取当前登录用户信息 GET /api/auth/me】<<<
@auth_bp.route("/me", methods=["GET"])
def me():
    """
    获取当前登录用户信息接口
    前端在请求头中携带 Authorization: Bearer <token>
    成功响应：{"code": 200, "data": {"username": "...", "role": "...", "name": "..."}}
    """
    from auth import decode_token
    # 从请求头读取 Authorization 字段
    auth_header = request.headers.get("Authorization", "")
    # 检查 Token 格式，必须以 "Bearer " 开头
    if not auth_header.startswith("Bearer "):
        return jsonify({"code": 401, "msg": "未登录"}), 401
    # [7:] 截取 "Bearer " 之后的部分，得到实际 Token 字符串
    token = auth_header[7:]
    try:
        # 解析 Token，验证签名和过期时间
        payload = decode_token(token)
        username = payload["username"]
        # 从运行时用户字典中获取用户详细信息（如显示名称）
        user = USERS.get(username, {})
        return jsonify({
            "code": 200,
            "data": {
                "username": username,
                "role": payload["role"],              # 从 Token payload 中读取角色
                "name": user.get("name", username)    # 优先用存储的名称，否则用用户名
            }
        })
    except Exception:
        # Token 解析失败（过期或签名无效），统一返回 401
        return jsonify({"code": 401, "msg": "Token无效"}), 401

# >>>【用户注册接口 POST /api/auth/register 账号检测 正则防注入】<<<
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    用户注册接口
    请求体（JSON）：{"username": "xxx", "password": "xxx", "name": "xxx"}
    """
    import re
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    name = data.get("name", username).strip()
    
    if not username or not password:
        return jsonify({"code": 400, "msg": "用户名和密码不能为空"}), 400
    if not re.match(r'^[A-Za-z0-9]+$', username):
        # >>>【正则防注入 正则校验 账号合法性检查】<<<
        return jsonify({"code": 400, "msg": "账号只能包含英文和数字"}), 400
    if not re.match(r'^[A-Za-z0-9]+$', password):
        return jsonify({"code": 400, "msg": "密码只能包含英文和数字"}), 400
    if username in USERS:
        return jsonify({"code": 400, "msg": "用户名已存在"}), 400
        
    # >>>【默认角色 注册用户默认为普通分析员】<<<
    USERS[username] = {
        "username": username,
        "password": password,
        "role": "analyst",  # 默认注册为普通研究员
        "name": name
    }
    
    return jsonify({"code": 200, "msg": "注册成功"})
