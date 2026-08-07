import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser_api import summarize_folder, summarize_folder_json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_csv(folder, filename, fieldnames, rows):
    path = os.path.join(folder, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def write_chase_cc_csv(folder, filename="Chase_CC_9809.csv", rows=None):
    fieldnames = ["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount", "Memo"]
    rows = rows or [{
        "Transaction Date": "01/05/2024", "Post Date": "01/06/2024",
        "Description": "Amazon", "Category": "Shopping", "Type": "Sale",
        "Amount": "-50.00", "Memo": "",
    }]
    return write_csv(folder, filename, fieldnames, rows)


def write_chase_bank_csv(folder, filename="Chase_Checking_1234.csv", rows=None):
    fieldnames = ["Details", "Posting Date", "Description", "Amount", "Type", "Balance", "Check or Slip #"]
    rows = rows or [{
        "Details": "DEBIT", "Posting Date": "01/10/2024", "Description": "SAFEWAY #456",
        "Amount": "-82.30", "Type": "ACH_DEBIT", "Balance": "3417.70", "Check or Slip #": "",
    }]
    return write_csv(folder, filename, fieldnames, rows)


def write_unrecognized_csv(folder, filename="unknown.csv"):
    return write_csv(folder, filename, ["Foo", "Bar"], [{"Foo": "1", "Bar": "2"}])


# ---------------------------------------------------------------------------
# summarize_folder()
# ---------------------------------------------------------------------------

class TestSummarizeFolder(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.folder = self._tmpdir.name

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_empty_folder_returns_none_summaries(self):
        result = summarize_folder(self.folder)
        self.assertIsNone(result["cc_summary"])
        self.assertIsNone(result["bank_summary"])
        self.assertEqual(result["monthly_cc"], [])
        self.assertEqual(result["monthly_bank"], [])
        self.assertEqual(result["warnings"], [])

    def test_credit_card_csv_populates_cc_summary(self):
        write_chase_cc_csv(self.folder)
        result = summarize_folder(self.folder)
        self.assertIsNotNone(result["cc_summary"])
        self.assertEqual(result["cc_summary"]["total_cards"], 1)
        self.assertAlmostEqual(result["cc_summary"]["total_spending"], 50.00)
        self.assertIsNone(result["bank_summary"])

    def test_bank_csv_populates_bank_summary(self):
        write_chase_bank_csv(self.folder)
        result = summarize_folder(self.folder)
        self.assertIsNotNone(result["bank_summary"])
        self.assertEqual(result["bank_summary"]["total_accounts"], 1)
        self.assertAlmostEqual(result["bank_summary"]["total_spending"], -82.30)
        self.assertIsNone(result["cc_summary"])

    def test_mixed_credit_and_bank_files(self):
        write_chase_cc_csv(self.folder)
        write_chase_bank_csv(self.folder)
        result = summarize_folder(self.folder)
        self.assertIsNotNone(result["cc_summary"])
        self.assertIsNotNone(result["bank_summary"])
        self.assertEqual(len(result["monthly_cc"]), 1)
        self.assertEqual(len(result["monthly_bank"]), 1)

    def test_unrecognized_file_produces_warning_and_is_skipped(self):
        write_chase_cc_csv(self.folder)
        write_unrecognized_csv(self.folder)
        result = summarize_folder(self.folder)
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("unknown.csv", result["warnings"][0])
        self.assertEqual(result["cc_summary"]["total_cards"], 1)

    def test_filename_without_digit_last4_falls_back_to_0000(self):
        # Defensive fallback for files that don't follow the naming
        # convention below — not the expected path, just shouldn't crash.
        write_chase_cc_csv(self.folder, filename="chasecard.csv")
        result = summarize_folder(self.folder)
        self.assertEqual(result["cc_summary"]["by_card"][0]["name"], "chasecard (0000)")

    def test_nested_folders_are_scanned_and_real_last4_used(self):
        # Mirrors the actual Drive layout + naming convention:
        # Finance/<accountType>/<institution>/AccountName_1234.csv
        cc_dir = os.path.join(self.folder, "CreditCard", "Chase")
        os.makedirs(cc_dir)
        write_chase_cc_csv(cc_dir, filename="Chase_Sapphire_4521.csv")

        bank_dir = os.path.join(self.folder, "Bank", "Chase")
        os.makedirs(bank_dir)
        write_chase_bank_csv(bank_dir, filename="Chase_Checking_6789.csv")
        write_chase_bank_csv(bank_dir, filename="Chase_Savings_1122.csv")

        result = summarize_folder(self.folder)

        self.assertEqual(result["cc_summary"]["by_card"][0]["name"], "Chase Sapphire (4521)")

        account_last4s = {a["last4"] for a in result["bank_summary"]["by_account"]}
        self.assertEqual(account_last4s, {"6789", "1122"})

    def test_result_is_json_serializable(self):
        write_chase_cc_csv(self.folder)
        write_chase_bank_csv(self.folder)
        result = summarize_folder(self.folder)
        import json
        json.dumps(result)  # should not raise


class TestSummarizeFolderJson(unittest.TestCase):

    def test_returns_valid_json_string(self):
        with tempfile.TemporaryDirectory() as folder:
            write_chase_cc_csv(folder)
            raw = summarize_folder_json(folder)
            import json
            parsed = json.loads(raw)
            self.assertEqual(parsed["cc_summary"]["total_cards"], 1)


if __name__ == "__main__":
    unittest.main()
