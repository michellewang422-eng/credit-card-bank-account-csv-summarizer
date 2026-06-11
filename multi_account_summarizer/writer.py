# ============================================================
# 把所有表格写入同一个 CSV 文件
# PART 1: Overall Summary（信用卡整体 + 银行账户整体）
# PART 2: Monthly Details（按月，每月信用卡 + 银行账户合并）
# ============================================================

import csv


def _format_account_label(last4, account_name):
    if last4.isdigit():
        return "****" + last4 + " (" + account_name + ")"
    else:
        return account_name


def _format_spending(amount):
    return "-$" + str(abs(amount))


def _format_credits(amount):
    return "+$" + str(amount)


def _format_amount(amount):
    if amount < 0:
        return "-$" + str(abs(amount))
    else:
        return "+$" + str(amount)


# ── Overall Credit Cards ───────────────────────────────────

def _write_overall_cc(rows, cc_summary):
    rows.append(["OVERALL CREDIT CARDS SUMMARY (UP TO DATE)"])
    rows.append(["Total Credit Cards",        cc_summary["total_cards"]])
    rows.append(["Total Spending (All Cards)", _format_spending(cc_summary["total_spending"])])
    rows.append(["Total Credits (All Cards)",  _format_credits(cc_summary["total_credits"])])
    rows.append([])

    rows.append(["-- Group by Credit Card --"])
    rows.append(["Card Name", "Total Transactions", "Total Spending", "Total Credits"])
    for card in cc_summary["by_card"]:
        rows.append([
            card["name"],
            card["transactions"],
            _format_spending(card["spending"]),
            _format_credits(card["credits"]),
        ])
    rows.append([])

    rows.append(["-- Group by Category (All Cards Combined) --"])
    rows.append(["Category", "Transaction Count", "Spending", "Credits"])
    for cat in cc_summary["by_category"]:
        rows.append([
            cat["category"],
            cat["count"],
            _format_spending(cat["spending"]),
            _format_credits(cat["credits"]),
        ])
    rows.append([])
    rows.append([])


# ── Overall Bank Accounts ──────────────────────────────────

def _write_overall_bank(rows, bank_summary):
    net_cash_flow = round(
        bank_summary["total_income"] +
        bank_summary["total_spending"] +
        bank_summary["total_cc_payments"], 2)

    rows.append(["OVERALL BANK ACCOUNTS SUMMARY (UP TO DATE)"])
    rows.append(["Total Bank Accounts", bank_summary["total_accounts"]])
    rows.append(["Net Cash Flow",       _format_amount(net_cash_flow)])
    rows.append([])

    # 真实收支 → 立即接按账户明细
    rows.append(["-- Real Transactions (Transfers & CC Payments Excluded) --"])
    rows.append(["Total Spending", _format_spending(bank_summary["total_spending"])])
    rows.append(["Total Income",   _format_credits(bank_summary["total_income"])])
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

    # 信用卡还款 → 立即接按账户明细
    rows.append(["-- Credit Card Payments (Paid from Bank to Credit Cards) --"])
    rows.append(["Total CC Payments", _format_spending(bank_summary["total_cc_payments"])])
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

    # 转账 → 立即接按账户明细
    rows.append(["-- Transfers Between Accounts --"])
    rows.append(["Transfer Out", _format_spending(bank_summary["total_transfer_out"])])
    rows.append(["Transfer In",  _format_credits(bank_summary["total_transfer_in"])])
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

    # Group by Bank Name 放最後
    rows.append(["-- Group by Bank Name --"])
    rows.append(["Bank Name", "Net Cash Flow", "Income", "Spending", "CC Payments", "Transfer In", "Transfer Out"])
    for bank in bank_summary["by_bank"]:
        bank_net = round(bank["income"] + bank["spending"] + bank["cc_payments"], 2)
        rows.append([
            bank["name"],
            _format_amount(bank_net),
            _format_credits(bank["income"]),
            _format_spending(bank["spending"]),
            _format_spending(bank["cc_payments"]),
            _format_credits(bank["transfer_in"]),
            _format_spending(bank["transfer_out"]),
        ])
    rows.append([])
    rows.append([])


