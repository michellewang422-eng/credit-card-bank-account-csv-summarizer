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
    date: date                    # 交易日期
    post_date: date               # 入账日期
    description: str              # 商家名字
    category: str                 # 消费分类
    amount: float                 # 金额，负数=支出，正数=收入/还款
    tx_type: str                  # 交易类型
    memo: str                     # 备注


@dataclass
class Summary:                    # 汇总报告
    total_transactions: int       # 总笔数
    total_spending: float         # 总支出（正数显示）
    total_credits: float          # 总收入/还款（正数显示）
    by_category: list             # 分类汇总，每项是 [分类名, 笔数, 净金额（负=支出，正=收入）]


# ============================================================
# 第一步：识别 CSV 格式
# 做法：读第一行的列名，逐个检查必须有的列是否都在
# ============================================================

# 定义一个集合，包含 Chase CSV 文件必须具备的所有列名。
# 用 set 而非 list：后面要做集合差运算（-），效率更高，顺序无关紧要。
REQUIRED_COLUMNS = {
    "Transaction Date", "Post Date", "Description", "Category", "Type", "Amount", "Memo"
}

# 验证 CSV 文件的列名是否符合预期格式。
# 参数 fieldnames：由 csv.DictReader 解析出来的列名列表（第一行的所有字段）。
def validate_format(fieldnames):
    # 如果 fieldnames 是 None，说明 CSV 文件完全为空，连表头行都没有。
    # csv.DictReader 在文件为空时会把 .fieldnames 置为 None。
    if fieldnames is None:
        print("错误：CSV 文件没有列名。")
        sys.exit(1)  # 退出码 1 表示出错（非正常退出）
    # 集合差运算：从"必须有的列"中减去"实际存在的列"，剩下的就是缺失的列名。
    # set(fieldnames) 把列表转成集合，以便做差运算。
    missing = REQUIRED_COLUMNS - set(fieldnames)
    # 如果 missing 非空（即有缺失列），打印错误并退出。
    # str(missing) 会输出类似 {'Amount', 'Memo'} 的字符串，方便用户定位问题。
    if missing:
        print("错误：CSV 格式不对，缺少列：" + str(missing))
        sys.exit(1)  # 以退出码 1 终止，告知调用方程序失败


# ============================================================
# 第二步：读取并解析 CSV 数据
# 做法：逐行读取，把每行文字转成 Transaction 对象
# ============================================================

def parse(file_path):

    with open(file_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # DictReader 让每行变成字典，列名是键
        # {"Transaction Date": "01/05/2024", "Amount": "-85.32", ...}
        validate_format(reader.fieldnames)
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
            post_date=datetime.strptime(row["Post Date"].strip(), "%m/%d/%Y").date(),
            description=row["Description"].strip(),
            category=row.get("Category", "").strip() or "Uncategorized",
            # 分类为空时用 "Uncategorized" 代替
            amount=amount,
            tx_type=row.get("Type", "").strip(),
            memo=row.get("Memo", "").strip(),
        )
        transactions.append(t)      # 加到列表末尾

    return transactions


# ============================================================
# 第三步：计算汇总数字
# 做法：一次循环算出总额，另一次循环按分类统计
# ============================================================

def summarize(transactions):

    # len(transactions) 返回列表长度，为 0 说明没有任何数据，直接报错退出
    # 防止后面对空列表做计算，得出错误结果（比如 sum([]) = 0，看起来正常但实际没意义）
    if len(transactions) == 0:
        print("错误：文件里没有找到任何交易记录。")
        sys.exit(1)

    # ── 计算总支出 ──────────────────────────────────────────────────────────

    # 步骤一：筛选出所有支出（金额为负数的交易）
    # 比如：[-85.32, -6.50, -24.00]
    spending_transactions = [t for t in transactions if t.amount < 0]

    # 步骤二：把每笔支出取反，变成正数，方便相加
    # -(-85.32)=85.32, -(-6.50)=6.50, -(-24.00)=24.00 → [85.32, 6.50, 24.00]
    spending_amounts = [-t.amount for t in spending_transactions]

    # 步骤三：全部加起来
    # 85.32 + 6.50 + 24.00 = 115.82000000000001（浮点误差）
    spending_total = sum(spending_amounts)

    # 步骤四：保留两位小数，消除浮点误差
    # 115.82000000000001 → 115.82
    total_spending = round(spending_total, 2)

    # ── 计算总收入/还款（同样逻辑，方向相反）──────────────────────────────

    # 步骤一：筛选出所有收入/还款（金额为正数的交易）
    # 比如：[250.00, 12.00]
    credit_transactions = [t for t in transactions if t.amount > 0]

    # 步骤二：取出每笔金额
    # [250.00, 12.00]
    credit_amounts = [t.amount for t in credit_transactions]

    # 步骤三：全部加起来
    # 250.00 + 12.00 = 262.0
    credits_total = sum(credit_amounts)

    # 步骤四：保留两位小数，消除浮点误差
    total_credits = round(credits_total, 2)

    # ── 按分类统计 ──────────────────────────────────────────────────────────
    by_category = _group_by_category(transactions)

    return Summary(
        total_transactions=len(transactions),
        total_spending=total_spending,
        total_credits=total_credits,
        by_category=by_category,
    )


