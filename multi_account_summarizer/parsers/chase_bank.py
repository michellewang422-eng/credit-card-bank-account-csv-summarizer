# ============================================================
# Chase 银行账户 CSV 解析器
# 列名：Details, Posting Date, Description, Amount, Type, Balance, Check or Slip #
# 金额规则：负数 = 支出/取款，正数 = 收入/存款
# 特别：保留 Balance（账户余额）列
# ============================================================

from .models import BankTransaction
from .util import parse_csv, parse_amount, parse_date


def parse(file_path, account_name, account_last4):

    def row_to_transaction(row):
        # 金额：直接用，负数=支出，正数=存款
        amount = parse_amount(row.get("Amount", ""))
        if amount is None:
            return None

        # 日期：Chase 银行列名是 "Posting Date"（信用卡是 "Transaction Date"）
        tx_date = parse_date(row.get("Posting Date", ""))
        if tx_date is None:
            return None

        # 余额：解析失败时用 0.0 代替，不跳过这条交易
        balance = parse_amount(row.get("Balance", ""))
        if balance is None:
            balance = 0.0

        return BankTransaction(
            date         = tx_date,
            description  = row.get("Description", "").strip(),
            amount       = amount,
            balance      = balance,
            account_name = account_name,
            account_last4= account_last4,
        )

    return parse_csv(file_path, row_to_transaction)
