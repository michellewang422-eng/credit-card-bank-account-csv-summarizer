# ============================================================
# 自动识别 CSV 文件是哪种账户格式
# 做法：读取第一行列名，和每种格式的特征列名比对
# ============================================================


# 每种格式的完整列名集合，用大括号 {} 表示集合（set）
# 集合的特点：无序、不重复，适合做"是否包含"的判断
# issubset() 的作用：检查这个集合里的所有列名是否都出现在 CSV 的列名里
# 例：{"Amount", "Date"}.issubset({"Date", "Amount", "Description"}) → True

# Chase 信用卡：7列
# 例：Chase 导出的 CSV 第一行是 Transaction Date,Post Date,Description,Category,Type,Amount,Memo
CHASE_CC_COLUMNS    = {
    "Transaction Date", "Post Date", "Description",
    "Category", "Type", "Amount", "Memo",
}

# Amex 信用卡：11列（列数最多，特征最独特，不容易和其他格式混淆）
# 例：Extended Details、Appears On Your Statement As 这些列只有 Amex 才有
AMEX_CC_COLUMNS     = {
    "Date", "Description", "Amount", "Extended Details",
    "Appears On Your Statement As", "Address", "City/State",
    "Zip Code", "Country", "Reference", "Category",
}

# Citi Costco 信用卡：6列（比普通 Citi 多一列 Member Name）
# ⚠️ 必须在普通 Citi 之前检测：
#   因为 Citi Costco 的列名完全包含普通 Citi 的列名
#   如果先检测普通 Citi，Costco 的文件也会被误判为普通 Citi
CITI_COSTCO_COLUMNS = {
    "Status", "Date", "Description", "Debit", "Credit", "Member Name",
}

# Citi 普通信用卡：5列
# 例：Citi 导出的 CSV 第一行是 Status,Date,Description,Debit,Credit
CITI_CC_COLUMNS     = {
    "Status", "Date", "Description", "Debit", "Credit",
}

# Chase 银行账户：7列
# 注意：用 "Posting Date" 和 "Balance" 区别于 Chase 信用卡（信用卡用 "Transaction Date"，无 Balance 列）
CHASE_BANK_COLUMNS  = {
    "Details", "Posting Date", "Description",
    "Amount", "Type", "Balance", "Check or Slip #",
}

# Wells Fargo 银行账户：5列
# 注意：列名全部大写（DATE、DESCRIPTION、AMOUNT），不会和其他银行的小写列名混淆
WELLS_FARGO_COLUMNS = {
    "DATE", "DESCRIPTION", "AMOUNT", "CHECK #", "STATUS",
}


def detect_account_type(fieldnames):
    # 根据 CSV 的列名列表，判断这个文件属于哪种账户格式
    # 参数 fieldnames：csv.DictReader 读出的列名列表
    # 例：["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount", "Memo"]
    # 返回值：对应格式的字符串，例："chase_cc"，识别失败返回 None

    # 如果列名列表为空（比如文件是空的），直接返回 None
    if fieldnames is None:
        return None

    # 把列名列表转成集合，方便用 issubset() 做包含判断
    # 例：["Amount", "Date", "Description"] → {"Amount", "Date", "Description"}
    columns = set(fieldnames)

    # 逐一用 issubset() 检查：特征列名集合里的所有列是否都出现在 CSV 的列名里
    # ⚠️ 检测顺序很重要，必须把特征更多（更具体）的格式放在前面：
    #   Citi Costco（6列）必须在普通 Citi（5列）前面，否则 Costco 文件会被误判

    # 检查是否是 Chase 信用卡
    # 例：columns 包含 "Transaction Date"、"Post Date" 等7列 → 返回 "chase_cc"
    if CHASE_CC_COLUMNS.issubset(columns):
        return "chase_cc"

    # 检查是否是 Amex 信用卡
    # 例：columns 包含 "Extended Details"、"Appears On Your Statement As" 等11列 → 返回 "amex_cc"
    if AMEX_CC_COLUMNS.issubset(columns):
        return "amex_cc"

    # 检查是否是 Citi Costco 信用卡（必须在普通 Citi 之前）
    # 例：columns 包含 "Member Name" 等6列 → 返回 "citi_costco"
    if CITI_COSTCO_COLUMNS.issubset(columns):
        return "citi_costco"

    # 检查是否是 Citi 普通信用卡
    # 例：columns 包含 "Debit"、"Credit" 等5列（但没有 "Member Name"）→ 返回 "citi_cc"
    if CITI_CC_COLUMNS.issubset(columns):
        return "citi_cc"

    # 检查是否是 Chase 银行账户
    # 例：columns 包含 "Posting Date"、"Balance" 等7列 → 返回 "chase_bank"
    if CHASE_BANK_COLUMNS.issubset(columns):
        return "chase_bank"

    # 检查是否是 Wells Fargo 银行账户
    # 例：columns 包含 "DATE"、"AMOUNT" 等5列（全大写）→ 返回 "wells_fargo_bank"
    if WELLS_FARGO_COLUMNS.issubset(columns):
        return "wells_fargo_bank"

    # 所有格式都没匹配到，返回 None，由调用方决定如何处理
    return None


def extract_account_info(filename):
    # 从文件名里提取账户名称和账户后四位
    # 文件名规则：用下划线分隔，最后一段是后四位数字，前面的是账户名
    # 例：
    #   "Chase_CC_9809.csv"         → name="Chase CC",          last4="9809"
    #   "Wells_Fargo_Bank_6789.csv" → name="Wells Fargo Bank",  last4="6789"
    #   "Amex_Gold_1234.csv"        → name="Amex Gold",         last4="1234"

    # 去掉 .csv 或 .CSV 扩展名，兼容大小写
    # 例："Chase_CC_9809.csv" → "Chase_CC_9809"
    name = filename.replace(".csv", "").replace(".CSV", "")

    # 用下划线把文件名拆成多段
    # 例："Chase_CC_9809" → ["Chase", "CC", "9809"]
    parts = name.split("_")

    # 检查最后一段是否全部是数字（即后四位）
    # isdigit() 返回 True 表示全是数字，例："9809" → True，"CC" → False
    if len(parts) >= 2 and parts[-1].isdigit():
        # 最后一段是数字 → 正常提取后四位和账户名
        # 例："Chase_CC_9809" → last4="9809", account_name="Chase CC"
        last4        = parts[-1]
        account_name = " ".join(parts[:-1])
    elif len(parts) >= 2:
        # 有下划线但最后一段不是数字 → 整个文件名作为账户名，用 "0000" 代替后四位
        # 例："Chase_CC.csv" → account_name="Chase CC", last4="0000"
        last4        = "0000"
        account_name = name.replace("_", " ")
    else:
        # 文件名没有下划线 → 整个文件名作为账户名，用 "0000" 代替后四位
        # 例："mybank.csv" → account_name="mybank", last4="0000"
        last4        = "0000"
        account_name = name

    # 返回账户名称和后四位，供 parse 函数使用
    # 例：("Chase CC", "9809")
    return account_name, last4
