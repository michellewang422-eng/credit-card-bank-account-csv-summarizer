# ============================================================
# 主程序入口
# 做法：扫描文件夹 → 识别每个 CSV 的账户类型 → 调用对应解析器
# ============================================================

# 导入 csv 模块，用于读取 CSV 文件的列名（只读第一行，判断文件格式）
import csv

# 导入 sys 模块，用于在出错时强制退出程序
# 例：sys.exit(1) 表示以错误状态退出，1 代表"异常退出"
import sys

# 导入 Path，用于处理文件和文件夹路径
# Path 比直接拼字符串更安全，在 Mac、Windows 上都能正常工作
# 例：Path("/Users/michelle/Desktop") / "output.csv"
#      → Path("/Users/michelle/Desktop/output.csv")
from pathlib import Path

# 从 parsers 包导入识别函数和文件名解析函数
# detect_account_type：根据列名判断是哪种账户格式，例："chase_cc"
# extract_account_info：从文件名提取账户名和后四位，例："Chase CC", "9809"
from parsers.detector import detect_account_type, extract_account_info

# 导入五种账户的解析器，每种都有一个 parse() 函数
from parsers import chase_cc, amex_cc, citi_cc, chase_bank, wells_fargo_bank

# 导入两种计算器，分别处理信用卡和银行账户的汇总计算
from calculators import credit_card, bank_account

# 导入写出函数，把四张汇总表写入一个 CSV 文件
from writer import write_all


def load_all_files(folder_path):
    # 扫描指定文件夹，找出所有 CSV 文件并返回路径列表

    # Path(folder_path) 把字符串路径转成 Path 对象，方便后续操作
    # 例：folder_path = "/Users/michelle/Downloads/statements"
    folder = Path(folder_path)

    # glob("*.csv") 找出文件夹里所有 .csv 文件，返回 Path 对象列表
    # 同时用 glob("*.CSV") 兼容大写扩展名，两个列表用 + 合并
    # 例：[Path(".../Chase_CC_9809.csv"), Path(".../Amex_Gold_1234.csv")]
    csv_files = list(folder.glob("*.csv")) + list(folder.glob("*.CSV"))

    # 如果文件夹里没有任何 CSV 文件，打印错误信息并退出程序
    if not csv_files:
        print("错误：文件夹里没有找到任何 CSV 文件。")
        sys.exit(1)   # 强制退出，1 表示异常退出

    # 打印找到的文件数量，让用户知道程序读到了几个文件
    # 例：找到 3 个 CSV 文件
    print("找到 " + str(len(csv_files)) + " 个 CSV 文件")
    return csv_files


def parse_all_files(csv_files):
    # 逐个文件读取，识别账户类型，调用对应解析器，汇总所有交易记录

    all_credit_transactions = []   # 收集所有信用卡交易，最终传给 credit_card 计算器
    all_bank_transactions   = []   # 收集所有银行账户交易，最终传给 bank_account 计算器

    # 遍历每一个 CSV 文件
    for file_path in csv_files:

        # 打开文件，只读取第一行列名，用于识别账户格式
        # 不需要读全部内容，只需要 reader.fieldnames（列名列表）
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            # reader.fieldnames 是第一行的列名列表
            # 例：["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount", "Memo"]
            account_type = detect_account_type(reader.fieldnames)

        # 从文件名里提取账户名称和后四位
        # file_path.name 只取文件名部分（不含路径）
        # 例：file_path = Path(".../Chase_CC_9809.csv") → filename = "Chase_CC_9809.csv"
        filename            = file_path.name
        account_name, last4 = extract_account_info(filename)
        # 例：account_name = "Chase CC"，last4 = "9809"

        # 如果 detect_account_type 返回 None，说明这个文件格式不认识，跳过
        if account_type is None:
            print("警告：无法识别文件格式，跳过：" + filename)
            continue   # 跳过这个文件，继续处理下一个

        # 如果文件名不符合 AccountName_Last4.csv 格式（last4 不是数字），
        # 暂停并询问用户提供正确的账户信息
        if not last4.isdigit():
            print("\n⚠️  文件名不符合格式（需要：AccountName_Last4.csv）：" + filename)
            user_name = input("请输入此账户的名称（直接按 Enter 使用 \"" + account_name + "\"）：").strip()
            user_last4 = input("请输入卡号/账户后4位（直接按 Enter 使用 \"0000\"）：").strip()
            if user_name:
                account_name = user_name
            if user_last4.isdigit():
                last4 = user_last4
            else:
                last4 = "0000"
            print()

        # 打印当前正在处理的文件，让用户看到进度
        # 例：正在读取：Chase_CC_9809.csv（chase_cc）
        print("正在读取：" + filename + "（" + account_type + "）")

        # 根据识别出的账户类型，调用对应的解析器
        # 每个解析器的 parse() 返回一个交易对象列表
        # extend() 把列表里的元素逐个加入总列表（不是嵌套列表）
        # 例：all_credit_transactions.extend([交易A, 交易B]) → 追加两条记录

        if account_type == "chase_cc":
            # 调用 Chase 信用卡解析器，结果加入信用卡总列表
            transactions = chase_cc.parse(str(file_path), account_name, last4)
            all_credit_transactions.extend(transactions)

        elif account_type == "amex_cc":
            # 调用 Amex 信用卡解析器，结果加入信用卡总列表
            transactions = amex_cc.parse(str(file_path), account_name, last4)
            all_credit_transactions.extend(transactions)

        elif account_type in ("citi_cc", "citi_costco"):
            # Citi 普通卡和 Citi Costco 卡共用同一个解析器（列格式相同）
            transactions = citi_cc.parse(str(file_path), account_name, last4)
            all_credit_transactions.extend(transactions)

        elif account_type == "chase_bank":
            # 调用 Chase 银行账户解析器，结果加入银行账户总列表
            transactions = chase_bank.parse(str(file_path), account_name, last4)
            all_bank_transactions.extend(transactions)

        elif account_type == "wells_fargo_bank":
            # 调用 Wells Fargo 银行账户解析器，结果加入银行账户总列表
            transactions = wells_fargo_bank.parse(str(file_path), account_name, last4)
            all_bank_transactions.extend(transactions)

    # 返回两个列表：所有信用卡交易、所有银行账户交易
    return all_credit_transactions, all_bank_transactions


