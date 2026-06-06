# ============================================================
# 银行账户汇总计算器
# 表格2：Overall Bank Accounts Summary
# 表格4：Monthly Bank Accounts Summary（按月重复表格2的逻辑）
# ============================================================


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

    # 三个字典，key 都是银行名称（account_name），value 分别存不同数据
    bank_spending = {}   # key = bank name, value = 支出总额（负数累加）
    bank_income   = {}   # key = bank name, value = 收入总额（正数累加）
    bank_last4s   = {}   # key = bank name, value = 这家银行所有账户后4位的集合

    # 遍历每一笔交易，按银行名分组累加
    for t in transactions:

        # 取这笔交易的银行名称
        # 例：t.account_name = "Chase Checking"
        name = t.account_name

        # 如果这家银行第一次出现，先初始化它的三个字典条目
        if name not in bank_spending:
            bank_spending[name] = 0.0    # 支出从 0 开始累加
            bank_income[name]   = 0.0    # 收入从 0 开始累加
            bank_last4s[name]   = set()  # 用集合存账户后4位，自动去重（同一账户不重复）

        # 根据金额正负判断是支出还是收入，分别累加
        # 例：t.amount = -52.30 → 支出，累加到 bank_spending
        #     t.amount = 1200.0 → 收入，累加到 bank_income
        if t.amount < 0:
            bank_spending[name] = bank_spending[name] + t.amount
        else:
            bank_income[name]   = bank_income[name] + t.amount

        # 把这笔交易的账户后4位加入集合（集合自动去重，同一账户多笔交易只记录一次）
        # 例：bank_last4s["Chase"] = {"1234", "5678"}（Chase 名下有两个账户）
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
            "ending_balance": round(total_ending_balance, 2),  # 例：4300.0
            "spending":       round(bank_spending[name], 2),    # 例：-1230.5
            "income":         round(bank_income[name],   2),    # 例：3500.0
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

        # 两个字典，按分类统计金额和笔数
        category_amount = {}  # key = 分类名, value = 该分类金额合计
        category_count  = {}  # key = 分类名, value = 该分类交易笔数

        for t in account_transactions:
            # 银行账户没有消费分类列（不像信用卡有 "Groceries"、"Shopping" 等）
            # 所以统一用固定字符串 "Transaction" 作为分类名
            cat = "Transaction"

            # 如果该分类第一次出现，先初始化
            if cat not in category_amount:
                category_amount[cat] = 0.0
                category_count[cat]  = 0

            # 累加金额（正负都加，净额）和笔数
            # 例：三笔交易 -52.3、-30.0、+1200.0 → 合计 1117.7，共 3 笔
            category_amount[cat] = category_amount[cat] + t.amount
            category_count[cat]  = category_count[cat] + 1

        # 把分类统计整理成列表（银行账户只有一个分类 "Transaction"，所以列表只有一个元素）
        categories = []
        for cat in category_amount:
            categories.append({
                "category": cat,                             # 例："Transaction"
                "count":    category_count[cat],             # 例：25（共25笔）
                "amount":   round(category_amount[cat], 2),  # 例：1117.7（净额）
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

    # 取所有支出交易的金额并取反，变成正数方便求和
    # 例：交易金额 [-52.3, -30.0, 1200.0] → spending_list = [52.3, 30.0]
    spending_list = []                         # 存放每笔支出的正数金额
    income_list   = []                         # 存放每笔收入的金额
    for t in transactions:
        if t.amount < 0:                       # 负数 = 支出/取款
            spending_list.append(-t.amount)    # 取反变正数，例：-52.3 → 52.3
        else:                                  # 正数 = 存款/收入
            income_list.append(t.amount)       # 直接加入，例：1200.0

    # sum() 求和，round(..., 2) 保留两位小数
    # 例：total_spending = 52.3 + 30.0 = 82.3
    total_spending = round(sum(spending_list), 2)
    total_income   = round(sum(income_list),   2)

    # 用集合收集所有不同的账户后4位，集合自动去重
    # 例：交易来自账户 "1234"、"1234"、"5678" → unique_accounts = {"1234", "5678"}
    unique_accounts = set()                    # 用集合自动去重
    for t in transactions:
        unique_accounts.add(t.account_last4)   # 例：加入 "1234"、"5678"

    # 统计共有几个不同的账户
    # 例：{"1234", "5678"} → total_accounts = 2
    total_accounts  = len(unique_accounts)

    # 返回整体汇总字典，包含总账户数、总支出、总收入、按银行分组、按账户分组
    return {
        "total_accounts":  total_accounts,   # 例：2
        "total_spending":  total_spending,   # 例：82.3
        "total_income":    total_income,     # 例：1200.0
        "by_bank":         _group_by_bank(transactions),    # 调用分组函数，得到按银行的汇总列表
        "by_account":      _group_by_account(transactions), # 调用分组函数，得到按账户的汇总列表
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

        # 和 summarize_overall 一样，计算这个月的支出列表和收入列表
        spending_list = []                              # 存放这个月每笔支出的正数金额
        income_list   = []                              # 存放这个月每笔收入的金额
        for t in month_transactions:
            if t.amount < 0:                            # 负数 = 支出/取款
                spending_list.append(-t.amount)         # 取反变正数，例：-52.3 → 52.3
            else:                                       # 正数 = 存款/收入
                income_list.append(t.amount)            # 直接加入，例：1200.0

        # 把这个月的汇总数据打包成字典
        one_month = {
            "month":          month_key,                          # 例："2025-05"
            "total_spending": round(sum(spending_list), 2),       # 例：820.5
            "total_income":   round(sum(income_list),   2),       # 例：3500.0
            "by_bank":        _group_by_bank(month_transactions),    # 这个月按银行的分组
            "by_account":     _group_by_account(month_transactions), # 这个月按账户的分组
        }
        result.append(one_month)

    # 返回按月排列的汇总列表
    # 例：[{"month": "2025-01", ...}, {"month": "2025-02", ...}, ...]
    return result
