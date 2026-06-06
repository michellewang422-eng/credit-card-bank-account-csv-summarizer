# ============================================================
# Wells Fargo 银行账户 CSV 解析器
# 列名：DATE, DESCRIPTION, AMOUNT, CHECK #, STATUS
# 金额规则：负数 = 支出/取款，正数 = 收入/存款
# 注意：Wells Fargo 导出不含账户余额列，balance 固定为 0.0
# ============================================================

# 导入 csv 模块，用于读取 CSV 文件
# 例：Wells Fargo 导出的 CSV 每行是一条账户交易记录，csv 模块把每行变成字典
import csv

# 导入 datetime，用于把字符串日期转成真正的日期对象
# 例："05/15/2025" → datetime.date(2025, 5, 15)
from datetime import datetime

# 从同一个 parsers 包里导入 BankTransaction 数据类
# 和 chase_bank.py 一样，银行账户交易共用同一个数据模板（有 balance 字段）
from .models import BankTransaction


# 定义 parse 函数，接收三个参数：
#   file_path    = CSV 文件路径，例："/downloads/wells_fargo_checking.csv"
#   account_name = 账户名称，例："Wells Fargo Checking"
#   account_last4= 账户后四位，例："7890"
def parse(file_path, account_name, account_last4):

    # 创建空列表，用来收集所有解析成功的交易记录
    transactions = []

    # 打开 CSV 文件
    #   newline=""       → 让 csv 模块自己处理换行符，避免 Windows 上出现空行
    #   encoding="utf-8-sig" → 兼容 Excel 导出时自动加的 BOM 头
    with open(file_path, newline="", encoding="utf-8-sig") as f:

        # csv.DictReader 把每一行读成字典，列名作为 key
        # ⚠️ Wells Fargo 列名全部是大写，和其他银行不同
        # 例：{"DATE": "05/15/2025", "DESCRIPTION": "SAFEWAY #1234",
        #      "AMOUNT": "-52.30", "CHECK #": "", "STATUS": "posted"}
        reader = csv.DictReader(f)

        # 逐行遍历，每次 row 是上面那样的一个字典
        for row in reader:

            # 取出金额字段，strip() 去掉首尾空格
            # ⚠️ 注意列名是大写 "AMOUNT"，不是 "Amount"
            # 例：row["AMOUNT"] = "  -52.30  " → raw_amount = "-52.30"
            raw_amount = row.get("AMOUNT", "").strip()

            # 如果金额字段是空的（比如 CSV 末尾有空行），跳过这一行
            if not raw_amount:
                continue

            # 把字符串金额转成浮点数
            # Wells Fargo 金额规则和 Chase 银行相同：负数 = 支出/取款，正数 = 存款/收入
            # 例："-52.30" → -52.3（超市消费），"1200.0" → 1200.0（工资存入）
            # 如果转换失败（比如字段内容是 "N/A"），跳过这一行
            try:
                amount = float(raw_amount)
            except ValueError:
                continue

            # 取出日期字段，Wells Fargo 格式也是 MM/DD/YYYY
            # ⚠️ 注意列名是大写 "DATE"，不是 "Date"
            # 例：row["DATE"] = "05/15/2025" → raw_date = "05/15/2025"
            raw_date = row.get("DATE", "").strip()
            try:
                # strptime 按格式解析字符串，.date() 去掉时间部分只保留日期
                # 例："05/15/2025" → datetime.date(2025, 5, 15)
                tx_date = datetime.strptime(raw_date, "%m/%d/%Y").date()
            except ValueError:
                # 日期格式不对时跳过（没有日期的交易无法使用）
                continue

            # 用解析好的字段创建一个 BankTransaction 对象
            # ⚠️ balance 固定写死为 0.0：
            #   Wells Fargo 导出的 CSV 不包含账户余额列，无法获取余额
            #   （对比 Chase 银行，有 "Balance" 列可以读取真实余额）
            # 例：BankTransaction(date=2025-05-15, description="SAFEWAY #1234",
            #                     amount=-52.3, balance=0.0,
            #                     account_name="Wells Fargo Checking", account_last4="7890")
            transaction = BankTransaction(
                date         = tx_date,
                description  = row.get("DESCRIPTION", "").strip(),  # ⚠️ 列名也是大写
                amount       = amount,
                balance      = 0.0,   # Wells Fargo 导出不含余额列，固定填 0.0
                account_name = account_name,
                account_last4= account_last4,
            )

            # 把这条交易加入列表
            transactions.append(transaction)

    # 所有行处理完毕，返回完整的交易记录列表
    return transactions
