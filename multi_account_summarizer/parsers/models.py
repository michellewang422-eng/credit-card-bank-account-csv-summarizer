# ============================================================
# 数据模板：定义信用卡交易和银行账户交易的数据结构
# ============================================================

# 导入 dataclass 装饰器
# dataclass 的作用：自动帮类生成 __init__ 方法，省去手动写赋值代码
# 例：没有 dataclass 时需要自己写：
#     def __init__(self, date, description, ...):
#         self.date = date
#         self.description = description
#         ...
# 加了 @dataclass 后，只需声明字段名和类型，Python 自动生成上面的代码
from dataclasses import dataclass

# 导入 date 类型，用于声明日期字段的类型
# 例：date 对象长这样：datetime.date(2025, 5, 15)，表示 2025年5月15日
from datetime import date


# @dataclass 是一个装饰器，写在类定义上方，告诉 Python 自动生成初始化方法
# 这样创建对象时可以直接传参：
# 例：CreditTransaction(date=..., description="AMAZON", category="Shopping", ...)
@dataclass
class CreditTransaction:
    # 以下每一行声明一个字段，格式是：字段名: 类型
    # Python 用这些声明自动生成 __init__，不需要手写

    date: date          # 交易日期，例：datetime.date(2025, 5, 15)
    description: str    # 商家名称，例："WHOLE FOODS #123"
    category: str       # 消费分类，例："Groceries"、"Dining"、"Uncategorized"
    amount: float       # 金额：负数 = 消费支出（例：-39.99），正数 = 还款/退款（例：200.0）
    account_name: str   # 信用卡名称，例："Chase Sapphire"、"Amex Gold"
    account_last4: str  # 卡号后四位，例："9809"（用字符串存，避免丢失前导零）


# BankTransaction 和 CreditTransaction 结构相似，但有两点不同：
#   1. 没有 category 字段（银行账户交易没有消费分类）
#   2. 多了 balance 字段（银行账户记录每笔交易后的余额，信用卡不记录）
@dataclass
class BankTransaction:
    date: date          # 交易日期，例：datetime.date(2025, 5, 15)
    description: str    # 交易描述，例："SAFEWAY #456"、"PAYROLL DEPOSIT"
    amount: float       # 金额：负数 = 支出/取款（例：-52.3），正数 = 存款/收入（例：1200.0）
    balance: float      # 该笔交易后的账户余额，例：3500.0（Wells Fargo 无此数据时固定为 0.0）
    account_name: str   # 银行账户名称，例："Chase Checking"、"Wells Fargo Checking"
    account_last4: str  # 账户后四位，例："6789"（用字符串存，避免丢失前导零）
