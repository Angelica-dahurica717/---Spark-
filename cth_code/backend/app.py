# backend/app.py
# Flask 应用主入口：创建 app 实例，注册4个 Blueprint 路由模块，配置跨域，启动服务

import sys
import os

# 把当前文件所在目录（backend/）插入 Python 模块搜索路径的最前面
# 确保 import auth、import config 等同级模块可以正常找到
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Flask：Web 框架核心类；jsonify：把 Python 字典转成 JSON HTTP 响应
from flask import Flask, jsonify
# CORS：解决前后端分离时浏览器的跨域限制
from flask_cors import CORS
# 从 api 包导入4个 Blueprint 蓝图对象
from api import auth_bp, analysis_bp, rumors_bp, users_bp

# 创建 Flask 应用实例，__name__ 让 Flask 知道模板和静态文件的根目录
app = Flask(__name__)

# 允许所有来源访问 /api/* 路径下的接口
# origins="*" 表示不限制请求来源域名，适合开发环境
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 注册蓝图：把各模块定义的路由绑定到 app 上
# auth_bp 处理 /api/auth/* 路由（登录、获取用户信息）
app.register_blueprint(auth_bp)
# analysis_bp 处理 /api/analysis/* 路由（词云、主题、趋势等分析接口）
app.register_blueprint(analysis_bp)
# rumors_bp 处理 /api/rumors/* 路由（谣言检索与分页）
app.register_blueprint(rumors_bp)
# users_bp 处理 /api/users/* 路由（用户管理，仅管理员可用）
app.register_blueprint(users_bp)


# 根路径健康检查接口，用于确认服务是否正常运行
@app.route("/")
def index():
    return jsonify({"msg": "谣言分析系统 API 服务运行中", "version": "1.0.0"})


# 全局错误处理器：捕获 404 Not Found，统一返回 JSON 格式错误信息
@app.errorhandler(404)
def not_found(e):
    return jsonify({"code": 404, "msg": "接口不存在"}), 404


# 全局错误处理器：捕获 405 Method Not Allowed（如 POST 接口被 GET 请求）
@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"code": 405, "msg": "请求方法不支持"}), 405


# 全局错误处理器：捕获未处理的服务器内部异常，str(e) 输出错误详情
@app.errorhandler(500)
def internal_error(e):
    return jsonify({"code": 500, "msg": "服务器内部错误", "detail": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print(" 谣言分析系统 Flask 后端启动")
    print(" 地址：http://127.0.0.1:5000")
    print("=" * 50)
    # host="0.0.0.0"：监听所有网卡，局域网内其他设备可访问
    # port=5000：指定端口号
    # debug=True：开启调试模式，代码修改后自动重载，同时显示详细报错信息
    app.run(host="0.0.0.0", port=5000, debug=True)
