# ============================================================
# Chase 信用卡 CSV 解析器
# 列名：Transaction Date, Post Date, Description, Category, Type, Amount, Memo
# 金额规则：负数 = 支出，正数 = 还款/退款
# ============================================================

# 导入 csv 模块，用于读取 CSV 文件
# 例：Chase 信用卡导出的 CSV 每行是一条刷卡记录，csv 模块把每行变成字典
import csv

# 导入 datetime，用于把字符串日期转成真正的日期对象
# 例："05/15/2025" → datetime.date(2025, 5, 15)
from datetime import datetime

# 从同一个 parsers 包里导入 CreditTransaction 数据类
# 注意：这里导入的是 CreditTransaction，而不是 chase_bank.py 里的 BankTransaction
# 区别：信用卡交易有 category（消费分类）字段，银行账户交易有 balance（余额）字段
from .models import CreditTransaction


# 定义 parse 函数，接收三个参数：
#   file_path    = CSV 文件路径，例："/downloads/chase_sapphire.csv"
#   account_name = 账户名称，例："Chase Sapphire"
#   account_last4= 卡号后四位，例："5678"
def parse(file_path, account_name, account_last4):

    # 创建空列表，用来收集所有解析成功的交易记录
    transactions = []

    # 打开 CSV 文件
    #   newline=""       → 让 csv 模块自己处理换行符，避免 Windows 上出现空行
    #   encoding="utf-8-sig" → 兼容 Excel 导出时自动加的 BOM 头
    with open(file_path, newline="", encoding="utf-8-sig") as f:

        # csv.DictReader 把每一行读成字典，列名作为 key
        # 例：{"Transaction Date": "05/15/2025", "Post Date": "05/16/2025",
        #      "Description": "AMAZON.COM", "Category": "Shopping",
        #      "Type": "Sale", "Amount": "-39.99", "Memo": ""}
        reader = csv.DictReader(f)

        # 逐行遍历，每次 row 是上面那样的一个字典
        for row in reader:

            # 取出金额字段，strip() 去掉首尾空格
            # 例：row["Amount"] = "  -39.99  " → raw_amount = "-39.99"
            raw_amount = row.get("Amount", "").strip()

            # 如果金额字段是空的（比如 CSV 末尾有空行），跳过这一行
            if not raw_amount:
                continue

            # 把字符串金额转成浮点数
            # Chase 信用卡金额规则：负数 = 消费支出，正数 = 还款或退款
            # 例："-39.99" → -39.99（消费），"100.0" → 100.0（还款）
            # 如果转换失败（比如字段内容是 "N/A"），跳过这一行
            try:
                amount = float(raw_amount)
            except ValueError:
                continue

            # 取出交易日期（Transaction Date），格式固定是 MM/DD/YYYY
            # 注意：Chase 信用卡有两个日期列：
            #   Transaction Date = 实际刷卡日期（我们用这个）
            #   Post Date        = 银行入账日期（通常比刷卡晚 1-2 天，不用）
            # 例：row["Transaction Date"] = "05/15/2025" → raw_date = "05/15/2025"
            raw_date = row.get("Transaction Date", "").strip()
            try:
                # strptime 按格式解析字符串，.date() 去掉时间部分只保留日期
                # 例："05/15/2025" → datetime.date(2025, 5, 15)
                tx_date = datetime.strptime(raw_date, "%m/%d/%Y").date()
            except ValueError:
                # 日期格式不对时跳过（没有日期的交易无法使用）
                continue

            # 取出消费分类字段
            # `or "Uncategorized"` 的作用：如果 strip() 后是空字符串（""），
            # Python 会把它当 False，于是取后面的默认值 "Uncategorized"
            # 例：row["Category"] = "Shopping"  → category = "Shopping"
            #     row["Category"] = ""          → category = "Uncategorized"
            #     row["Category"] = "  "        → strip() 后是 "" → category = "Uncategorized"
            category = row.get("Category", "").strip() or "Uncategorized"

            # 用解析好的字段创建一个 CreditTransaction 对象
            # 例：CreditTransaction(date=2025-05-15, description="AMAZON.COM",
            #                       category="Shopping", amount=-39.99,
            #                       account_name="Chase Sapphire", account_last4="5678")
            transaction = CreditTransaction(
                date         = tx_date,
                description  = row.get("Description", "").strip(),  # 商户名，例："WHOLE FOODS #123"
                category     = category,
                amount       = amount,
                account_name = account_name,
                account_last4= account_last4,
            )

            # 把这条交易加入列表
            transactions.append(transaction)

    # 所有行处理完毕，返回完整的交易记录列表
    return transactions
