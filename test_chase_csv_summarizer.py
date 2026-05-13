import csv
import os
import tempfile
import unittest
from datetime import date

from chase_csv_summarizer import (
    Summary,
    Transaction,
    _group_by_category,
    _parse_credit_card,
    summarize,
    validate_format,
    write_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_row(
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
        "Post Date": post_date,
        "Description": description,
        "Category": category,
        "Type": tx_type,
        "Amount": amount,
        "Memo": memo,
    }


def make_tx(amount, category="Shopping"):
    return Transaction(
        date=date(2024, 1, 5),
        post_date=date(2024, 1, 6),
        description="Test",
        category=category,
        amount=amount,
        tx_type="Sale",
        memo="",
    )


# ---------------------------------------------------------------------------
# validate_format
# ---------------------------------------------------------------------------

class TestValidateFormat(unittest.TestCase):

    def test_all_required_columns_present(self):
        fieldnames = [
            "Transaction Date", "Post Date", "Description",
            "Category", "Type", "Amount", "Memo",
        ]
        # Should not raise or exit
        validate_format(fieldnames)

    def test_missing_column_exits(self):
        fieldnames = ["Transaction Date", "Description", "Amount"]
        with self.assertRaises(SystemExit) as ctx:
            validate_format(fieldnames)
        self.assertEqual(ctx.exception.code, 1)

    def test_none_fieldnames_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            validate_format(None)
        self.assertEqual(ctx.exception.code, 1)


# ---------------------------------------------------------------------------
# _parse_credit_card
# ---------------------------------------------------------------------------

class TestParseCreditCard(unittest.TestCase):

    def test_basic_spending_row(self):
        rows = [make_row(amount="-85.32", category="Dining", memo="tip")]
        txs = _parse_credit_card(rows)
        self.assertEqual(len(txs), 1)
        t = txs[0]
        self.assertEqual(t.date, date(2024, 1, 5))
        self.assertEqual(t.post_date, date(2024, 1, 6))
        self.assertEqual(t.description, "Amazon")
        self.assertEqual(t.category, "Dining")
        self.assertAlmostEqual(t.amount, -85.32)
        self.assertEqual(t.memo, "tip")

    def test_empty_amount_skipped(self):
        rows = [make_row(amount="")]
        txs = _parse_credit_card(rows)
        self.assertEqual(len(txs), 0)

    def test_invalid_amount_skipped(self):
        rows = [make_row(amount="N/A")]
        txs = _parse_credit_card(rows)
        self.assertEqual(len(txs), 0)

    def test_positive_amount_included(self):
        rows = [make_row(amount="200.00", category="Payment")]
        txs = _parse_credit_card(rows)
        self.assertEqual(len(txs), 1)
        self.assertAlmostEqual(txs[0].amount, 200.00)

    def test_missing_category_defaults_to_uncategorized(self):
        rows = [make_row(amount="-10.00", category="")]
        txs = _parse_credit_card(rows)
        self.assertEqual(txs[0].category, "Uncategorized")

    def test_memo_captured(self):
        rows = [make_row(amount="-10.00", memo="business expense")]
        txs = _parse_credit_card(rows)
        self.assertEqual(txs[0].memo, "business expense")


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------

class TestSummarize(unittest.TestCase):

    def test_total_spending_sums_negatives(self):
        txs = [make_tx(-50.0), make_tx(-30.0)]
        s = summarize(txs)
        self.assertAlmostEqual(s.total_spending, 80.0)

    def test_total_credits_sums_positives(self):
        txs = [make_tx(-50.0), make_tx(100.0, category="Payment")]
        s = summarize(txs)
        self.assertAlmostEqual(s.total_credits, 100.0)

    def test_total_transactions_counts_all(self):
        txs = [make_tx(-50.0), make_tx(100.0), make_tx(-20.0)]
        s = summarize(txs)
        self.assertEqual(s.total_transactions, 3)

    def test_empty_transactions_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            summarize([])
        self.assertEqual(ctx.exception.code, 1)


# ---------------------------------------------------------------------------
# _group_by_category
# ---------------------------------------------------------------------------

class TestGroupByCategory(unittest.TestCase):

    def test_positive_amounts_included(self):
        txs = [make_tx(200.0, category="Payment")]
        result = _group_by_category(txs)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "Payment")
        self.assertAlmostEqual(result[0][2], 200.0)

    def test_net_amount_per_category(self):
        txs = [make_tx(-30.0, "Dining"), make_tx(-20.0, "Dining"), make_tx(5.0, "Dining")]
        result = _group_by_category(txs)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0][2], -45.0)

    def test_sorted_ascending_by_net_amount(self):
        txs = [make_tx(-10.0, "A"), make_tx(-50.0, "B"), make_tx(20.0, "C")]
        result = _group_by_category(txs)
        amounts = [r[2] for r in result]
        self.assertEqual(amounts, sorted(amounts))

    def test_count_per_category(self):
        txs = [make_tx(-10.0, "Dining"), make_tx(-20.0, "Dining"), make_tx(-5.0, "Gas")]
        result = _group_by_category(txs)
        by_cat = {r[0]: r[1] for r in result}
        self.assertEqual(by_cat["Dining"], 2)
        self.assertEqual(by_cat["Gas"], 1)


# ---------------------------------------------------------------------------
# write_summary
# ---------------------------------------------------------------------------

class TestWriteSummary(unittest.TestCase):

    def test_output_csv_contains_expected_rows(self):
        summary = Summary(
            total_transactions=3,
            total_spending=80.0,
            total_credits=100.0,
            by_category=[["Dining", 2, -50.0], ["Payment", 1, 100.0]],
        )
        with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            write_summary(summary, path)
            with open(path, newline="", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("CHASE TRANSACTION SUMMARY", content)
            self.assertIn("Total Spending", content)
            self.assertIn("Total Credits", content)
            self.assertIn("Dining", content)
            self.assertIn("Payment", content)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
