# backend/auth.py
# >>>【JWT身份认证核心模块 登录鉴权 Token校验】<<<
# 提供：① 生成 Token  ② 解析验证 Token  ③ 两个装饰器（普通登录保护 / 管理员保护）

import jwt                    
import datetime               
from functools import wraps
from flask import request, jsonify
from config import JWT_SECRET, JWT_EXPIRE_HOURS, USERS


def generate_token(username: str, role: str) -> str:
    # >>>【生成JWT Token 登录成功后签发凭证】<<<
    """
    生成 JWT Token
    :param username: 用户名，写入 payload
    :param role: 用户角色（admin/viewer），写入 payload
    :return: 编码后的 JWT 字符串
    """
    payload = {
        "username": username,   # 自定义字段：用户名
        "role": role,           # 自定义字段：角色
        # exp 是 JWT 标准字段，表示过期时间戳
        # utcnow() 取当前 UTC 时间，加上配置的小时数得到过期时刻
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRE_HOURS)
    }
    # jwt.encode：用 HS256 对称加密算法和密钥对 payload 签名，返回 JWT 字符串
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    # >>>【JWT Token解析验证 签名校验 过期检查】<<<
    """
    解析并验证 JWT Token
    :param token: 前端传来的 JWT 字符串
    :return: 解码后的 payload 字典
    :raises jwt.ExpiredSignatureError: Token 已过期
    :raises jwt.InvalidTokenError: Token 签名无效或格式错误
    """
    # jwt.decode 会自动验证签名和过期时间，验证失败则抛出异常
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])


def login_required(f):
    # >>>【login_required装饰器 登录拦截 接口保护】<<<
    """
    装饰器：保护需要登录才能访问的接口
    用法：在路由函数上加 @login_required
    工作流程：
      1. 从请求头 Authorization 中提取 Bearer Token
      2. 调用 decode_token 验证签名和有效期
      3. 验证通过则把 payload 挂载到 request.current_user，继续执行原函数
      4. 验证失败则直接返回 401 错误，不执行原函数
    """
    @wraps(f)  # 保留原函数的 __name__、__doc__ 等属性，避免装饰后函数名变成 "decorated"
    def decorated(*args, **kwargs):
        # 从 HTTP 请求头读取 Authorization 字段，格式为 "Bearer <token>"
        auth_header = request.headers.get("Authorization", "")
        # 检查前缀是否为 "Bearer "，不符合格式直接拒绝
        if not auth_header.startswith("Bearer "):
            return jsonify({"code": 401, "msg": "未登录，请先登录"}), 401
        # 截取 "Bearer " 之后的7个字符后的部分，即实际 Token 字符串
        token = auth_header[7:]
        try:
            payload = decode_token(token)
            # 把解析结果挂载到 request 对象，后续接口函数可直接读取当前用户信息
            request.current_user = payload
        except jwt.ExpiredSignatureError:
            # Token 的 exp 字段对应的时间已过期
            return jsonify({"code": 401, "msg": "Token已过期，请重新登录"}), 401
        except jwt.InvalidTokenError:
            # 签名不匹配或 Token 格式损坏
            return jsonify({"code": 401, "msg": "无效的Token"}), 401
        # 验证通过，调用原始路由函数
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    # >>>【admin_required装饰器 管理员权限拦截 角色校验】<<<
    """
    装饰器：保护仅管理员可访问的接口（在 login_required 基础上再校验角色）
    工作流程：
      1. 先走 login_required 的完整 Token 验证流程
      2. 验证通过后检查 role 字段是否为 "admin"
      3. 非管理员返回 403 Forbidden
    """
    @wraps(f)
    @login_required  # 先套 login_required，确保已登录再判断角色
    def decorated(*args, **kwargs):
        # request.current_user 由 login_required 写入，此处直接读取 role 字段
        if request.current_user.get("role") != "admin":
            return jsonify({"code": 403, "msg": "权限不足，需要管理员权限"}), 403
        return f(*args, **kwargs)
    return decorated
