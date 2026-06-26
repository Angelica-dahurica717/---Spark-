# backend/api/users.py
# >>>【用户管理接口 用户增删改查 CRUD】<<<  全部接口仅admin可访问
import re
from flask import request, jsonify
from api import users_bp
from auth import admin_required
from config import USERS

# 运行时可修改的用户表（基于 config.py 初始化）
_users = {k: dict(v, username=k) for k, v in USERS.items()}
_next_id = len(_users) + 1


def _user_public(u):
    """返回不含密码的用户信息"""
    return {
        "username": u["username"],
        "name":     u.get("name", u["username"]),
        "role":     u.get("role", "analyst"),
    }


@users_bp.route("", methods=["GET"])
@admin_required
def get_users():
    # >>>【查询全部用户列表 GET /api/users】<<<
    """获取全部用户列表"""
    return jsonify({
        "code": 200,
        "data": [_user_public(u) for u in _users.values()]
    })


@users_bp.route("", methods=["POST"])
@admin_required
def create_user():
    # >>>【新增用户 POST /api/users 用户创建】<<<
    """新增用户"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    role     = data.get("role", "analyst")
    name     = data.get("name", username)

    if not username or not password:
        return jsonify({"code": 400, "msg": "用户名和密码不能为空"}), 400
    if not re.match(r'^[A-Za-z0-9]+$', username):
        return jsonify({"code": 400, "msg": "账号只能包含英文和数字"}), 400
    if not re.match(r'^[A-Za-z0-9]+$', password):
        return jsonify({"code": 400, "msg": "密码只能包含英文和数字"}), 400
    if username in _users:
        return jsonify({"code": 400, "msg": "用户名已存在"}), 400
    if role not in ("admin", "analyst"):
        return jsonify({"code": 400, "msg": "角色只能是 admin 或 analyst"}), 400

    _users[username] = {"username": username, "password": password, "role": role, "name": name}
    return jsonify({"code": 200, "msg": "创建成功", "data": _user_public(_users[username])})


@users_bp.route("/<username>", methods=["PUT"])
@admin_required
def update_user(username):
    # >>>【编辑用户信息 PUT /api/users/<username> 用户修改】<<<
    """修改用户信息"""
    if username not in _users:
        return jsonify({"code": 404, "msg": "用户不存在"}), 404

    data = request.get_json() or {}
    user = _users[username]

    if username == "admin" and "role" in data and data["role"] != "admin":
        # >>>【root账号保护 admin角色不可修改】<<<
        return jsonify({"code": 400, "msg": "admin 的权限角色固定为管理员，无法被修改"}), 400

    if "password" in data and data["password"].strip():
        if not re.match(r'^[A-Za-z0-9]+$', data["password"].strip()):
            return jsonify({"code": 400, "msg": "密码只能包含英文和数字"}), 400
        user["password"] = data["password"].strip()
    if "name" in data:
        user["name"] = data["name"]
    if "role" in data and data["role"] in ("admin", "analyst"):
        user["role"] = data["role"]

    return jsonify({"code": 200, "msg": "修改成功", "data": _user_public(user)})


@users_bp.route("/<username>", methods=["DELETE"])
@admin_required
def delete_user(username):
    # >>>【删除用户 DELETE /api/users/<username> 用户删除】<<<
    """删除用户（不能删除自己）"""
    current = request.current_user.get("username")
    if username == current:
        return jsonify({"code": 400, "msg": "不能删除自己"}), 400
    if username == "admin":
        # >>>【禁止删除root账号 admin保护机制】<<<
        return jsonify({"code": 400, "msg": "admin 是 root 账号，禁止被删除"}), 400
    if username not in _users:
        return jsonify({"code": 404, "msg": "用户不存在"}), 404

    del _users[username]
    return jsonify({"code": 200, "msg": "删除成功"})