def main():
    # 主流程：引导用户输入路径 → 读取文件 → 计算汇总 → 写出结果

    print("=== 多账户信用卡 & 银行账户汇总工具 ===")
    print()

    # 第一步：让用户输入存放 CSV 文件的文件夹路径
    # input() 等待用户在终端输入一行文字，strip() 去掉首尾空格
    # 例：用户输入 "/Users/michelle/Downloads/statements" → input_folder = 同上
    input_folder = input("请输入存放 CSV 文件的文件夹路径：\n> ").strip()

    # 处理 Mac 上路径里的转义空格：Finder 拖入终端时空格会变成 "\ "
    # 例："/Users/michelle/My\ Documents" → "/Users/michelle/My Documents"
    input_folder = input_folder.replace("\\ ", " ")

    # 如果用户直接按了 Enter 没有输入任何内容，报错退出
    if not input_folder:
        print("错误：文件夹路径不能为空。")
        sys.exit(1)

    # 把字符串路径转成 Path 对象，并检查文件夹是否真实存在
    folder_path = Path(input_folder)
    if not folder_path.exists():
        # 文件夹不存在，打印错误信息并退出
        print("错误：找不到文件夹：" + str(folder_path))
        sys.exit(1)

    # 第二步：让用户输入输出文件的保存路径
    # 如果用户直接按 Enter，默认保存到桌面的 account_summary.csv
    output_file = input("\n请输入输出文件路径（直接按 Enter 保存到桌面）：\n> ").strip()
    output_file = output_file.replace("\\ ", " ")   # 同样处理转义空格

    if output_file:
        # 用户指定了路径，直接用
        # 例：output_file = "/Users/michelle/reports/2025.csv"
        output_path = Path(output_file)
    else:
        # 用户没有输入，默认保存到桌面
        # Path.home() 返回当前用户的主目录，例：Path("/Users/michelle")
        # / "Desktop" 拼接子路径，例：Path("/Users/michelle/Desktop")
        desktop     = Path.home() / "Desktop"
        output_path = desktop / "account_summary.csv"

    # 第三步：读取并解析所有 CSV 文件
    print()
    csv_files = load_all_files(str(folder_path))
    # parse_all_files 返回两个列表：信用卡交易 和 银行账户交易
    credit_transactions, bank_transactions = parse_all_files(csv_files)

    # 打印解析结果，让用户确认读到了多少笔交易
    # 例：信用卡交易：312 笔
    #     银行账户交易：89 笔
    print()
    print("信用卡交易：" + str(len(credit_transactions)) + " 笔")
    print("银行账户交易：" + str(len(bank_transactions)) + " 笔")

    # 第四步：调用计算器，生成四张汇总表的数据
    print()
    print("正在计算汇总...")

    cc_summary   = credit_card.summarize_overall(credit_transactions)   # 表格1：信用卡整体汇总
    monthly_cc   = credit_card.summarize_monthly(credit_transactions)   # 表格3：信用卡月度汇总
    bank_summary = bank_account.summarize_overall(bank_transactions)    # 表格2：银行账户整体汇总
    monthly_bank = bank_account.summarize_monthly(bank_transactions)    # 表格4：银行账户月度汇总

    # 第五步：把四张表写入同一个 CSV 输出文件
    # write_all 负责格式化并写出，main 不需要关心写出的细节
    write_all(str(output_path), cc_summary, bank_summary, monthly_cc, monthly_bank)

    # 第六步：在终端打印结果摘要，让用户快速看到关键数字
    print()
    if cc_summary:
        # 例：信用卡账户数：  2
        #     信用卡总支出：  -$1230.50
        #     信用卡总还款：  +$500.00
        print("信用卡账户数：  " + str(cc_summary["total_cards"]))
        print("信用卡总支出：  -$" + str(cc_summary["total_spending"]))
        print("信用卡总还款：  +$" + str(cc_summary["total_credits"]))
    if bank_summary:
        # 例：银行账户数：    2
        #     银行总支出：    -$820.30
        #     银行总收入：    +$3500.00
        print("银行账户数：    " + str(bank_summary["total_accounts"]))
        print("银行总支出：    -$" + str(bank_summary["total_spending"]))
        print("银行总收入：    +$" + str(bank_summary["total_income"]))


# 这是 Python 的标准写法：只有直接运行这个文件时才执行 main()
# 如果这个文件被其他模块 import，main() 不会自动运行
# 例：直接运行 → python main.py → __name__ == "__main__" → 执行 main()
#     被导入时 → import main    → __name__ == "main"      → 不执行
if __name__ == "__main__":
    main()