# ── Monthly Credit Cards ───────────────────────────────────

def _write_monthly_cc(rows, month_data):
    rows.append(["Credit Cards"])
    rows.append(["Total Spending", _format_spending(month_data["total_spending"])])
    rows.append(["Total Credits",  _format_credits(month_data["total_credits"])])
    rows.append([])

    rows.append(["-- Group by Credit Card --"])
    rows.append(["Card Name", "Total Transactions", "Total Spending", "Total Credits"])
    for card in month_data["by_card"]:
        rows.append([
            card["name"],
            card["transactions"],
            _format_spending(card["spending"]),
            _format_credits(card["credits"]),
        ])
    rows.append([])

    rows.append(["-- Group by Category --"])
    rows.append(["Category", "Transaction Count", "Spending", "Credits"])
    for cat in month_data["by_category"]:
        rows.append([
            cat["category"],
            cat["count"],
            _format_spending(cat["spending"]),
            _format_credits(cat["credits"]),
        ])
    rows.append([])


# ── Monthly Bank Accounts ──────────────────────────────────

def _write_monthly_bank(rows, month_data):
    net_cash_flow = round(
        month_data["total_income"] +
        month_data["total_spending"] +
        month_data["total_cc_payments"], 2)

    rows.append(["Bank Accounts"])
    rows.append(["Net Cash Flow",  _format_amount(net_cash_flow)])
    rows.append([])

    # 真实收支 → 立即接按账户明细
    rows.append(["-- Real Transactions (Transfers & CC Payments Excluded) --"])
    rows.append(["Total Spending", _format_spending(month_data["total_spending"])])
    rows.append(["Total Income",   _format_credits(month_data["total_income"])])
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

    # 信用卡还款 → 立即接按账户明细
    rows.append(["-- Credit Card Payments --"])
    rows.append(["Total CC Payments", _format_spending(month_data["total_cc_payments"])])
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

    # 转账 → 立即接按账户明细
    rows.append(["-- Transfers Between Accounts --"])
    rows.append(["Transfer Out", _format_spending(month_data["total_transfer_out"])])
    rows.append(["Transfer In",  _format_credits(month_data["total_transfer_in"])])
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

    # Group by Bank Name 放最後
    rows.append(["-- Group by Bank Name --"])
    rows.append(["Bank Name", "Net Cash Flow", "Income", "Spending", "CC Payments", "Transfer In", "Transfer Out"])
    for bank in month_data["by_bank"]:
        bank_net = round(bank["income"] + bank["spending"] + bank["cc_payments"], 2)
        rows.append([
            bank["name"],
            _format_amount(bank_net),
            _format_credits(bank["income"]),
            _format_spending(bank["spending"]),
            _format_spending(bank["cc_payments"]),
            _format_credits(bank["transfer_in"]),
            _format_spending(bank["transfer_out"]),
        ])
    rows.append([])
    rows.append([])


# ── Main entry ─────────────────────────────────────────────

def write_all(output_path, cc_summary, bank_summary, monthly_cc, monthly_bank):
    rows = []

    # ── PART 1: Overall Summary ────────────────────────────
    rows.append(["PART 1: OVERALL SUMMARY"])
    rows.append([])

    if cc_summary:
        _write_overall_cc(rows, cc_summary)

    if bank_summary:
        _write_overall_bank(rows, bank_summary)

    # ── PART 2: Monthly Details ────────────────────────────
    rows.append(["PART 2: MONTHLY DETAILS"])
    rows.append([])

    cc_by_month   = {}
    bank_by_month = {}

    if monthly_cc:
        for m in monthly_cc:
            cc_by_month[m["month"]] = m

    if monthly_bank:
        for m in monthly_bank:
            bank_by_month[m["month"]] = m

    all_months = sorted(set(list(cc_by_month.keys()) + list(bank_by_month.keys())))

    for month in all_months:
        rows.append(["Month: " + month])
        rows.append([])

        if month in cc_by_month:
            _write_monthly_cc(rows, cc_by_month[month])

        if month in bank_by_month:
            _write_monthly_bank(rows, bank_by_month[month])

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print("汇总已保存到：" + output_path)