def _group_by_category(transactions):

    # ── 第一步：建立两个空字典，准备收集数据 ──────────────────────
    # totals 存每个分类的净金额，counts 存每个分类的交易笔数
    totals = {}
    counts = {}

    # ── 第二步：逐笔交易，按分类累加金额和笔数 ────────────────────
    for t in transactions:

        # 取出这笔交易的分类名，存到 cat 方便后面使用
        cat = t.category

        # 如果这个分类是第一次出现，先给它一个起点（否则 += 会报错）
        if cat not in totals:
            totals[cat] = 0.0   # 金额从 0 开始
            counts[cat] = 0     # 笔数从 0 开始

        # 把这笔交易的金额加进去（负数=支出，正数=收入，符号保留）
        totals[cat] = totals[cat] + t.amount

        # 这个分类多了一笔交易
        counts[cat] = counts[cat] + 1

    # ── 第三步：把两个字典合并成一个列表 ──────────────────────────
    # 字典没办法排序，所以先转成列表，每项格式：[分类名, 笔数, 净金额]
    result = []

    for cat in totals:
        category_name   = cat
        category_count  = counts[cat]
        category_amount = round(totals[cat], 2)  # round 消除浮点误差

        one_row = [category_name, category_count, category_amount]
        result.append(one_row)

    # ── 第四步：按净金额从小到大排序 ──────────────────────────────
    # 净金额最小（负数最大）= 支出最多，排在最前面，方便用户一眼看到
    for i in range(len(result)):
        for j in range(i + 1, len(result)):
            # 比较两行的净金额（每行第三个元素，下标 2）
            if result[i][2] > result[j][2]:
                # 把金额更小的那行换到前面
                result[i], result[j] = result[j], result[i]

    return result


# ============================================================
# 第四步：写出汇总 CSV 文件
# ============================================================

def write_summary(summary, output_path):

    rows = []

    # ── 第一行：报告标题 ───────────────────────────────────────────
    title_row = ["CHASE TRANSACTION SUMMARY"]
    rows.append(title_row)

    # ── 第二行：交易总笔数 ─────────────────────────────────────────
    transaction_count_row = ["Total Transactions", summary.total_transactions]
    rows.append(transaction_count_row)

    # ── 第三行：总支出 ─────────────────────────────────────────────
    # str(229.82) → "229.82"，再拼上 "-$" → "-$229.82"
    spending_str = "-$" + str(summary.total_spending)
    spending_row = ["Total Spending", spending_str]
    rows.append(spending_row)

    # ── 第四行：总收入/还款 ────────────────────────────────────────
    # str(262.0) → "262.0"，再拼上 "+$" → "+$262.0"
    credits_str = "+$" + str(summary.total_credits)
    credits_row = ["Total Credits", credits_str]
    rows.append(credits_row)

    # ── 第五行：空行（起分隔作用，让文件看起来整洁）────────────────
    empty_row = []
    rows.append(empty_row)

    # ── 第六行：分类明细的表头 ─────────────────────────────────────
    category_header_row = ["Category", "Count", "Net Amount"]
    rows.append(category_header_row)

    # ── 第七行起：每个分类占一行 ───────────────────────────────────
    for item in summary.by_category:

        # 取出这个分类的三个数据
        category_name  = item[0]   # 分类名，比如 "Shopping"
        category_count = item[1]   # 笔数，比如 3
        net            = item[2]   # 净金额，比如 -193.32

        # 把净金额格式化成带符号的字符串
        if net < 0:
            # 支出：abs(-193.32) = 193.32，再拼上 "-$" → "-$193.32"
            amount_str = "-$" + str(abs(net))
        else:
            # 收入/还款：250.0 → "+$250.0"
            amount_str = "+$" + str(net)

        # 组成一行，加入 rows
        category_row = [category_name, category_count, amount_str]
        rows.append(category_row)

    # ── 最后：把所有行写入 CSV 文件 ────────────────────────────────
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        # "w" 模式：写入文件，不存在则新建，已存在则覆盖
        writer = csv.writer(f)
        writer.writerows(rows)      # 把所有行一次性写入


