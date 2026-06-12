import csv
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.wells_fargo_bank import parse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_wf_row(
    tx_date="01/15/2024",
    description="AMAZON.COM",
    amount="-50.00",
    check_num="",
    status="posted",
):
    return {
        "DATE":        tx_date,
        "DESCRIPTION": description,
        "AMOUNT":      amount,
        "CHECK #":     check_num,
        "STATUS":      status,
    }


def make_wf_csv(rows):
    # 把 rows 写入临时 CSV 文件，返回文件路径
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    )
    writer = csv.DictWriter(
        f, fieldnames=["DATE", "DESCRIPTION", "AMOUNT", "CHECK #", "STATUS"]
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# parse()
# ---------------------------------------------------------------------------

class TestWellsFargoParse(unittest.TestCase):

    def tearDown(self):
        # 每个测试结束后删除临时文件
        if hasattr(self, "_tmp") and os.path.exists(self._tmp):
            os.unlink(self._tmp)

    def _parse(self, rows, account_name="Wells Fargo Bank", last4="1234"):
        self._tmp = make_wf_csv(rows)
        return parse(self._tmp, account_name, last4)

    # --- 正常交易 ---

    def test_withdrawal_negative_amount(self):
        txs = self._parse([make_wf_row(amount="-85.32")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, -85.32)

    def test_deposit_positive_amount(self):
        txs = self._parse([make_wf_row(amount="2500.00", description="DIRECT DEPOSIT")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, 2500.00)

    def test_date_parsed_correctly(self):
        txs = self._parse([make_wf_row(tx_date="03/22/2024")])
        self.assertEqual(txs[0].date, date(2024, 3, 22))

    def test_description_captured(self):
        txs = self._parse([make_wf_row(description="WHOLE FOODS MARKET")])
        self.assertEqual(txs[0].description, "WHOLE FOODS MARKET")

    def test_balance_always_zero(self):
        # Wells Fargo 导出不含余额列，balance 固定为 0.0
        txs = self._parse([make_wf_row(amount="-30.00")])
        self.assertAlmostEqual(txs[0].balance, 0.0)

    def test_account_name_and_last4_set(self):
        txs = self._parse([make_wf_row()], account_name="Wells Fargo Bank", last4="5678")
        self.assertEqual(txs[0].account_name, "Wells Fargo Bank")
        self.assertEqual(txs[0].account_last4, "5678")

    def test_multiple_transactions_returned_in_order(self):
        rows = [
            make_wf_row(tx_date="01/10/2024", amount="-20.00"),
            make_wf_row(tx_date="01/15/2024", amount="-50.00"),
            make_wf_row(tx_date="01/20/2024", amount="1000.00"),
        ]
        txs = self._parse(rows)
        self.assertEqual(len(txs), 3)
        self.assertEqual(txs[0].date, date(2024, 1, 10))
        self.assertEqual(txs[1].date, date(2024, 1, 15))
        self.assertEqual(txs[2].date, date(2024, 1, 20))

    # --- 跳过无效行 ---

    def test_empty_amount_skipped(self):
        txs = self._parse([make_wf_row(amount="")])
        self.assertEqual(len(txs), 0)

    def test_non_numeric_amount_skipped(self):
        txs = self._parse([make_wf_row(amount="N/A")])
        self.assertEqual(len(txs), 0)

    def test_invalid_date_skipped(self):
        txs = self._parse([make_wf_row(tx_date="2024-01-15")])
        self.assertEqual(len(txs), 0)

    def test_empty_date_skipped(self):
        txs = self._parse([make_wf_row(tx_date="")])
        self.assertEqual(len(txs), 0)

    # --- 边界情况 ---

    def test_empty_file_returns_empty_list(self):
        txs = self._parse([])
        self.assertEqual(txs, [])

    def test_valid_and_invalid_rows_mixed(self):
        rows = [
            make_wf_row(tx_date="01/10/2024", amount="-20.00"),
            make_wf_row(tx_date="bad-date",   amount="-30.00"),
            make_wf_row(tx_date="01/20/2024", amount="N/A"),
            make_wf_row(tx_date="01/25/2024", amount="500.00"),
        ]
        txs = self._parse(rows)
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[0].date, date(2024, 1, 10))
        self.assertEqual(txs[1].date, date(2024, 1, 25))

    def test_description_whitespace_stripped(self):
        txs = self._parse([make_wf_row(description="  STARBUCKS  ")])
        self.assertEqual(txs[0].description, "STARBUCKS")

    def test_check_payment_row_parsed(self):
        # CHECK # 列有值时，交易应正常解析
        txs = self._parse([make_wf_row(amount="-250.00", check_num="1042")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, -250.00)


if __name__ == "__main__":
    unittest.main()
