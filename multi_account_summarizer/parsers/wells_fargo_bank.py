# ============================================================
# Wells Fargo 银行账户 CSV 解析器
# 列名：DATE, DESCRIPTION, AMOUNT, CHECK #, STATUS
# 金额规则：负数 = 支出/取款，正数 = 收入/存款
# 注意：Wells Fargo 导出不含账户余额列，balance 固定为 0.0
# ============================================================

from .models import BankTransaction
from .util import parse_csv, parse_amount, parse_date


def parse(file_path, account_name, account_last4):

    def row_to_transaction(row):
        # 金额：⚠️ 列名全大写 "AMOUNT"（其他银行是 "Amount"）
        amount = parse_amount(row.get("AMOUNT", ""))
        if amount is None:
            return None

        # 日期：⚠️ 列名全大写 "DATE"（其他银行是 "Date" 或 "Posting Date"）
        tx_date = parse_date(row.get("DATE", ""))
        if tx_date is None:
            return None

        return BankTransaction(
            date         = tx_date,
            description  = row.get("DESCRIPTION", "").strip(),  # ⚠️ 列名也是大写
            amount       = amount,
            balance      = 0.0,   # Wells Fargo 导出不含余额列
            account_name = account_name,
            account_last4= account_last4,
        )

    return parse_csv(file_path, row_to_transaction)
