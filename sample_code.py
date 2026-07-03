"""示例代码文件 — 用于验证 AI Code Review 工具。"""

import os
import pickle


def get_user_name(user):
    """获取用户名 — 没有做空值检查。"""
    return user.name.upper()


def search_users(query):
    """搜索用户 — SQL 注入风险。"""
    sql = "SELECT * FROM users WHERE name = '" + query + "'"
    return sql


def process_items(items):
    """处理列表 — O(n²) 性能问题。"""
    result = []
    for item in items:  # 外层循环
        for other in items:  # 内层循环 — 不必要的嵌套
            if item != other:
                result.append((item, other))
    return result


def unsafe_command(filename):
    """执行命令 — 命令注入风险。"""
    os.system("cat " + filename)


def load_user_data(path):
    """加载用户数据 — 不安全的反序列化。"""
    with open(path, "rb") as f:
        return pickle.load(f)


def calculate_average(numbers):
    """计算平均值 — 空列表边界条件未处理。"""
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)  # 空列表时 ZeroDivisionError


PASSWORD = "admin123"  # 硬编码密码

x = 1
y = 2
z = 3
# 以上三个变量未使用
