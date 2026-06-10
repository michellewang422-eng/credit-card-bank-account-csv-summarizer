# ============================================================
# 把4张表格写入同一个 CSV 文件
# 表格1：Overall Credit Cards Summary
# 表格2：Overall Bank Accounts Summary
# 表格3：Monthly Credit Cards Summary
# 表格4：Monthly Bank Accounts Summary
# ============================================================

# 导入 csv 模块，用于把数据写出为 CSV 文件
import csv


def _format_account_label(last4, account_name):
    # 生成账户的显示标签
    # 如果 last4 是数字（正常格式）→ 显示 "****6789 (Chase Checking)"
    # 如果 last4 不是数字（文件名没有后四位）→ 直接显示账户名，不加 ****
    # 例：last4="6789"      → "****6789 (Chase Checking)"
    #     last4="Chase_CC"  → "Chase CC"
    if last4.isdigit():
        return "****" + last4 + " (" + account_name + ")"
    else:
        return account_name


def _format_spending(amount):
    # 把支出金额格式化成带符号的字符串，供 CSV 单元格显示
    # 参数 amount 是负数（支出），abs() 取绝对值变正数后再拼字符串
    # 例：amount = -193.32 → abs(-193.32) = 193.32 → 返回 "-$193.32"
    return "-$" + str(abs(amount))


def _format_credits(amount):
    # 把还款/收入金额格式化成带符号的字符串
    # 参数 amount 已经是正数，直接拼字符串
    # 例：amount = 262.0 → 返回 "+$262.0"
    return "+$" + str(amount)


def _format_amount(amount):
    # 根据金额正负自动选择格式，适用于净额（可正可负）的场景
    # 例：amount = -82.3  → 返回 "-$82.3"（净支出）
    #     amount = 200.0  → 返回 "+$200.0"（净收入/退款）
    if amount < 0:
        return "-$" + str(abs(amount))
    else:
        return "+$" + str(amount)


def _write_table1(rows, cc_summary):
    # ── 表格1：Overall Credit Cards Summary ───────────────────
    # 把表格1的所有行追加到 rows 列表，每个元素是一行（列表）
    # rows 是引用传递，直接修改调用方的列表，不需要返回值

    # 表格标题行
    rows.append(["TABLE 1: OVERALL CREDIT CARDS SUMMARY (UP TO DATE)"])

    # 整体汇总三行：卡数、总支出、总还款
    # 例：["Total Credit Cards", 2]
    #     ["Total Spending (All Cards)", "-$1230.50"]
    #     ["Total Credits (All Cards)",  "+$500.00"]
    rows.append(["Total Credit Cards",         cc_summary["total_cards"]])
    rows.append(["Total Spending (All Cards)",  _format_spending(cc_summary["total_spending"])])
    rows.append(["Total Credits (All Cards)",   _format_credits(cc_summary["total_credits"])])
    rows.append([])   # 空行，用于视觉分隔

    # 按信用卡名称分组的小节
    rows.append(["-- Group by Credit Card --"])
    rows.append(["Card Name", "Total Transactions", "Total Spending", "Total Credits"])   # 列标题

    # 遍历每张卡的汇总数据，每张卡写一行
    # 例：["Chase Sapphire", 18, "-$1230.50", "+$500.00"]
    for card in cc_summary["by_card"]:
        card_row = [
            card["name"],                          # 例："Chase Sapphire"
            card["transactions"],                  # 例：18
            _format_spending(card["spending"]),    # 例："-$1230.50"
            _format_credits(card["credits"]),      # 例："+$500.00"
        ]
        rows.append(card_row)

    rows.append([])   # 空行

    # 按消费分类分组的小节（所有信用卡合并统计）
    rows.append(["-- Group by Category (All Cards Combined) --"])
    rows.append(["Category", "Transaction Count", "Spending", "Credits"])   # 列标题

    for cat in cc_summary["by_category"]:
        cat_row = [
            cat["category"],
            cat["count"],
            _format_spending(cat["spending"]),   # 例："-$243.80"
            _format_credits(cat["credits"]),     # 例："+$0.0" 或 "+$25.0"
        ]
        rows.append(cat_row)

    rows.append([])   # 空行
    rows.append([])   # 额外空行，与下一张表格拉开距离


