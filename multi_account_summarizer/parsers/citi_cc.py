# ============================================================
# Citi 信用卡 / Citi Costco 信用卡 CSV 解析器
# Citi 列名：      Status, Date, Description, Debit, Credit
# Citi Costco 列名：Status, Date, Description, Debit, Credit, Member Name
# 金额规则：
#   Debit  列有值 = 支出（正数）→ 转成负数
#   Credit 列有值 = 还款/退款（正数）→ 保持正数
# 注意：没有 Category 列，统一用 "Uncategorized"
# ============================================================

# 导入 csv 模块，用于读取 CSV 文件
# 例：Citi 导出的 CSV 每行是一条刷卡记录，csv 模块把每行变成字典
import csv

# 导入 datetime，用于把字符串日期转成真正的日期对象
# 例："05/15/2025" → datetime.date(2025, 5, 15)
from datetime import datetime

# 从同一个 parsers 包里导入 CreditTransaction 数据类
# 和其他信用卡解析器一样，共用同一个数据模板
from .models import CreditTransaction


# 定义 parse 函数，接收三个参数：
#   file_path    = CSV 文件路径，例："/downloads/citi_costco.csv"
#   account_name = 账户名称，例："Citi Costco"
#   account_last4= 卡号后四位，例："3456"
def parse(file_path, account_name, account_last4):

    # 创建空列表，用来收集所有解析成功的交易记录
    transactions = []

    # 打开 CSV 文件
    #   newline=""       → 让 csv 模块自己处理换行符，避免 Windows 上出现空行
    #   encoding="utf-8-sig" → 兼容 Excel 导出时自动加的 BOM 头
    with open(file_path, newline="", encoding="utf-8-sig") as f:

        # csv.DictReader 把每一行读成字典，列名作为 key
        # 例（普通 Citi）：   {"Status": "Cleared", "Date": "05/15/2025",
        #                      "Description": "AMAZON", "Debit": "39.99", "Credit": ""}
        # 例（Citi Costco）： {"Status": "Cleared", "Date": "05/15/2025",
        #                      "Description": "COSTCO GAS", "Debit": "60.00", "Credit": "",
        #                      "Member Name": "MICHELLE WANG"}
        reader = csv.DictReader(f)

        # 逐行遍历，每次 row 是上面那样的一个字典
        for row in reader:

            # ⚠️ Citi 的金额格式和其他银行完全不同：
            # 不用单一的 Amount 列，而是拆成两列：
            #   Debit  列：有值表示这是一笔支出（消费），值本身是正数
            #   Credit 列：有值表示这是一笔收入（还款或退款），值本身是正数
            # 同一行里，Debit 和 Credit 只会有一个有值，另一个为空
            raw_debit  = row.get("Debit", "").strip()   # 例："39.99" 或 ""
            raw_credit = row.get("Credit", "").strip()  # 例："" 或 "200.00"

            # 根据哪一列有值来决定金额和正负号
            if raw_debit:
                # Debit 有值 → 这是一笔消费支出
                # 取负数，统一成"负数=支出"的格式
                # 例：raw_debit = "39.99" → amount = -39.99
                try:
                    amount = -float(raw_debit)
                except ValueError:
                    # 值不是数字（比如 "N/A"），跳过这一行
                    continue

            elif raw_credit:
                # Credit 有值 → 这是一笔还款或退款
                # 保持正数，统一成"正数=还款/收入"的格式
                # 例：raw_credit = "200.00" → amount = 200.0
                try:
                    amount = float(raw_credit)
                except ValueError:
                    # 值不是数字，跳过这一行
                    continue

            else:
                # Debit 和 Credit 都为空 → 无效行，跳过
                # 例：CSV 末尾的空行，或 Status 行
                continue

            # 取出日期字段，Citi 格式也是 MM/DD/YYYY（和 Chase、Amex 相同）
            # 注意：Citi 的日期列名是 "Date"（和 Amex 相同，和 Chase 的 "Transaction Date" 不同）
            # 例：row["Date"] = "05/15/2025" → raw_date = "05/15/2025"
            raw_date = row.get("Date", "").strip()
            try:
                # strptime 按格式解析字符串，.date() 去掉时间部分只保留日期
                # 例："05/15/2025" → datetime.date(2025, 5, 15)
                tx_date = datetime.strptime(raw_date, "%m/%d/%Y").date()
            except ValueError:
                # 日期格式不对时跳过（没有日期的交易无法使用）
                continue

            # 用解析好的字段创建一个 CreditTransaction 对象
            # 注意：category 直接写死为 "Uncategorized"，因为 Citi 的 CSV 没有分类列
            # 例：CreditTransaction(date=2025-05-15, description="AMAZON",
            #                       category="Uncategorized", amount=-39.99,
            #                       account_name="Citi Costco", account_last4="3456")
            transaction = CreditTransaction(
                date         = tx_date,
                description  = row.get("Description", "").strip(),  # 商户名，例："COSTCO WHSE #0123"
                category     = "Uncategorized",   # Citi 没有分类列，固定填此值
                amount       = amount,
                account_name = account_name,
                account_last4= account_last4,
            )

            # 把这条交易加入列表
            transactions.append(transaction)

    # 所有行处理完毕，返回完整的交易记录列表
    return transactions
