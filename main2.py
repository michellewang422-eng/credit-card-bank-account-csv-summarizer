# ============================================================
# Chase CSV 账单汇总工具
# ============================================================

import csv                  # 读写 CSV 文件
import sys                  # 退出程序
from dataclasses import dataclass       # 自动生成表格功能，省力工具
                                        #   def __init__(self, date, description, ...):
                                        #       self.date = date  ...（不用手写）
from datetime import date, datetime     # 日期类型
from pathlib import Path                # 处理文件路径


# ============================================================
# 数据模板
# ============================================================


@dataclass
class Transaction:                # 一笔交易
    date: date                    # 日期
    description: str              # 商家名字
    category: str                 # 消费分类
    amount: float                 # 金额，负数=支出，正数=收入
    tx_type: str                  # 交易类型


@dataclass
class Summary:                    # 汇总报告
    total_transactions: int       # 总笔数
    total_spending: float         # 总支出（正数）
    by_category: list             # 分类汇总，每项是 [分类名, 笔数, 总金额（负=支出，正=收入）]


# ============================================================
# 第一步：识别 CSV 格式
# 做法：读第一行的列名，逐个检查必须有的列是否都在
# ============================================================



# ============================================================
# 第二步：读取并解析 CSV 数据
# 做法：逐行读取，把每行文字转成 Transaction 对象
# ============================================================

def parse(file_path):

    with open(file_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # DictReader 让每行变成字典，列名是键
        # {"Transaction Date": "01/05/2024", "Amount": "-85.32", ...}
        rows = list(reader)         # 一次性读完所有行，存成列表

    return _parse_credit_card(rows)


def _parse_credit_card(rows):

    transactions = []               # 空列表，用来收集解析好的交易

    for row in rows:                # 逐行处理

        raw_amount = row.get("Amount", "").strip()
        # row.get("Amount", "") 取金额，列不存在时给空文字，不报错

        if not raw_amount:          # 金额是空的，跳过这行
            continue

        try:
            amount = float(raw_amount)
            # float() 把文字变成数字，"-85.32" → -85.32
        except ValueError:          # 文字不是数字（比如 "N/A"），跳过
            continue

        t = Transaction(
            date=datetime.strptime(row["Transaction Date"].strip(), "%m/%d/%Y").date(),
            # strptime 把文字解析成日期，"%m/%d/%Y" 是格式：月/日/年
            # "01/05/2024" → 2024年1月5日，.date() 去掉时分秒
            description=row["Description"].strip(),
            category=row.get("Category", "").strip() or "Uncategorized",
            # 分类为空时用 "Uncategorized" 代替
            amount=amount,
            tx_type=row.get("Type", "").strip(),
        )
        transactions.append(t)      # 加到列表末尾

    return transactions



# ============================================================
# 第三步：计算汇总数字
# 做法：一次循环算出总额，另一次循环按分类统计
# ============================================================

def summarize(transactions):

    if len(transactions) == 0:      # 没有数据，报错退出
        print("错误：文件里没有找到任何交易记录。")
        sys.exit(1)

    total_spending = round(sum(-t.amount for t in transactions if t.amount < 0), 2)
    by_category = _group_by_category(transactions)

    return Summary(
        total_transactions=len(transactions),
        total_spending=total_spending,
        by_category=by_category,
    )


def _group_by_category(transactions):

    totals = {}     # key = 分类名，value = 总支出金额（正数）
    counts = {}     # key = 分类名，value = 笔数

    for t in transactions:
        if t.amount >= 0:
            continue                    # 跳过收入和还款，只统计支出

        cat = t.category

        if cat not in totals:
            totals[cat] = 0.0
            counts[cat] = 0

        totals[cat] += -t.amount        # 取反，把负数变正数存进去
        counts[cat] += 1

    # 把字典整理成列表，每项是 [分类名, 笔数, 总金额]
    result = []
    for cat in totals:
        result.append([cat, counts[cat], round(totals[cat], 2)])

    # 按总金额从大到小排序
    for i in range(len(result)):
        for j in range(i + 1, len(result)):
            if result[j][2] > result[i][2]:
                result[i], result[j] = result[j], result[i]

    return result


# ============================================================
# 第四步：写出汇总 CSV 文件
# ============================================================

def write_summary(summary, output_path):

    rows = []

    rows.append(["CHASE TRANSACTION SUMMARY"])
    rows.append(["Total Transactions", summary.total_transactions])
    rows.append(["Total Spending", "-$" + str(summary.total_spending)])
    rows.append([])

    rows.append(["Category", "Count", "Total Spent"])
    for item in summary.by_category:
        rows.append([item[0], item[1], "$" + str(item[2])])

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        # "w" 模式：写入文件，不存在则新建，已存在则覆盖
        writer = csv.writer(f)
        writer.writerows(rows)      # 把所有行一次性写入


# ============================================================
# 主程序：问用户问题，串联所有步骤
# ============================================================

def main():

    print("=== Chase CSV 账单汇总工具 ===")
    print()

    # --- 问输入文件路径 ---
    input_file = input("请输入 Chase CSV 文件路径：\n> ").strip()
    # input() 显示提示文字，等用户打字，按 Enter 后继续
    # .strip() 去掉前后空格
    input_file = input_file.replace("\\ ", " ")
    # 把路径里的 "\ "（反斜杠+空格）替换成普通空格
    # 终端拖入文件时会自动加反斜杠，这里把它去掉

    if not input_file:
        print("错误：文件路径不能为空。")
        sys.exit(1)

    input_path = Path(input_file)

    if not input_path.exists():
        print("错误：找不到文件：" + str(input_path))
        sys.exit(1)

    # --- 问输出文件路径 ---
    output_file = input("\n请输入输出文件路径（直接按 Enter 使用默认名称）：\n> ").strip()
    output_file = output_file.replace("\\ ", " ")
    # 和输入路径一样，去掉终端拖入时自动加的反斜杠

    if output_file:
        output_path = Path(output_file)
    else:
        desktop = Path.home() / "Desktop"
        # Path.home() 取当前用户的家目录，比如 /Users/michellewang
        # / "Desktop" 拼接桌面路径
        output_path = desktop / (input_path.stem + "_summary.csv")
        # input_path.stem 取原始文件名（不含扩展名）
        # 加上 "_summary.csv"，保存到桌面

    # --- 执行流程 ---
    print()
    print("正在读取：" + str(input_path))

    transactions = parse(str(input_path))

    print("读取到 " + str(len(transactions)) + " 笔交易")

    summary = summarize(transactions)
    write_summary(summary, str(output_path))

    # --- 打印结果 ---
    print()
    print("汇总已保存到：" + str(output_path))
    print("总笔数：  " + str(summary.total_transactions))
    print("总支出：  $" + str(summary.total_spending))


if __name__ == "__main__":
    main()