def _write_table2(rows, bank_summary):
    # ── 表格2：Overall Bank Accounts Summary ──────────────────

    net_cash_flow = round(bank_summary["total_income"] + bank_summary["total_spending"] + bank_summary["total_cc_payments"], 2)

    rows.append(["TABLE 2: OVERALL BANK ACCOUNTS SUMMARY (UP TO DATE)"])
    rows.append(["Total Bank Accounts", bank_summary["total_accounts"]])
    rows.append([])

    # 真实收支区（不含 transfer）
    rows.append(["-- Real Transactions (Transfers & CC Payments Excluded) --"])
    rows.append(["Total Spending",     _format_spending(bank_summary["total_spending"])])
    rows.append(["Total Income",       _format_credits(bank_summary["total_income"])])
    rows.append(["Net Cash Flow",      _format_amount(net_cash_flow)])
    rows.append([])

    rows.append(["-- Credit Card Payments (Paid from Bank to Credit Cards) --"])
    rows.append(["Total CC Payments",  _format_spending(bank_summary["total_cc_payments"])])
    rows.append([])

    rows.append(["-- Transfers Between Accounts --"])
    rows.append(["Transfer Out",       _format_spending(bank_summary["total_transfer_out"])])
    rows.append(["Transfer In",        _format_credits(bank_summary["total_transfer_in"])])
    rows.append([])

    rows.append(["-- Group by Bank Name --"])
    rows.append(["Bank Name", "Ending Balance", "Spending", "Income", "Net Cash Flow", "CC Payments", "Transfer Out", "Transfer In"])

    for bank in bank_summary["by_bank"]:
        bank_net = round(bank["income"] + bank["spending"] + bank["cc_payments"], 2)
        rows.append([
            bank["name"],
            "+$" + str(bank["ending_balance"]),
            _format_spending(bank["spending"]),
            _format_credits(bank["income"]),
            _format_amount(bank_net),
            _format_spending(bank["cc_payments"]),
            _format_spending(bank["transfer_out"]),
            _format_credits(bank["transfer_in"]),
        ])

    rows.append([])

    rows.append(["-- Real Transactions by Account --"])
    rows.append(["Account", "Count", "Spending", "Income"])

    for account in bank_summary["by_account"]:
        label = _format_account_label(account["last4"], account["account_name"])
        for cat in account["categories"]:
            if cat["category"] == "Transaction":
                rows.append([label, cat["count"],
                             _format_spending(cat["spending"]),
                             _format_credits(cat["income"])])

    rows.append([])

    rows.append(["-- Credit Card Payments by Account --"])
    rows.append(["Account", "Count", "CC Payments"])

    for account in bank_summary["by_account"]:
        label = _format_account_label(account["last4"], account["account_name"])
        for cat in account["categories"]:
            if cat["category"] == "CC Payment":
                rows.append([label, cat["count"],
                             _format_spending(cat["spending"])])

    rows.append([])

    rows.append(["-- Transfers by Account --"])
    rows.append(["Account", "Count", "Transfer Out", "Transfer In"])

    for account in bank_summary["by_account"]:
        label = _format_account_label(account["last4"], account["account_name"])
        for cat in account["categories"]:
            if cat["category"] == "Transfer":
                rows.append([label, cat["count"],
                             _format_spending(cat["spending"]),
                             _format_credits(cat["income"])])

    rows.append([])
    rows.append([])


def _write_table3(rows, monthly_cc):
    # ── 表格3：Monthly Credit Cards Summary ───────────────────
    # monthly_cc 是一个列表，每个元素是一个月的信用卡汇总字典

    # 表格标题行
    rows.append(["TABLE 3: MONTHLY CREDIT CARDS SUMMARY"])
    rows.append([])   # 空行

    # 遍历每个月的数据，按月逐块写出
    for month_data in monthly_cc:

        # 取出月份字符串
        # 例：month = "2025-05"
        month = month_data["month"]

        # 这个月的标题和汇总行
        # 例：["Month: 2025-05"]
        #     ["Total Spending", "-$820.30"]
        #     ["Total Credits",  "+$500.00"]
        rows.append(["Month: " + month])
        rows.append(["Total Spending", _format_spending(month_data["total_spending"])])
        rows.append(["Total Credits",  _format_credits(month_data["total_credits"])])
        rows.append([])   # 空行

        # 这个月按信用卡分组
        rows.append(["-- Group by Credit Card --"])
        rows.append(["Card Name", "Total Transactions", "Total Spending", "Total Credits"])

        # 遍历这个月每张卡的数据，每张卡写一行
        # 例：["Chase Sapphire", 6, "-$430.20", "+$200.00"]
        for card in month_data["by_card"]:
            rows.append([
                card["name"],
                card["transactions"],
                _format_spending(card["spending"]),
                _format_credits(card["credits"]),
            ])

        rows.append([])   # 空行

        # 这个月按消费分类分组
        rows.append(["-- Group by Category --"])
        rows.append(["Category", "Transaction Count", "Spending", "Credits"])

        for cat in month_data["by_category"]:
            rows.append([
                cat["category"],
                cat["count"],
                _format_spending(cat["spending"]),
                _format_credits(cat["credits"]),
            ])

        rows.append([])   # 每个月结束后加空行，与下一个月分隔

    rows.append([])   # 表格结束后额外加一行，与表格4拉开距离


