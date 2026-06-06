# ============================================================
# Chase 银行账户 CSV 解析器
# 列名：Details, Posting Date, Description, Amount, Type, Balance, Check or Slip #
# 金额规则：负数 = 支出/取款，正数 = 收入/存款
# 特别：保留 Balance（账户余额）列
# ============================================================

# 导入 csv 模块，用于读取 CSV 文件
# 例：CSV 文件里每行是一条交易记录，csv 模块帮我们把每行变成字典
import csv

# 导入 datetime，用于把字符串日期转成真正的日期对象
# 例："05/15/2025" → datetime.date(2025, 5, 15)
from datetime import datetime

# 从同一个 parsers 包里导入 BankTransaction 数据类
# BankTransaction 是一个模板，定义了一条银行交易记录有哪些字段
from .models import BankTransaction


# 定义 parse 函数，接收三个参数：
#   file_path    = CSV 文件的路径，例："/downloads/chase_checking.csv"
#   account_name = 账户名称，例："Chase Checking"
#   account_last4= 账户后四位，例："1234"
def parse(file_path, account_name, account_last4):

    # 创建一个空列表，用来存放解析出来的所有交易记录
    # 最终这个列表会被 return 出去
    transactions = []

    # 打开 CSV 文件
    #   newline=""     → 让 csv 模块自己处理换行符，避免在 Windows 上出现空行
    #   encoding="utf-8-sig" → 兼容带 BOM 头的 UTF-8 文件（Excel 导出的 CSV 常有 BOM）
    with open(file_path, newline="", encoding="utf-8-sig") as f:

        # csv.DictReader 把每一行读成字典，列名作为 key
        # 例：{"Details": "DEBIT", "Posting Date": "05/15/2025",
        #      "Description": "STARBUCKS", "Amount": "-5.75", "Balance": "1200.00", ...}
        reader = csv.DictReader(f)

        # 逐行遍历 CSV，每次 row 就是上面那样的一个字典
        for row in reader:

            # 取出金额字段，strip() 去掉首尾空格
            # 例：row["Amount"] = "  -5.75  " → raw_amount = "-5.75"
            raw_amount = row.get("Amount", "").strip()

            # 如果金额字段是空的（比如表头下有空行），跳过这一行
            if not raw_amount:
                continue

            try:
                # 把字符串金额转成浮点数
                # 例："-5.75" → -5.75（负数表示支出），"200.0" → 200.0（正数表示存款）
                amount = float(raw_amount)
            except ValueError:
                # 如果转换失败（比如金额字段里有文字），跳过这一行
                continue

            # 取出账户余额字段，strip() 去掉首尾空格
            # 例：row["Balance"] = "1200.00" → raw_balance = "1200.00"
            raw_balance = row.get("Balance", "").strip()
            try:
                # 把字符串余额转成浮点数
                # 例："1200.00" → 1200.0
                balance = float(raw_balance)
            except ValueError:
                # 余额解析失败时用 0 代替，不跳过这条交易（余额不影响核心逻辑）
                balance = 0.0

            # 取出日期字段，Chase 银行导出的格式固定是 MM/DD/YYYY
            # 例：row["Posting Date"] = "05/15/2025" → raw_date = "05/15/2025"
            raw_date = row.get("Posting Date", "").strip()
            try:
                # strptime 按指定格式解析日期字符串，.date() 只保留日期部分（去掉时间）
                # 例："05/15/2025" → datetime.date(2025, 5, 15)
                tx_date = datetime.strptime(raw_date, "%m/%d/%Y").date()
            except ValueError:
                # 日期格式不对时跳过这一行（没有日期的交易无法使用）
                continue

            # 用解析出的字段创建一个 BankTransaction 对象
            # 例：BankTransaction(date=2025-05-15, description="STARBUCKS",
            #                     amount=-5.75, balance=1200.0,
            #                     account_name="Chase Checking", account_last4="1234")
            transaction = BankTransaction(
                date         = tx_date,
                description  = row.get("Description", "").strip(),  # 交易描述，例："STARBUCKS 00123"
                amount       = amount,
                balance      = balance,
                account_name = account_name,
                account_last4= account_last4,
            )

            # 把这条交易记录加入列表
            transactions.append(transaction)

    # 所有行处理完毕，返回完整的交易记录列表
    return transactions
