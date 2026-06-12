import csv
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.citi_cc import parse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_citi_row(
    status="Cleared",
    tx_date="01/15/2024",
    description="AMAZON",
    debit="50.00",
    credit="",
):
    return {
        "Status":      status,
        "Date":        tx_date,
        "Description": description,
        "Debit":       debit,
        "Credit":      credit,
    }


def make_citi_costco_row(
    status="Cleared",
    tx_date="01/15/2024",
    description="COSTCO WHSE",
    debit="100.00",
    credit="",
    member_name="JOHN DOE",
):
    return {
        "Status":      status,
        "Date":        tx_date,
        "Description": description,
        "Debit":       debit,
        "Credit":      credit,
        "Member Name": member_name,
    }


def make_citi_csv(rows, include_member_name=False):
    fieldnames = ["Status", "Date", "Description", "Debit", "Credit"]
    if include_member_name:
        fieldnames.append("Member Name")

    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    )
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# Citi 普通信用卡
# ---------------------------------------------------------------------------

class TestCitiCCParse(unittest.TestCase):

    def tearDown(self):
        if hasattr(self, "_tmp") and os.path.exists(self._tmp):
            os.unlink(self._tmp)

    def _parse(self, rows, account_name="Citi CC", last4="4321"):
        self._tmp = make_citi_csv(rows)
        return parse(self._tmp, account_name, last4)

    # --- Debit / Credit 金额规则 ---

    def test_debit_stored_as_negative(self):
        # Debit 有值 = 支出，parser 取负数
        txs = self._parse([make_citi_row(debit="85.32", credit="")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, -85.32)

    def test_credit_stored_as_positive(self):
        # 真实 Citi CSV 里 Credit 列是负数（例：-200.00），parser 取反后变成正数
        txs = self._parse([make_citi_row(debit="", credit="-200.00")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, 200.00)

    def test_both_debit_and_credit_empty_skipped(self):
        txs = self._parse([make_citi_row(debit="", credit="")])
        self.assertEqual(len(txs), 0)

    def test_debit_takes_priority_when_both_present(self):
        # Debit 有值时优先读取 Debit，忽略 Credit
        txs = self._parse([make_citi_row(debit="50.00", credit="200.00")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, -50.00)

    # --- 正常字段 ---

    def test_date_parsed_correctly(self):
        txs = self._parse([make_citi_row(tx_date="03/22/2024")])
        self.assertEqual(txs[0].date, date(2024, 3, 22))

    def test_description_captured(self):
        txs = self._parse([make_citi_row(description="WHOLE FOODS")])
        self.assertEqual(txs[0].description, "WHOLE FOODS")

    def test_category_always_uncategorized(self):
        # Citi 没有分类列，固定为 "Uncategorized"
        txs = self._parse([make_citi_row()])
        self.assertEqual(txs[0].category, "Uncategorized")

    def test_account_name_and_last4_set(self):
        txs = self._parse([make_citi_row()], account_name="Citi CC", last4="4321")
        self.assertEqual(txs[0].account_name, "Citi CC")
        self.assertEqual(txs[0].account_last4, "4321")

    def test_multiple_transactions_in_order(self):
        rows = [
            make_citi_row(tx_date="01/05/2024", debit="30.00",  credit=""),
            make_citi_row(tx_date="01/10/2024", debit="",       credit="-500.00"),
            make_citi_row(tx_date="01/20/2024", debit="120.00", credit=""),
        ]
        txs = self._parse(rows)
        self.assertEqual(len(txs), 3)
        self.assertAlmostEqual(txs[0].amount, -30.00)
        self.assertAlmostEqual(txs[1].amount,  500.00)
        self.assertAlmostEqual(txs[2].amount, -120.00)

    # --- 跳过无效行 ---

    def test_non_numeric_debit_skipped(self):
        txs = self._parse([make_citi_row(debit="N/A", credit="")])
        self.assertEqual(len(txs), 0)

    def test_non_numeric_credit_skipped(self):
        txs = self._parse([make_citi_row(debit="", credit="N/A")])
        self.assertEqual(len(txs), 0)

    def test_invalid_date_skipped(self):
        txs = self._parse([make_citi_row(tx_date="2024-01-15")])
        self.assertEqual(len(txs), 0)

    def test_empty_date_skipped(self):
        txs = self._parse([make_citi_row(tx_date="")])
        self.assertEqual(len(txs), 0)

    # --- 边界情况 ---

    def test_empty_file_returns_empty_list(self):
        txs = self._parse([])
        self.assertEqual(txs, [])

    def test_valid_and_invalid_rows_mixed(self):
        rows = [
            make_citi_row(tx_date="01/05/2024", debit="30.00",  credit=""),
            make_citi_row(tx_date="bad-date",   debit="50.00",  credit=""),
            make_citi_row(tx_date="01/15/2024", debit="",       credit=""),
            make_citi_row(tx_date="01/20/2024", debit="",       credit="-500.00"),
        ]
        txs = self._parse(rows)
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[0].date, date(2024, 1, 5))
        self.assertEqual(txs[1].date, date(2024, 1, 20))

    def test_description_whitespace_stripped(self):
        txs = self._parse([make_citi_row(description="  STARBUCKS  ")])
        self.assertEqual(txs[0].description, "STARBUCKS")


# ---------------------------------------------------------------------------
# Citi Costco 信用卡（同一个 parser，多一列 Member Name）
# ---------------------------------------------------------------------------

class TestCitiCostcoParse(unittest.TestCase):

    def tearDown(self):
        if hasattr(self, "_tmp") and os.path.exists(self._tmp):
            os.unlink(self._tmp)

    def _parse(self, rows, account_name="Citi Costco", last4="5555"):
        self._tmp = make_citi_csv(rows, include_member_name=True)
        return parse(self._tmp, account_name, last4)

    def test_debit_stored_as_negative(self):
        txs = self._parse([make_citi_costco_row(debit="100.00", credit="")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, -100.00)

    def test_credit_stored_as_positive(self):
        # 真实 Citi CSV 里 Credit 列是负数（例：-300.00），parser 取反后变成正数
        txs = self._parse([make_citi_costco_row(debit="", credit="-300.00")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, 300.00)

    def test_member_name_column_does_not_break_parsing(self):
        # Member Name 列存在但 parser 不使用，不应影响结果
        txs = self._parse([make_citi_costco_row(member_name="JANE DOE")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, -100.00)

    def test_category_always_uncategorized(self):
        txs = self._parse([make_citi_costco_row()])
        self.assertEqual(txs[0].category, "Uncategorized")

    def test_account_name_and_last4_set(self):
        txs = self._parse([make_citi_costco_row()], account_name="Citi Costco", last4="5555")
        self.assertEqual(txs[0].account_name, "Citi Costco")
        self.assertEqual(txs[0].account_last4, "5555")

    def test_empty_file_returns_empty_list(self):
        txs = self._parse([])
        self.assertEqual(txs, [])


if __name__ == "__main__":
    unittest.main()
