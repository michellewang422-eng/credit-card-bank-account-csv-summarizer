# ============================================================
# 信用卡汇总计算器
# 表格1：Overall Credit Cards Summary
# 表格3：Monthly Credit Cards Summary（按月重复表格1的逻辑）
# ============================================================


def _group_by_card(transactions):
    # 按信用卡名称分组，统计每张卡的笔数、支出、还款

    # 三个字典，key 都是信用卡名称（account_name），value 分别存不同数据
    card_spending = {}   # key = account_name, value = 支出总额（负数累加）
    card_credits  = {}   # key = account_name, value = 还款总额（正数累加）
    card_counts   = {}   # key = account_name, value = 交易总笔数

    # 遍历每一笔交易，按卡名分组累加
    for t in transactions:

        # 取这笔交易的信用卡名称
        # 例：t.account_name = "Chase Sapphire"
        name = t.account_name

        # 如果这张卡第一次出现，先初始化它的三个字典条目
        if name not in card_spending:
            card_spending[name] = 0.0   # 支出从 0 开始累加
            card_credits[name]  = 0.0   # 还款从 0 开始累加
            card_counts[name]   = 0     # 笔数从 0 开始计数

        # 根据金额正负判断是支出还是还款，分别累加
        # 例：t.amount = -39.99 → 支出，累加到 card_spending
        #     t.amount = 200.0  → 还款，累加到 card_credits
        if t.amount < 0:
            card_spending[name] = card_spending[name] + t.amount
        else:
            card_credits[name]  = card_credits[name] + t.amount

        # 无论支出还是还款，笔数都加 1
        card_counts[name] = card_counts[name] + 1

    # 把上面三个字典整理成一个列表，每个元素代表一张卡的汇总
    result = []
    for name in card_spending:
        # round(..., 2) 保留两位小数，避免浮点误差
        # 例：card_spending["Chase Sapphire"] = -1230.5
        #     card_credits["Chase Sapphire"]  = 500.0
        #     card_counts["Chase Sapphire"]   = 18
        one_card = {
            "name":         name,                            # 例："Chase Sapphire"
            "transactions": card_counts[name],               # 例：18（共18笔）
            "spending":     round(card_spending[name], 2),   # 例：-1230.5
            "credits":      round(card_credits[name],  2),   # 例：500.0
        }
        result.append(one_card)

    # 定义一个函数，告诉 sort 用每张卡的 spending 值作为排序依据
    def get_spending(x):
        return x["spending"]

    # 按支出从多到少排序（spending 是负数，最小的即花得最多的排在最前面）
    # 例：spending -1230.5 排在 -200.0 前面
    result.sort(key=get_spending)

    return result


def _group_by_category(transactions):
    # 按消费分类分组，统计所有信用卡合并后各分类的支出金额和笔数

    # 三个字典，key 都是分类名称（category）
    category_spending = {}   # key = 分类名, value = 该分类支出总额（负数累加）
    category_credits  = {}   # key = 分类名, value = 该分类还款总额（正数累加）
    category_count    = {}   # key = 分类名, value = 该分类交易笔数

    for t in transactions:
        cat = t.category

        if cat not in category_spending:
            category_spending[cat] = 0.0
            category_credits[cat]  = 0.0
            category_count[cat]    = 0

        # 支出和还款分开累加，和顶部 total_spending / total_credits 逻辑一致
        if t.amount < 0:
            category_spending[cat] = category_spending[cat] + t.amount
        else:
            category_credits[cat]  = category_credits[cat] + t.amount

        category_count[cat] = category_count[cat] + 1

    result = []
    for cat in category_spending:
        one_category = {
            "category": cat,
            "count":    category_count[cat],
            "spending": round(category_spending[cat], 2),   # 例：-82.3
            "credits":  round(category_credits[cat],  2),   # 例：0.0 或 25.0
        }
        result.append(one_category)

    # 按支出从多到少排序
    def get_spending(x):
        return x["spending"]

    result.sort(key=get_spending)

    return result


