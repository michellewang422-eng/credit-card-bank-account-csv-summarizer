# ============================================================
# 银行账户汇总计算器
# 表格2：Overall Bank Accounts Summary
# 表格4：Monthly Bank Accounts Summary（按月重复表格2的逻辑）
# ============================================================


def _is_transfer(t):
    # 判断一笔交易是否是账户间转账
    # 例："ONLINE TRANSFER TO XXXXXX6631"        → True
    #     "First Tech Feder... One-Time Transf"  → True（截断的 Transfer）
    #     "WT 260212... CHINA CITIC BANK"         → True（Wire Transfer）
    #     "WIRE TRANS SVC CHARGE"                → True（Wire 手续费）
    #     "STARBUCKS #123"                       → False
    desc = t.description.upper()
    return (
        "TRANSFER" in desc or
        "TRANSF"   in desc or   # 截断的 Transfer，例："One-Time Transf"
        "XFER"     in desc or
        "WIRE"     in desc or   # Wire transfer，例："WIRE TRANS SVC CHARGE"
        "WT "      in desc      # Wire transfer 前缀，例："WT 260212-180938..."
    )


def _is_cc_payment(t):
    # 判断一笔银行交易是否是信用卡还款（从银行账户付给信用卡）
    # 这类交易不算真实支出，因为实际消费已经记录在信用卡账单里
    # 例："CHASE CREDIT CRD EPAY"                → True（Chase 信用卡还款）
    #     "CITI CARD ONLINE PAYMENT"             → True（Citi 在线还款）
    #     "AMERICAN EXPRESS ACH PMT"             → True（Amex 还款）
    #     "BANK OF AMERICA  PAYMENT 18c5rjieb"  → True（BofA 信用卡还款，同时含 BANK OF AMERICA 和 PAYMENT）
    #     "AMAZON CORP SYF PAYMNT"               → True（Synchrony Financial）
    #     "ONLINE TRANSFER TO BANK OF AMERICA"  → False（转账，被 _is_transfer 先捕获）
    #     "REGIONS MORTGAGE MORT PMT"            → False（房贷还款，是真实支出）
    desc = t.description.upper()
    return (
        "CREDIT CRD"          in desc or   # 例："CHASE CREDIT CRD EPAY"
        "CREDIT CARD"         in desc or
        "EPAY"                in desc or   # 电子还款
        "CARD ONLINE PAYMENT" in desc or   # 例："CITI CARD ONLINE PAYMENT"
        "SYF PAYMNT"          in desc or   # Synchrony Financial，例："AMAZON CORP SYF PAYMNT"
        "AMERICAN EXPRESS"    in desc or   # Amex 还款
        "AMEX"                in desc or   # Amex 缩写
        # BofA：必须同时包含 "BANK OF AMERICA" 和 "PAYMENT"，
        # 避免把转账到 BofA 账户误判为信用卡还款
        ("BANK OF AMERICA" in desc and "PAYMENT" in desc)
    )


def _get_ending_balance(transactions, account_last4):
    # 取某个账户（后4位）最后一笔交易的 balance，作为 ending balance
    # 思路：先筛出这个账户的所有交易 → 按日期排序 → 取最后一笔的 balance

    # 从所有交易里只保留属于这个账户的交易
    # 例：account_last4 = "1234"，只保留 t.account_last4 == "1234" 的交易
    account_transactions = []                          # 先建一个空列表
    for t in transactions:                             # 逐笔遍历所有交易
        if t.account_last4 == account_last4:           # 如果这笔交易属于目标账户
            account_transactions.append(t)             # 就把它加入列表

    # 如果这个账户没有任何交易记录，直接返回 0.0
    if not account_transactions:
        return 0.0

    # 定义一个函数，告诉 sort 用 t.date 作为排序依据
    def get_date(t):
        return t.date

    # 按日期从早到晚排序
    # 例：[2025-03-01, 2025-01-15, 2025-05-20] → [2025-01-15, 2025-03-01, 2025-05-20]
    account_transactions.sort(key=get_date)

    # 取排序后最后一笔交易（即日期最近的那笔）
    # 例：排序后最后一笔是 2025-05-20 那条记录
    last_transaction = account_transactions[-1]

    # 返回这笔交易记录的账户余额，作为该账户的期末余额
    # 例：last_transaction.balance = 3500.0 → 返回 3500.0
    return last_transaction.balance


