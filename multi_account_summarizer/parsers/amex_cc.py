# ============================================================
# Amex 信用卡 CSV 解析器
# 列名：Date, Description, Amount, Extended Details, ..., Category
# 金额规则：正数 = 支出，负数 = 还款/退款（和 Chase 相反！）
# 处理方式：读取后取反，统一成"负数=支出，正数=还款"
# ============================================================

from .models import CreditTransaction
from .util import parse_csv, parse_amount, parse_date


def parse(file_path, account_name, account_last4):

    def row_to_transaction(row):
        # 金额：⚠️ Amex 和 Chase 方向相反，取反统一格式
        # 例：Amex 消费 85.32 → -85.32，Amex 还款 -200.0 → +200.0
        raw_float = parse_amount(row.get("Amount", ""))
        if raw_float is None:
            return None
        amount = -raw_float

        # 日期：Amex 列名是 "Date"（Chase 是 "Transaction Date"）
        tx_date = parse_date(row.get("Date", ""))
        if tx_date is None:
            return None

        # 分类：为空时用 "Uncategorized"
        category = row.get("Category", "").strip() or "Uncategorized"

        return CreditTransaction(
            date         = tx_date,
            description  = row.get("Description", "").strip(),
            category     = category,
            amount       = amount,
            account_name = account_name,
            account_last4= account_last4,
        )

    return parse_csv(file_path, row_to_transaction)
