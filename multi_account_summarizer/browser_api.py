# ============================================================
# 浏览器入口（供 Pyodide 调用）
# 和 main.py 做同样的事：扫描文件夹 → 识别账户类型 → 调用解析器 → 计算汇总
# 区别：不读 input()、不 print()、不写文件，直接返回可 JSON 序列化的字典
# ============================================================

import csv
import json
from pathlib import Path

from parsers.detector import detect_account_type, extract_account_info
from parsers import chase_cc, amex_cc, citi_cc, chase_bank, wells_fargo_bank
from calculators import credit_card, bank_account


# 每种账户类型对应：解析器模块 + 该放进信用卡列表还是银行列表
_DISPATCH = {
    "chase_cc":        (chase_cc,        "credit"),
    "amex_cc":         (amex_cc,         "credit"),
    "citi_cc":         (citi_cc,         "credit"),
    "citi_costco":     (citi_cc,         "credit"),
    "chase_bank":       (chase_bank,       "bank"),
    "wells_fargo_bank": (wells_fargo_bank, "bank"),
}


def summarize_folder(folder_path):
    # 扫描文件夹里所有 CSV（含子文件夹，对应 Drive 的 Finance/<accountType>/<institution>/ 结构），
    # 识别并解析，返回四张汇总表 + 无法识别的文件列表
    folder = Path(folder_path)
    csv_files = sorted(folder.rglob("*.csv")) + sorted(folder.rglob("*.CSV"))

    all_credit_transactions = []
    all_bank_transactions   = []
    warnings                = []

    for file_path in csv_files:
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            account_type = detect_account_type(reader.fieldnames)

        account_name, last4 = extract_account_info(file_path.name)
        # main.py 的交互式 input() 分支在这里没有意义（浏览器没有终端），
        # 直接退回默认值 "0000"，和 extract_account_info 自身的兜底逻辑一致
        if not last4.isdigit():
            last4 = "0000"

        if account_type is None:
            warnings.append("无法识别文件格式，跳过：" + file_path.name)
            continue

        parser, bucket = _DISPATCH[account_type]
        transactions = parser.parse(str(file_path), account_name, last4)

        if bucket == "credit":
            all_credit_transactions.extend(transactions)
        else:
            all_bank_transactions.extend(transactions)

    return {
        "cc_summary":   credit_card.summarize_overall(all_credit_transactions),
        "monthly_cc":   credit_card.summarize_monthly(all_credit_transactions),
        "bank_summary": bank_account.summarize_overall(all_bank_transactions),
        "monthly_bank": bank_account.summarize_monthly(all_bank_transactions),
        "warnings":     warnings,
    }


def summarize_folder_json(folder_path):
    # 给 Pyodide/JS 调用的入口：直接返回 JSON 字符串，
    # 避免 JS 那边处理 Pyodide 的 PyProxy/toJs 转换细节
    return json.dumps(summarize_folder(folder_path))