# ============================================================
# 主程序：问用户问题，串联所有步骤
# ============================================================

def main():

    # ── 第一步：打印欢迎信息 ───────────────────────────────────────
    print("=== Chase CSV 账单汇总工具 ===")
    print()   # 打印空行，起视觉分隔作用

    # ── 第二步：问用户要输入文件路径 ──────────────────────────────
    # input() 显示提示文字，暂停程序等用户打字，按 Enter 后继续
    # \n 换行，> 是提示符，让界面更清晰
    input_file = input("请输入 Chase CSV 文件路径：\n> ")

    # 去掉用户输入的首尾空格，比如 "  path.csv  " → "path.csv"
    input_file = input_file.strip()

    # 从 Finder 拖入文件时，终端会在空格前自动加 \
    # 比如 "Chase\ January\ 2024.csv" → "Chase January 2024.csv"
    input_file = input_file.replace("\\ ", " ")

    # ── 第三步：检查输入路径是否合法 ──────────────────────────────
    # 用户直接按 Enter，什么都没输入
    if not input_file:
        print("错误：文件路径不能为空。")
        sys.exit(1)   # 退出码 1 表示出错

    # 把字符串路径转成 Path 对象，才能用 .exists() 检查文件是否存在
    input_path = Path(input_file)

    # .exists() 检查文件是否真实存在于硬盘上
    if not input_path.exists():
        print("错误：找不到文件：" + str(input_path))
        sys.exit(1)

    # ── 第四步：问用户要输出文件路径 ──────────────────────────────
    output_file = input("\n请输入输出文件路径（直接按 Enter 使用默认名称）：\n> ")
    output_file = output_file.strip()
    output_file = output_file.replace("\\ ", " ")   # 同上，去掉反斜杠

    # ── 第五步：决定输出文件保存在哪里 ───────────────────────────
    if output_file:
        # 用户自己指定了路径，直接用
        output_path = Path(output_file)
    else:
        # 用户按 Enter 跳过，自动保存到桌面

        # Path.home() 取当前用户的家目录，比如 /Users/michellewang
        home_directory = Path.home()

        # / "Desktop" 拼接出桌面路径：/Users/michellewang/Desktop
        desktop = home_directory / "Desktop"

        # input_path.stem 取原始文件名，不含扩展名
        # 比如 "Chase January 2024.csv" → "Chase January 2024"
        original_filename = input_path.stem

        # 拼上 "_summary.csv"，得到输出文件名
        # 比如 "Chase January 2024" + "_summary.csv" = "Chase January 2024_summary.csv"
        output_filename = original_filename + "_summary.csv"

        # 最终输出路径：/Users/michellewang/Desktop/Chase January 2024_summary.csv
        output_path = desktop / output_filename

    # ── 第六步：读取 CSV 文件，解析成交易列表 ─────────────────────
    print()
    print("正在读取：" + str(input_path))

    # parse() 打开文件，把每行解析成 Transaction 对象，返回列表
    transactions = parse(str(input_path))

    # len() 取列表长度，str() 把数字转成文字才能用 + 拼接
    print("读取到 " + str(len(transactions)) + " 笔交易")

    # ── 第七步：计算汇总，写入输出文件 ───────────────────────────
    # summarize() 统计总支出、总收入、分类明细，返回 Summary 对象
    summary = summarize(transactions)

    # write_summary() 把 Summary 对象写成 CSV 文件
    write_summary(summary, str(output_path))

    # ── 第八步：打印最终结果给用户看 ──────────────────────────────
    print()
    print("汇总已保存到：" + str(output_path))

    transaction_count_str = str(summary.total_transactions)
    spending_str          = str(summary.total_spending)
    credits_str           = str(summary.total_credits)

    print("总笔数：  " + transaction_count_str)
    print("总支出：  -$" + spending_str)
    print("总收入：  +$" + credits_str)


if __name__ == "__main__":
    main()