def _group_by_bank(transactions):
    # 按银行名称分组，统计每家银行的 ending balance、支出、收入

    bank_spending      = {}   # 真实支出（排除 transfer 和信用卡还款）
    bank_income        = {}   # 真实收入（排除 transfer）
    bank_transfer_out  = {}   # 转出金额
    bank_transfer_in   = {}   # 转入金额
    bank_cc_payments   = {}   # 信用卡还款金额（负数）
    bank_last4s        = {}

    for t in transactions:
        name = t.account_name

        if name not in bank_spending:
            bank_spending[name]     = 0.0
            bank_income[name]       = 0.0
            bank_transfer_out[name] = 0.0
            bank_transfer_in[name]  = 0.0
            bank_cc_payments[name]  = 0.0
            bank_last4s[name]       = set()

        if _is_transfer(t):
            if t.amount < 0:
                bank_transfer_out[name] = bank_transfer_out[name] + t.amount
            else:
                bank_transfer_in[name]  = bank_transfer_in[name] + t.amount
        elif _is_cc_payment(t):
            # 信用卡还款单独累加，不计入真实支出
            bank_cc_payments[name] = bank_cc_payments[name] + t.amount
        else:
            if t.amount < 0:
                bank_spending[name] = bank_spending[name] + t.amount
            else:
                bank_income[name]   = bank_income[name] + t.amount

        bank_last4s[name].add(t.account_last4)

    # 把上面三个字典整理成一个列表，每个元素代表一家银行
    result = []
    for name in bank_spending:

        # 计算这家银行旗下所有账户的 ending balance 总和
        # 例：Chase 有账户 "1234"（余额 3500）和 "5678"（余额 800）→ 总计 4300
        total_ending_balance = 0.0
        for last4 in bank_last4s[name]:
            # 调用上面的辅助函数，获取每个账户的期末余额，逐个累加
            total_ending_balance = total_ending_balance + _get_ending_balance(transactions, last4)

        # 把这家银行的汇总数据打包成字典
        # round(..., 2) 保留两位小数，避免浮点误差（例：-52.300000000001 → -52.3）
        one_bank = {
            "name":           name,
            "ending_balance": round(total_ending_balance,      2),
            "spending":       round(bank_spending[name],       2),
            "income":         round(bank_income[name],         2),
            "transfer_out":   round(bank_transfer_out[name],   2),
            "transfer_in":    round(bank_transfer_in[name],    2),
            "cc_payments":    round(bank_cc_payments[name],    2),
        }
        result.append(one_bank)

    # 定义一个函数，告诉 sort 用每家银行的 spending 值作为排序依据
    def get_spending(x):
        return x["spending"]

    # 按支出金额从小到大排序（支出是负数，所以最小的是花得最多的）
    # 例：spending -1500 排在 -200 前面，即花得多的银行排在前面
    result.sort(key=get_spending)

    return result


def _group_by_account(transactions):
    # 按账户后4位分组，统计每个账户的交易详情

    # 先把所有交易按账户后4位归组，每个账户对应一个交易列表
    # 例：{"1234": [交易A, 交易B], "5678": [交易C]}
    account_groups = {}   # key = last4, value = 该账户的交易列表

    for t in transactions:
        last4 = t.account_last4  # 例：last4 = "1234"

        # 如果这个账户第一次出现，先初始化一个空列表
        if last4 not in account_groups:
            account_groups[last4] = []

        # 把这笔交易加入对应账户的列表
        account_groups[last4].append(t)

    # 对每个账户，进一步统计分类数据
    result = []

    for last4 in account_groups:
        # 取出这个账户的所有交易
        account_transactions = account_groups[last4]

        # 从第一笔交易里取账户名称（同一账户所有交易的 account_name 都一样）
        # 例：account_name = "Chase Checking"
        account_name = account_transactions[0].account_name

        category_spending = {}
        category_income   = {}
        category_count    = {}

        for t in account_transactions:
            # 三种分类：Transfer（转账）、CC Payment（信用卡还款）、Transaction（真实收支）
            if _is_transfer(t):
                cat = "Transfer"
            elif _is_cc_payment(t):
                cat = "CC Payment"
            else:
                cat = "Transaction"

            if cat not in category_spending:
                category_spending[cat] = 0.0
                category_income[cat]   = 0.0
                category_count[cat]    = 0

            if t.amount < 0:
                category_spending[cat] = category_spending[cat] + t.amount
            else:
                category_income[cat]   = category_income[cat] + t.amount

            category_count[cat] = category_count[cat] + 1

        categories = []
        for cat in category_spending:
            categories.append({
                "category": cat,
                "count":    category_count[cat],
                "spending": round(category_spending[cat], 2),  # 例：-82.3
                "income":   round(category_income[cat],   2),  # 例：1200.0
            })

        # 把这个账户的汇总数据打包成字典
        one_account = {
            "last4":        last4,         # 例："1234"
            "account_name": account_name,  # 例："Chase Checking"
            "categories":   categories,    # 例：[{"category": "Transaction", "count": 25, "amount": 1117.7}]
        }
        result.append(one_account)

    return result