def summarize_overall(transactions):
    # 计算表格1：所有信用卡的整体汇总（对应 Overall Credit Cards Summary）

    # 如果没有任何交易记录，直接返回 None，让调用方跳过这张表
    if not transactions:
        return None

    # 遍历所有交易，分别收集支出金额（取反变正数）和还款金额
    spending_list = []   # 存放每笔支出的正数金额，例：[39.99, 52.3, 30.0]
    credits_list  = []   # 存放每笔还款的金额，例：[200.0, 500.0]
    for t in transactions:
        if t.amount < 0:                       # 负数 = 消费支出
            spending_list.append(-t.amount)    # 取反变正数，例：-39.99 → 39.99
        else:                                  # 正数 = 还款/退款
            credits_list.append(t.amount)      # 直接加入，例：200.0

    # sum() 求和，round(..., 2) 保留两位小数
    # 例：total_spending = 39.99 + 52.3 + 30.0 = 122.29
    total_spending = round(sum(spending_list), 2)
    total_credits  = round(sum(credits_list),  2)

    # 用集合收集所有不同的信用卡名称，集合自动去重
    # 例：交易来自 "Chase Sapphire"、"Chase Sapphire"、"Amex Gold"
    #     → unique_cards = {"Chase Sapphire", "Amex Gold"}
    unique_cards = set()
    for t in transactions:
        unique_cards.add(t.account_name)   # 重复的卡名自动忽略

    # 统计共有几张不同的信用卡
    # 例：{"Chase Sapphire", "Amex Gold"} → total_cards = 2
    total_cards = len(unique_cards)

    # 返回整体汇总字典，包含总卡数、总支出、总还款、按卡分组、按分类分组
    return {
        "total_cards":    total_cards,                    # 例：2
        "total_spending": total_spending,                 # 例：122.29
        "total_credits":  total_credits,                  # 例：700.0
        "by_card":        _group_by_card(transactions),       # 调用分组函数，得到按卡的汇总列表
        "by_category":    _group_by_category(transactions),   # 调用分组函数，得到按分类的汇总列表
    }


def summarize_monthly(transactions):
    # 计算表格3：按月份分组，每个月重复 summarize_overall 的逻辑

    # 第一步：把所有交易按年月分组
    # key = "YYYY-MM" 格式字符串，value = 这个月的交易列表
    # 例：{"2025-01": [交易A, 交易B], "2025-02": [交易C]}
    monthly_groups = {}

    for t in transactions:
        # strftime 把日期格式化成 "YYYY-MM" 字符串
        # 例：datetime.date(2025, 5, 15) → "2025-05"
        month_key = t.date.strftime("%Y-%m")

        # 如果这个月第一次出现，先初始化一个空列表
        if month_key not in monthly_groups:
            monthly_groups[month_key] = []

        # 把这笔交易加入对应月份的列表
        monthly_groups[month_key].append(t)

    # 第二步：对每个月计算汇总，结果存入列表
    result = []

    # sorted() 让月份按时间顺序排列（字符串 "2025-01" < "2025-02"，直接排字符串即可）
    # 例：["2025-03", "2025-01", "2025-02"] → ["2025-01", "2025-02", "2025-03"]
    for month_key in sorted(monthly_groups.keys()):

        # 取出这个月的所有交易
        month_transactions = monthly_groups[month_key]

        # 和 summarize_overall 一样，计算这个月的支出列表和还款列表
        spending_list = []   # 存放这个月每笔支出的正数金额
        credits_list  = []   # 存放这个月每笔还款的金额
        for t in month_transactions:
            if t.amount < 0:                        # 负数 = 消费支出
                spending_list.append(-t.amount)     # 取反变正数，例：-39.99 → 39.99
            else:                                   # 正数 = 还款/退款
                credits_list.append(t.amount)       # 直接加入，例：200.0

        # 把这个月的汇总数据打包成字典
        one_month = {
            "month":          month_key,                              # 例："2025-05"
            "total_spending": round(sum(spending_list), 2),           # 例：122.29
            "total_credits":  round(sum(credits_list),  2),           # 例：700.0
            "by_card":        _group_by_card(month_transactions),         # 这个月按卡的分组
            "by_category":    _group_by_category(month_transactions),     # 这个月按分类的分组
        }
        result.append(one_month)

    # 返回按月排列的汇总列表
    # 例：[{"month": "2025-01", ...}, {"month": "2025-02", ...}, ...]
    return result
