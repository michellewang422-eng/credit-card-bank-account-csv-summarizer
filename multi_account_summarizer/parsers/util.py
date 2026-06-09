# ============================================================
# 解析器共用工具函数
# 所有 parser 共同的逻辑集中在这里，避免重复代码
# ============================================================

import csv
from datetime import datetime


def parse_amount(raw):
    # 把原始字符串金额转成浮点数，失败返回 None
    # 例："  -39.99  " → -39.99
    #     ""           → None（空字段）
    #     "N/A"        → None（非数字）
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_date(raw):
    # 把 MM/DD/YYYY 格式的字符串转成 date 对象，失败返回 None
    # 例："05/15/2025" → datetime.date(2025, 5, 15)
    #     ""           → None
    #     "2025-05-15" → None（格式不对）
    raw = raw.strip()
    try:
        return datetime.strptime(raw, "%m/%d/%Y").date()
    except ValueError:
        return None


def parse_csv(file_path, row_to_transaction):
    # 通用 CSV 解析函数，所有 parser 共用这一段开文件、循环、收集的逻辑
    # 参数：
    #   file_path          = CSV 文件路径
    #   row_to_transaction = 各 parser 提供的函数，把一行 row 转成 transaction 对象
    #                        如果这行应该跳过，返回 None
    transactions = []

    with open(file_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            transaction = row_to_transaction(row)

            # None 表示这行应该跳过（空行、无效金额、无效日期等）
            if transaction is not None:
                transactions.append(transaction)

    return transactions
