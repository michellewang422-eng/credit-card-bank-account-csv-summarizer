# ============================================================
# Citi 信用卡 / Citi Costco 信用卡 CSV 解析器
# Citi 列名：      Status, Date, Description, Debit, Credit
# Citi Costco 列名：Status, Date, Description, Debit, Credit, Member Name
# 金额规则：
#   Debit  列有值 = 支出（正数）→ 转成负数
#   Credit 列有值 = 还款/退款（正数）→ 保持正数
# 注意：没有 Category 列，统一用 "Uncategorized"
# ============================================================

from .models import CreditTransaction
from .util import parse_csv, parse_amount, parse_date


def parse(file_path, account_name, account_last4):

    def row_to_transaction(row):
        # ⚠️ Citi 金额拆成两列，不同于其他银行的单一 Amount 列
        raw_debit  = row.get("Debit",  "").strip()
        raw_credit = row.get("Credit", "").strip()

        if raw_debit:
            # Debit 有值 = 支出，取负数
            amount = parse_amount(raw_debit)
            if amount is None:
                return None
            amount = -amount
        elif raw_credit:
            # Credit 有值 = 还款/退款
            # ⚠️ Citi 的 Credit 列里还款是负数（例：-1211.26），取反变成正数统一格式
            amount = parse_amount(raw_credit)
            if amount is None:
                return None
            amount = -amount   # 例：-1211.26 → +1211.26
        else:
            # 两列都为空，跳过
            return None

        # 日期：Citi 列名是 "Date"
        tx_date = parse_date(row.get("Date", ""))
        if tx_date is None:
            return None

        return CreditTransaction(
            date         = tx_date,
            description  = row.get("Description", "").strip(),
            category     = "Uncategorized",   # Citi 没有分类列
            amount       = amount,
            account_name = account_name,
            account_last4= account_last4,
        )

    return parse_csv(file_path, row_to_transaction)
