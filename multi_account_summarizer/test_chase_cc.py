import csv
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.chase_cc import parse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chase_cc_row(
    tx_date="01/05/2024",
    post_date="01/06/2024",
    description="Amazon",
    category="Shopping",
    tx_type="Sale",
    amount="-50.00",
    memo="",
):
    return {
        "Transaction Date": tx_date,
        "Post Date":        post_date,
        "Description":      description,
        "Category":         category,
        "Type":             tx_type,
        "Amount":           amount,
        "Memo":             memo,
    }


def make_chase_cc_csv(rows):
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    )
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "Transaction Date", "Post Date", "Description",
            "Category", "Type", "Amount", "Memo",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# parse()
# ---------------------------------------------------------------------------

class TestChaseCCParse(unittest.TestCase):

    def tearDown(self):
        if hasattr(self, "_tmp") and os.path.exists(self._tmp):
            os.unlink(self._tmp)

    def _parse(self, rows, account_name="Chase CC", last4="9809"):
        self._tmp = make_chase_cc_csv(rows)
        return parse(self._tmp, account_name, last4)

    # --- 正常交易 ---

    def test_spending_negative_amount(self):
        txs = self._parse([make_chase_cc_row(amount="-85.32")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, -85.32)

    def test_payment_positive_amount(self):
        txs = self._parse([make_chase_cc_row(amount="200.00", category="Payment", tx_type="Payment")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, 200.00)

    def test_transaction_date_parsed(self):
        txs = self._parse([make_chase_cc_row(tx_date="03/22/2024")])
        self.assertEqual(txs[0].date, date(2024, 3, 22))

    def test_description_captured(self):
        txs = self._parse([make_chase_cc_row(description="WHOLE FOODS MARKET")])
        self.assertEqual(txs[0].description, "WHOLE FOODS MARKET")

    def test_category_captured(self):
        txs = self._parse([make_chase_cc_row(category="Dining")])
        self.assertEqual(txs[0].category, "Dining")

    def test_empty_category_defaults_to_uncategorized(self):
        txs = self._parse([make_chase_cc_row(category="")])
        self.assertEqual(txs[0].category, "Uncategorized")

    def test_account_name_and_last4_set(self):
        txs = self._parse([make_chase_cc_row()], account_name="Chase CC", last4="9809")
        self.assertEqual(txs[0].account_name, "Chase CC")
        self.assertEqual(txs[0].account_last4, "9809")

    def test_multiple_transactions_in_order(self):
        rows = [
            make_chase_cc_row(tx_date="01/05/2024", amount="-30.00"),
            make_chase_cc_row(tx_date="01/10/2024", amount="-85.00"),
            make_chase_cc_row(tx_date="01/20/2024", amount="500.00"),
        ]
        txs = self._parse(rows)
        self.assertEqual(len(txs), 3)
        self.assertEqual(txs[0].date, date(2024, 1, 5))
        self.assertEqual(txs[2].date, date(2024, 1, 20))

    # --- 跳过无效行 ---

    def test_empty_amount_skipped(self):
        txs = self._parse([make_chase_cc_row(amount="")])
        self.assertEqual(len(txs), 0)

    def test_non_numeric_amount_skipped(self):
        txs = self._parse([make_chase_cc_row(amount="N/A")])
        self.assertEqual(len(txs), 0)

    def test_invalid_date_skipped(self):
        txs = self._parse([make_chase_cc_row(tx_date="2024-01-05")])
        self.assertEqual(len(txs), 0)

    def test_empty_date_skipped(self):
        txs = self._parse([make_chase_cc_row(tx_date="")])
        self.assertEqual(len(txs), 0)

    # --- 边界情况 ---

    def test_empty_file_returns_empty_list(self):
        txs = self._parse([])
        self.assertEqual(txs, [])

    def test_valid_and_invalid_rows_mixed(self):
        rows = [
            make_chase_cc_row(tx_date="01/05/2024", amount="-30.00"),
            make_chase_cc_row(tx_date="bad-date",   amount="-50.00"),
            make_chase_cc_row(tx_date="01/15/2024", amount="N/A"),
            make_chase_cc_row(tx_date="01/20/2024", amount="-10.00"),
        ]
        txs = self._parse(rows)
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[0].date, date(2024, 1, 5))
        self.assertEqual(txs[1].date, date(2024, 1, 20))

    def test_description_whitespace_stripped(self):
        txs = self._parse([make_chase_cc_row(description="  STARBUCKS  ")])
        self.assertEqual(txs[0].description, "STARBUCKS")

    def test_refund_positive_amount(self):
        txs = self._parse([make_chase_cc_row(amount="25.00", category="Shopping", tx_type="Return")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, 25.00)


if __name__ == "__main__":
    unittest.main()
