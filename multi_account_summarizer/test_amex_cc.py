import csv
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.amex_cc import parse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_amex_row(
    tx_date="01/15/2024",
    description="AMAZON",
    amount="85.32",       # Amex 正数 = 支出（parser 会取反）
    extended_details="",
    appears_as="AMAZON.COM",
    address="",
    city_state="SEATTLE WA",
    zip_code="98101",
    country="UNITED STATES",
    reference="",
    category="Shopping",
):
    return {
        "Date":                        tx_date,
        "Description":                 description,
        "Amount":                      amount,
        "Extended Details":            extended_details,
        "Appears On Your Statement As": appears_as,
        "Address":                     address,
        "City/State":                  city_state,
        "Zip Code":                    zip_code,
        "Country":                     country,
        "Reference":                   reference,
        "Category":                    category,
    }


def make_amex_csv(rows):
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    )
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "Date", "Description", "Amount", "Extended Details",
            "Appears On Your Statement As", "Address", "City/State",
            "Zip Code", "Country", "Reference", "Category",
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

class TestAmexCCParse(unittest.TestCase):

    def tearDown(self):
        if hasattr(self, "_tmp") and os.path.exists(self._tmp):
            os.unlink(self._tmp)

    def _parse(self, rows, account_name="Amex CC", last4="31004"):
        self._tmp = make_amex_csv(rows)
        return parse(self._tmp, account_name, last4)

    # --- 金额方向（Amex 和 Chase 相反，parser 会取反）---

    def test_spending_stored_as_negative(self):
        # Amex 原始正数 +85.32 → parser 取反 → -85.32
        txs = self._parse([make_amex_row(amount="85.32")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, -85.32)

    def test_payment_stored_as_positive(self):
        # Amex 原始负数 -200.00（还款）→ parser 取反 → +200.00
        txs = self._parse([make_amex_row(amount="-200.00", category="Payment")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, 200.00)

    def test_zero_amount_stored_as_zero(self):
        txs = self._parse([make_amex_row(amount="0.00")])
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, 0.00)

    # --- 正常字段 ---

    def test_date_parsed_correctly(self):
        txs = self._parse([make_amex_row(tx_date="03/22/2024")])
        self.assertEqual(txs[0].date, date(2024, 3, 22))

    def test_description_captured(self):
        txs = self._parse([make_amex_row(description="WHOLE FOODS")])
        self.assertEqual(txs[0].description, "WHOLE FOODS")

    def test_category_captured(self):
        txs = self._parse([make_amex_row(category="Dining")])
        self.assertEqual(txs[0].category, "Dining")

    def test_empty_category_defaults_to_uncategorized(self):
        txs = self._parse([make_amex_row(category="")])
        self.assertEqual(txs[0].category, "Uncategorized")

    def test_account_name_and_last4_set(self):
        txs = self._parse([make_amex_row()], account_name="Amex CC", last4="31004")
        self.assertEqual(txs[0].account_name, "Amex CC")
        self.assertEqual(txs[0].account_last4, "31004")

    def test_multiple_transactions_in_order(self):
        rows = [
            make_amex_row(tx_date="01/05/2024", amount="30.00"),
            make_amex_row(tx_date="01/10/2024", amount="85.00"),
            make_amex_row(tx_date="01/20/2024", amount="-500.00"),
        ]
        txs = self._parse(rows)
        self.assertEqual(len(txs), 3)
        self.assertEqual(txs[0].date, date(2024, 1, 5))
        self.assertEqual(txs[2].date, date(2024, 1, 20))
        self.assertAlmostEqual(txs[2].amount, 500.00)   # 还款取反后为正

    # --- 跳过无效行 ---

    def test_empty_amount_skipped(self):
        txs = self._parse([make_amex_row(amount="")])
        self.assertEqual(len(txs), 0)

    def test_non_numeric_amount_skipped(self):
        txs = self._parse([make_amex_row(amount="N/A")])
        self.assertEqual(len(txs), 0)

    def test_invalid_date_skipped(self):
        txs = self._parse([make_amex_row(tx_date="2024-01-15")])
        self.assertEqual(len(txs), 0)

    def test_empty_date_skipped(self):
        txs = self._parse([make_amex_row(tx_date="")])
        self.assertEqual(len(txs), 0)

    # --- 边界情况 ---

    def test_empty_file_returns_empty_list(self):
        txs = self._parse([])
        self.assertEqual(txs, [])

    def test_valid_and_invalid_rows_mixed(self):
        rows = [
            make_amex_row(tx_date="01/05/2024", amount="30.00"),
            make_amex_row(tx_date="bad-date",   amount="50.00"),
            make_amex_row(tx_date="01/15/2024", amount="N/A"),
            make_amex_row(tx_date="01/20/2024", amount="10.00"),
        ]
        txs = self._parse(rows)
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[0].date, date(2024, 1, 5))
        self.assertEqual(txs[1].date, date(2024, 1, 20))

    def test_description_whitespace_stripped(self):
        txs = self._parse([make_amex_row(description="  STARBUCKS  ")])
        self.assertEqual(txs[0].description, "STARBUCKS")


if __name__ == "__main__":
    unittest.main()
