# ============================================================
# Amex 信用卡 CSV 解析器
# 列名：Date, Description, Amount, Extended Details, ..., Category
# 金额规则：正数 = 支出，负数 = 还款/退款（和 Chase 相反！）
# 处理方式：读取后取反，统一成"负数=支出，正数=还款"
# ============================================================

# 导入 csv 模块，用于读取 CSV 文件
# 例：Amex 导出的 CSV 每行是一条刷卡记录，csv 模块把每行变成字典
import csv

# 导入 datetime，用于把字符串日期转成真正的日期对象
# 例："05/15/2025" → datetime.date(2025, 5, 15)
from datetime import datetime

# 从同一个 parsers 包里导入 CreditTransaction 数据类
# 和 chase_cc.py 一样，信用卡交易共用同一个数据模板
from .models import CreditTransaction


# 定义 parse 函数，接收三个参数：
#   file_path    = CSV 文件路径，例："/downloads/amex_gold.csv"
#   account_name = 账户名称，例："Amex Gold"
#   account_last4= 卡号后四位，例："9012"
def parse(file_path, account_name, account_last4):

    # 创建空列表，用来收集所有解析成功的交易记录
    transactions = []

    # 打开 CSV 文件
    #   newline=""       → 让 csv 模块自己处理换行符，避免 Windows 上出现空行
    #   encoding="utf-8-sig" → 兼容 Excel 导出时自动加的 BOM 头
    with open(file_path, newline="", encoding="utf-8-sig") as f:

        # csv.DictReader 把每一行读成字典，列名作为 key
        # 例：{"Date": "05/15/2025", "Description": "WHOLE FOODS",
        #      "Amount": "85.32", "Category": "Groceries", ...}
        reader = csv.DictReader(f)

        # 逐行遍历，每次 row 是上面那样的一个字典
        for row in reader:

            # 取出金额字段，strip() 去掉首尾空格
            # 例：row["Amount"] = "  85.32  " → raw_amount = "85.32"
            raw_amount = row.get("Amount", "").strip()

            # 如果金额字段是空的（比如 CSV 末尾有空行），跳过这一行
            if not raw_amount:
                continue

            # 把字符串金额转成浮点数，暂存为 raw_float
            # 例："85.32" → 85.32，"-200.00" → -200.0
            # 如果转换失败（比如字段内容是 "N/A"），跳过这一行
            try:
                raw_float = float(raw_amount)
            except ValueError:
                continue

            # ⚠️ Amex 金额方向和 Chase 相反，必须取反才能统一格式：
            #   Amex 原始：消费是正数，还款是负数
            #   统一格式：消费是负数，还款是正数（和 Chase 一致）
            # 例：Amex 消费 85.32  → raw_float =  85.32 → amount = -85.32
            #     Amex 还款 -200.0 → raw_float = -200.0 → amount = +200.0
            amount = -raw_float

            # 取出日期字段，Amex 格式也是 MM/DD/YYYY（和 Chase 相同）
            # 注意：Amex 的日期列名是 "Date"，而不是 Chase 的 "Transaction Date"
            # 例：row["Date"] = "05/15/2025" → raw_date = "05/15/2025"
            raw_date = row.get("Date", "").strip()
            try:
                # strptime 按格式解析字符串，.date() 去掉时间部分只保留日期
                # 例："05/15/2025" → datetime.date(2025, 5, 15)
                tx_date = datetime.strptime(raw_date, "%m/%d/%Y").date()
            except ValueError:
                # 日期格式不对时跳过（没有日期的交易无法使用）
                continue

            # 取出消费分类字段，为空时用 "Uncategorized" 代替
            # 例：row["Category"] = "Groceries" → category = "Groceries"
            #     row["Category"] = ""           → category = "Uncategorized"
            category = row.get("Category", "").strip() or "Uncategorized"

            # 用解析好的字段创建一个 CreditTransaction 对象
            # 例：CreditTransaction(date=2025-05-15, description="WHOLE FOODS",
            #                       category="Groceries", amount=-85.32,
            #                       account_name="Amex Gold", account_last4="9012")
            transaction = CreditTransaction(
                date         = tx_date,
                description  = row.get("Description", "").strip(),  # 商户名，例："WHOLE FOODS #456"
                category     = category,
                amount       = amount,
                account_name = account_name,
                account_last4= account_last4,
            )

            # 把这条交易加入列表
            transactions.append(transaction)

    # 所有行处理完毕，返回完整的交易记录列表
    return transactions
