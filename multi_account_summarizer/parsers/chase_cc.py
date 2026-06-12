# ============================================================
# Chase 信用卡 CSV 解析器
# 列名：Transaction Date, Post Date, Description, Category, Type, Amount, Memo
# 金额规则：负数 = 支出，正数 = 还款/退款
# ============================================================

from .models import CreditTransaction
from .util import parse_csv, parse_amount, parse_date


def parse(file_path, account_name, account_last4):

    def row_to_transaction(row):
        # 金额：直接用，负数=支出，正数=还款
        amount = parse_amount(row.get("Amount", ""))
        if amount is None:
            return None

        # 日期：用 Transaction Date（实际刷卡日期）
        tx_date = parse_date(row.get("Transaction Date", ""))
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