def _write_table4(rows, monthly_bank):
    # ── 表格4：Monthly Bank Accounts Summary ──────────────────
    # monthly_bank 是一个列表，每个元素是一个月的银行账户汇总字典

    # 表格标题行
    rows.append(["TABLE 4: MONTHLY BANK ACCOUNTS SUMMARY"])
    rows.append([])   # 空行

    # 遍历每个月的数据，按月逐块写出
    for month_data in monthly_bank:

        # 取出月份字符串，例："2025-05"
        month = month_data["month"]

        # 这个月的标题和汇总行
        # 例：["Month: 2025-05"]
        #     ["Total Spending", "-$820.30"]
        #     ["Total Income",   "+$3500.00"]
        net_cash_flow = round(month_data["total_income"] + month_data["total_spending"] + month_data["total_cc_payments"], 2)

        rows.append(["Month: " + month])
        rows.append([])

        rows.append(["-- Real Transactions (Transfers & CC Payments Excluded) --"])
        rows.append(["Total Spending",    _format_spending(month_data["total_spending"])])
        rows.append(["Total Income",      _format_credits(month_data["total_income"])])
        rows.append(["Net Cash Flow",     _format_amount(net_cash_flow)])
        rows.append([])

        rows.append(["-- Credit Card Payments --"])
        rows.append(["Total CC Payments", _format_spending(month_data["total_cc_payments"])])
        rows.append([])

        rows.append(["-- Transfers Between Accounts --"])
        rows.append(["Transfer Out",      _format_spending(month_data["total_transfer_out"])])
        rows.append(["Transfer In",       _format_credits(month_data["total_transfer_in"])])
        rows.append([])

        rows.append(["-- Group by Bank Name --"])
        rows.append(["Bank Name", "Ending Balance", "Spending", "Income", "Net Cash Flow", "CC Payments", "Transfer Out", "Transfer In"])

        for bank in month_data["by_bank"]:
            bank_net = round(bank["income"] + bank["spending"] + bank["cc_payments"], 2)
            rows.append([
                bank["name"],
                "+$" + str(bank["ending_balance"]),
                _format_spending(bank["spending"]),
                _format_credits(bank["income"]),
                _format_amount(bank_net),
                _format_spending(bank["cc_payments"]),
                _format_spending(bank["transfer_out"]),
                _format_credits(bank["transfer_in"]),
            ])

        rows.append([])

        rows.append(["-- Real Transactions by Account --"])
        rows.append(["Account", "Count", "Spending", "Income"])

        for account in month_data["by_account"]:
            label = _format_account_label(account["last4"], account["account_name"])
            for cat in account["categories"]:
                if cat["category"] == "Transaction":
                    rows.append([label, cat["count"],
                                 _format_spending(cat["spending"]),
                                 _format_credits(cat["income"])])

        rows.append([])

        rows.append(["-- Credit Card Payments by Account --"])
        rows.append(["Account", "Count", "CC Payments"])

        for account in month_data["by_account"]:
            label = _format_account_label(account["last4"], account["account_name"])
            for cat in account["categories"]:
                if cat["category"] == "CC Payment":
                    rows.append([label, cat["count"],
                                 _format_spending(cat["spending"])])

        rows.append([])

        rows.append(["-- Transfers by Account --"])
        rows.append(["Account", "Count", "Transfer Out", "Transfer In"])

        for account in month_data["by_account"]:
            label = _format_account_label(account["last4"], account["account_name"])
            for cat in account["categories"]:
                if cat["category"] == "Transfer":
                    rows.append([label, cat["count"],
                                 _format_spending(cat["spending"]),
                                 _format_credits(cat["income"])])

        rows.append([])

    rows.append([])   # 表格结束后额外加一行


def write_all(output_path, cc_summary, bank_summary, monthly_cc, monthly_bank):
    # 把4张表按顺序全部写入同一个 CSV 文件
    # 参数：
    #   output_path  = 输出文件路径，例："/Users/michelle/Desktop/account_summary.csv"
    #   cc_summary   = 表格1 的数据（信用卡整体汇总），可能是 None（无信用卡数据时）
    #   bank_summary = 表格2 的数据（银行账户整体汇总），可能是 None
    #   monthly_cc   = 表格3 的数据（信用卡月度汇总列表）
    #   monthly_bank = 表格4 的数据（银行账户月度汇总列表）

    # 先把所有行收集到一个列表，最后一次性写入文件
    # 这样比每行单独写入更高效，也避免文件写到一半出错
    rows = []

    # 按表格顺序依次追加行，None 检查确保没有数据时跳过对应表格
    if cc_summary:
        _write_table1(rows, cc_summary)    # 表格1：信用卡整体汇总

    if bank_summary:
        _write_table2(rows, bank_summary)  # 表格2：银行账户整体汇总

    if monthly_cc:
        _write_table3(rows, monthly_cc)    # 表格3：信用卡月度汇总

    if monthly_bank:
        _write_table4(rows, monthly_bank)  # 表格4：银行账户月度汇总

    # 一次性把所有行写入 CSV 文件
    #   "w"          → 写入模式，如果文件已存在会覆盖
    #   newline=""   → 让 csv 模块自己处理换行，避免 Windows 上出现多余空行
    #   encoding="utf-8" → 标准 UTF-8 编码（不带 BOM，适合大多数工具打开）
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # writerows() 一次写入多行，比逐行调用 writerow() 更高效
        # 例：rows = [["TABLE 1", ...], ["Total Cards", 2], [], ...]
        writer.writerows(rows)

    # 写出完成后打印路径，让用户知道文件保存在哪里
    print("汇总已保存到：" + output_path)
