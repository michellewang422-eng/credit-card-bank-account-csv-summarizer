import importlib.util
import io
import sys
import unittest
from datetime import date
from pathlib import Path

# Load the module (filename has a space, so use importlib instead of import)
_spec = importlib.util.spec_from_file_location(
    "chase_summarizer",
    Path(__file__).parent / "Chase_credit card_CSV_summarizer.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

Transaction = _mod.Transaction
Summary = _mod.Summary
validate_format = _mod.validate_format
_parse_credit_card = _mod._parse_credit_card
summarize = _mod.summarize
_group_by_category = _mod._group_by_category
write_summary = _mod.write_summary
REQUIRED_COLUMNS = _mod.REQUIRED_COLUMNS


def _make_row(
    tx_date="01/05/2024",
    post_date="01/06/2024",
    description="AMAZON",
    category="Shopping",
    tx_type="Sale",
    amount="-85.32",
    memo="",
):
    return {
        "Transaction Date": tx_date,
        "Post Date": post_date,
        "Description": description,
        "Category": category,
        "Type": tx_type,
        "Amount": amount,
        "Memo": memo,
    }


class TestValidateFormat(unittest.TestCase):

    def test_ok_when_all_columns_present(self):
        # Should not exit when all required columns are present
        validate_format(list(REQUIRED_COLUMNS))  # no exception / sys.exit

    def test_exits_when_column_missing(self):
        incomplete = list(REQUIRED_COLUMNS - {"Amount"})
        with self.assertRaises(SystemExit):
            validate_format(incomplete)

    def test_exits_when_fieldnames_is_none(self):
        with self.assertRaises(SystemExit):
            validate_format(None)


class TestParseCreditCard(unittest.TestCase):

    def test_basic_spending_row(self):
        rows = [_make_row()]
        txs = _parse_credit_card(rows)
        self.assertEqual(len(txs), 1)
        t = txs[0]
        self.assertEqual(t.date, date(2024, 1, 5))
        self.assertEqual(t.post_date, date(2024, 1, 6))
        self.assertEqual(t.description, "AMAZON")
        self.assertEqual(t.category, "Shopping")
        self.assertEqual(t.amount, -85.32)
        self.assertEqual(t.tx_type, "Sale")
        self.assertEqual(t.memo, "")

    def test_skips_row_with_empty_amount(self):
        rows = [_make_row(amount="")]
        txs = _parse_credit_card(rows)
        self.assertEqual(len(txs), 0)

    def test_skips_row_with_invalid_amount(self):
        rows = [_make_row(amount="N/A")]
        txs = _parse_credit_card(rows)
        self.assertEqual(len(txs), 0)

    def test_positive_amount_not_skipped(self):
        # Payments / credits must be included, not skipped
        rows = [_make_row(amount="200.00", description="PAYMENT", category="Payment")]
        txs = _parse_credit_card(rows)
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0].amount, 200.00)

    def test_defaults_missing_category_to_uncategorized(self):
        rows = [_make_row(category="")]
        txs = _parse_credit_card(rows)
        self.assertEqual(txs[0].category, "Uncategorized")

    def test_reads_memo_field(self):
        rows = [_make_row(memo="some note")]
        txs = _parse_credit_card(rows)
        self.assertEqual(txs[0].memo, "some note")


class TestSummarize(unittest.TestCase):

    def _make_tx(self, amount, category="Shopping"):
        return Transaction(
            date=date(2024, 1, 5),
            post_date=date(2024, 1, 6),
            description="TEST",
            category=category,
            amount=amount,
            tx_type="Sale",
            memo="",
        )

    def test_total_spending_only_counts_negative(self):
        txs = [self._make_tx(-100.0), self._make_tx(-50.0), self._make_tx(200.0)]
        s = summarize(txs)
        self.assertEqual(s.total_spending, 150.0)

    def test_total_credits_only_counts_positive(self):
        txs = [self._make_tx(-100.0), self._make_tx(200.0), self._make_tx(30.0)]
        s = summarize(txs)
        self.assertEqual(s.total_credits, 230.0)

    def test_total_transactions_counts_all(self):
        txs = [self._make_tx(-50.0), self._make_tx(100.0)]
        s = summarize(txs)
        self.assertEqual(s.total_transactions, 2)

    def test_exits_on_empty_list(self):
        with self.assertRaises(SystemExit):
            summarize([])


class TestGroupByCategory(unittest.TestCase):

    def _make_tx(self, amount, category):
        return Transaction(
            date=date(2024, 1, 5),
            post_date=date(2024, 1, 6),
            description="TEST",
            category=category,
            amount=amount,
            tx_type="Sale",
            memo="",
        )

    def test_includes_positive_amounts(self):
        txs = [self._make_tx(200.0, "Payment")]
        result = _group_by_category(txs)
        categories = [r[0] for r in result]
        self.assertIn("Payment", categories)

    def test_net_amount_per_category(self):
        txs = [
            self._make_tx(-80.0, "Food"),
            self._make_tx(-20.0, "Food"),
        ]
        result = _group_by_category(txs)
        food = next(r for r in result if r[0] == "Food")
        self.assertEqual(food[2], -100.0)   # net = -80 + -20

    def test_sorted_ascending_by_net_amount(self):
        txs = [
            self._make_tx(-10.0, "Gas"),
            self._make_tx(-200.0, "Shopping"),
            self._make_tx(300.0, "Payment"),
        ]
        result = _group_by_category(txs)
        amounts = [r[2] for r in result]
        self.assertEqual(amounts, sorted(amounts))  # ascending

    def test_count_per_category(self):
        txs = [
            self._make_tx(-10.0, "Food"),
            self._make_tx(-20.0, "Food"),
            self._make_tx(-5.0, "Gas"),
        ]
        result = _group_by_category(txs)
        food = next(r for r in result if r[0] == "Food")
        self.assertEqual(food[1], 2)


class TestWriteSummary(unittest.TestCase):

    def _make_summary(self):
        return Summary(
            total_transactions=3,
            total_spending=150.0,
            total_credits=200.0,
            by_category=[["Food", 2, -100.0], ["Payment", 1, 200.0]],
        )

    def test_output_contains_expected_rows(self):
        import csv
        import tempfile
        s = self._make_summary()
        with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
            tmp_path = f.name
        write_summary(s, tmp_path)
        with open(tmp_path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        flat = [cell for row in rows for cell in row]
        self.assertIn("CHASE TRANSACTION SUMMARY", flat)
        self.assertIn("3", flat)
        self.assertIn("-$150.0", flat)
        self.assertIn("+$200.0", flat)
        self.assertIn("Food", flat)


if __name__ == "__main__":
    unittest.main()