def summarize_overall(transactions):
    # 计算表格2：所有银行账户的整体汇总（对应 Overall Bank Accounts Summary）

    # 如果没有任何交易记录，直接返回 None，让调用方跳过这张表
    if not transactions:
        return None

    # 所有流出保留负号，流入保留正号，符号统一方便计算
    spending_list      = []
    income_list        = []
    transfer_out_list  = []
    transfer_in_list   = []
    cc_payment_list    = []

    for t in transactions:
        if _is_transfer(t):
            if t.amount < 0:
                transfer_out_list.append(t.amount)   # 负数，例：-1000.0
            else:
                transfer_in_list.append(t.amount)    # 正数，例：+1000.0
        elif _is_cc_payment(t):
            cc_payment_list.append(t.amount)         # 负数，例：-500.0
        else:
            if t.amount < 0:
                spending_list.append(t.amount)        # 负数，例：-82.3
            else:
                income_list.append(t.amount)          # 正数，例：1200.0

    total_spending     = round(sum(spending_list),     2)   # 负数
    total_income       = round(sum(income_list),       2)   # 正数
    total_transfer_out = round(sum(transfer_out_list), 2)   # 负数
    total_transfer_in  = round(sum(transfer_in_list),  2)   # 正数
    total_cc_payments  = round(sum(cc_payment_list),   2)   # 负数

    unique_accounts = set()
    for t in transactions:
        unique_accounts.add(t.account_last4)

    total_accounts = len(unique_accounts)

    return {
        "total_accounts":     total_accounts,
        "total_spending":     total_spending,
        "total_income":       total_income,
        "total_transfer_out": total_transfer_out,
        "total_transfer_in":  total_transfer_in,
        "total_cc_payments":  total_cc_payments,
        "by_bank":            _group_by_bank(transactions),
        "by_account":         _group_by_account(transactions),
    }


def summarize_monthly(transactions):
    # 计算表格4：按月份分组，每个月重复 summarize_overall 的逻辑

    # 按年月把交易分组，key 是 "YYYY-MM" 格式的字符串
    monthly_groups = {}  # 例：{"2025-01": [交易...], "2025-02": [交易...]}

    for t in transactions:
        # strftime 把日期格式化成字符串
        # 例：datetime.date(2025, 5, 15) → "2025-05"
        month_key = t.date.strftime("%Y-%m")

        # 如果这个月第一次出现，先初始化一个空列表
        if month_key not in monthly_groups:
            monthly_groups[month_key] = []

        # 把这笔交易加入对应月份的列表
        monthly_groups[month_key].append(t)

    # 对每个月计算汇总，结果存入列表
    result = []

    # sorted() 让月份按时间顺序排列（字符串 "2025-01" < "2025-02"，所以直接排字符串即可）
    # 例：["2025-03", "2025-01", "2025-02"] → ["2025-01", "2025-02", "2025-03"]
    for month_key in sorted(monthly_groups.keys()):

        # 取出这个月的所有交易
        month_transactions = monthly_groups[month_key]

        spending_list     = []
        income_list       = []
        transfer_out_list = []
        transfer_in_list  = []
        cc_payment_list   = []

        for t in month_transactions:
            if _is_transfer(t):
                if t.amount < 0:
                    transfer_out_list.append(t.amount)   # 负数
                else:
                    transfer_in_list.append(t.amount)    # 正数
            elif _is_cc_payment(t):
                cc_payment_list.append(t.amount)         # 负数
            else:
                if t.amount < 0:
                    spending_list.append(t.amount)        # 负数
                else:
                    income_list.append(t.amount)          # 正数

        one_month = {
            "month":              month_key,
            "total_spending":     round(sum(spending_list),     2),
            "total_income":       round(sum(income_list),       2),
            "total_transfer_out": round(sum(transfer_out_list), 2),
            "total_transfer_in":  round(sum(transfer_in_list),  2),
            "total_cc_payments":  round(sum(cc_payment_list),   2),
            "by_bank":            _group_by_bank(month_transactions),
            "by_account":         _group_by_account(month_transactions),
        }
        result.append(one_month)

    # 返回按月排列的汇总列表
    # 例：[{"month": "2025-01", ...}, {"month": "2025-02", ...}, ...]
    return result
