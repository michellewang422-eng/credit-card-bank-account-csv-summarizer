import csv
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.chase_bank import parse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chase_bank_row(
    details="DEBIT",
    posting_date="01/15/2024",
    description="AMAZON.COM",
    amount="-50.00",
    tx_type="DEBIT_CARD",
    balance="1500.00",
    check_num="",
):
    return {
        "Details":        details,
        "Posting Date":   posting_date,
        "Description":    description,
        "Amount":         amount,
        "Type":           tx_type,
        "Balance":        balance,
        "Check or Slip #": check_num,
    }


def make_chase_bank_csv(rows):
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    )
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "Details", "Posting Date", "Description",
            "Amount", "Type", "Balance", "Check or Slip #",
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

class TestChaseBankParse(unittest.TestCase):

    def tearDown(self):
        if hasattr(self, "_tmp") and os.path.exists(self._tmp):
            os.unlink(self._tmp)

    def _parse(self, rows, account_name="Chase Bank", last4="6789"):
        self._tmp = make_chase_bank_csv(rows)
        return parse(self._tmp, account_name, last4)

    # --- 正常交易 ---

    def test_withdrawal_negative_amount(self):
        txs = self._parse([make_chase_bank_row(amount="-85.32")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, -85.32)

    def test_deposit_positive_amount(self):
        txs = self._parse([make_chase_bank_row(amount="2500.00", description="DIRECT DEPOSIT")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, 2500.00)

    def test_date_parsed_correctly(self):
        txs = self._parse([make_chase_bank_row(posting_date="03/22/2024")])
        self.assertEqual(txs[0].date, date(2024, 3, 22))

    def test_description_captured(self):
        txs = self._parse([make_chase_bank_row(description="WHOLE FOODS")])
        self.assertEqual(txs[0].description, "WHOLE FOODS")

    def test_balance_captured(self):
        txs = self._parse([make_chase_bank_row(balance="3200.50")])
        self.assertAlmostEqual(txs[0].balance, 3200.50)

    def test_balance_parse_failure_defaults_to_zero(self):
        txs = self._parse([make_chase_bank_row(balance="N/A")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].balance, 0.0)

    def test_account_name_and_last4_set(self):
        txs = self._parse([make_chase_bank_row()], account_name="Chase Bank", last4="6789")
        self.assertEqual(txs[0].account_name, "Chase Bank")
        self.assertEqual(txs[0].account_last4, "6789")

    def test_multiple_transactions_in_order(self):
        rows = [
            make_chase_bank_row(posting_date="01/10/2024", amount="-20.00", balance="980.00"),
            make_chase_bank_row(posting_date="01/15/2024", amount="-50.00", balance="930.00"),
            make_chase_bank_row(posting_date="01/20/2024", amount="1000.00", balance="1930.00"),
        ]
        txs = self._parse(rows)
        self.assertEqual(len(txs), 3)
        self.assertEqual(txs[0].date, date(2024, 1, 10))
        self.assertEqual(txs[2].date, date(2024, 1, 20))

    # --- 跳过无效行 ---

    def test_empty_amount_skipped(self):
        txs = self._parse([make_chase_bank_row(amount="")])
        self.assertEqual(len(txs), 0)

    def test_non_numeric_amount_skipped(self):
        txs = self._parse([make_chase_bank_row(amount="N/A")])
        self.assertEqual(len(txs), 0)

    def test_invalid_date_skipped(self):
        txs = self._parse([make_chase_bank_row(posting_date="2024-01-15")])
        self.assertEqual(len(txs), 0)

    def test_empty_date_skipped(self):
        txs = self._parse([make_chase_bank_row(posting_date="")])
        self.assertEqual(len(txs), 0)

    # --- 边界情况 ---

    def test_empty_file_returns_empty_list(self):
        txs = self._parse([])
        self.assertEqual(txs, [])

    def test_valid_and_invalid_rows_mixed(self):
        rows = [
            make_chase_bank_row(posting_date="01/10/2024", amount="-20.00"),
            make_chase_bank_row(posting_date="bad-date",   amount="-30.00"),
            make_chase_bank_row(posting_date="01/20/2024", amount="N/A"),
            make_chase_bank_row(posting_date="01/25/2024", amount="500.00"),
        ]
        txs = self._parse(rows)
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[0].date, date(2024, 1, 10))
        self.assertEqual(txs[1].date, date(2024, 1, 25))

    def test_description_whitespace_stripped(self):
        txs = self._parse([make_chase_bank_row(description="  STARBUCKS  ")])
        self.assertEqual(txs[0].description, "STARBUCKS")

    def test_check_payment_row_parsed(self):
        txs = self._parse([make_chase_bank_row(amount="-500.00", check_num="1042", tx_type="CHECK_PAID")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, -500.00)


if __name__ == "__main__":
    unittest.main()
