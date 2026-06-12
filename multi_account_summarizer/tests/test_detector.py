import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.detector import detect_account_type, extract_account_info


# ---------------------------------------------------------------------------
# detect_account_type
# ---------------------------------------------------------------------------

class TestDetectAccountType(unittest.TestCase):

    # --- 每种格式能被正确识别 ---

    def test_chase_cc_detected(self):
        fieldnames = [
            "Transaction Date", "Post Date", "Description",
            "Category", "Type", "Amount", "Memo",
        ]
        self.assertEqual(detect_account_type(fieldnames), "chase_cc")

    def test_amex_cc_detected(self):
        fieldnames = [
            "Date", "Description", "Amount", "Extended Details",
            "Appears On Your Statement As", "Address", "City/State",
            "Zip Code", "Country", "Reference", "Category",
        ]
        self.assertEqual(detect_account_type(fieldnames), "amex_cc")

    def test_citi_cc_detected(self):
        fieldnames = ["Status", "Date", "Description", "Debit", "Credit"]
        self.assertEqual(detect_account_type(fieldnames), "citi_cc")

    def test_citi_costco_detected(self):
        fieldnames = [
            "Status", "Date", "Description", "Debit", "Credit", "Member Name"
        ]
        self.assertEqual(detect_account_type(fieldnames), "citi_costco")

    def test_chase_bank_detected(self):
        fieldnames = [
            "Details", "Posting Date", "Description",
            "Amount", "Type", "Balance", "Check or Slip #",
        ]
        self.assertEqual(detect_account_type(fieldnames), "chase_bank")

    def test_wells_fargo_bank_detected(self):
        fieldnames = ["DATE", "DESCRIPTION", "AMOUNT", "CHECK #", "STATUS"]
        self.assertEqual(detect_account_type(fieldnames), "wells_fargo_bank")

    # --- Citi Costco vs Citi CC 优先级 ---

    def test_citi_costco_not_misidentified_as_citi_cc(self):
        # Citi Costco 包含 Citi CC 所有列加上 Member Name
        # 必须识别为 citi_costco，不能误判为 citi_cc
        fieldnames = [
            "Status", "Date", "Description", "Debit", "Credit", "Member Name"
        ]
        result = detect_account_type(fieldnames)
        self.assertEqual(result, "citi_costco")
        self.assertNotEqual(result, "citi_cc")

    # --- Wells Fargo 不和 Citi 混淆（大小写不同）---

    def test_wells_fargo_not_misidentified_as_citi(self):
        # Wells Fargo 的 "STATUS" 是全大写，Citi 的是 "Status"
        # 两者不能互相误判
        wf_fieldnames   = ["DATE", "DESCRIPTION", "AMOUNT", "CHECK #", "STATUS"]
        citi_fieldnames = ["Status", "Date", "Description", "Debit", "Credit"]
        self.assertEqual(detect_account_type(wf_fieldnames),   "wells_fargo_bank")
        self.assertEqual(detect_account_type(citi_fieldnames), "citi_cc")

    # --- 列名不完整时返回 None ---

    def test_partial_chase_cc_columns_returns_none(self):
        fieldnames = ["Transaction Date", "Post Date"]   # 缺少其他列
        self.assertIsNone(detect_account_type(fieldnames))

    def test_partial_amex_columns_returns_none(self):
        fieldnames = ["Extended Details", "Appears On Your Statement As"]   # 缺少其他列
        self.assertIsNone(detect_account_type(fieldnames))

    def test_partial_wells_fargo_columns_returns_none(self):
        fieldnames = ["DATE", "DESCRIPTION", "AMOUNT"]   # 缺少 CHECK # 和 STATUS
        self.assertIsNone(detect_account_type(fieldnames))

    # --- 未知格式和特殊输入 ---

    def test_unknown_format_returns_none(self):
        fieldnames = ["Foo", "Bar", "Baz"]
        self.assertIsNone(detect_account_type(fieldnames))

    def test_empty_list_returns_none(self):
        self.assertIsNone(detect_account_type([]))

    def test_none_input_returns_none(self):
        self.assertIsNone(detect_account_type(None))

    def test_extra_columns_still_matches(self):
        # CSV 可能有额外列，issubset() 仍应正确匹配
        fieldnames = [
            "Transaction Date", "Post Date", "Description",
            "Category", "Type", "Amount", "Memo",
            "Extra Column",   # 额外列
        ]
        self.assertEqual(detect_account_type(fieldnames), "chase_cc")


# ---------------------------------------------------------------------------
# extract_account_info
# ---------------------------------------------------------------------------

class TestExtractAccountInfo(unittest.TestCase):

    def test_standard_chase_cc_filename(self):
        name, last4 = extract_account_info("Chase_CC_9809.csv")
        self.assertEqual(name,  "Chase CC")
        self.assertEqual(last4, "9809")

    def test_wells_fargo_multi_part_filename(self):
        name, last4 = extract_account_info("Wells_Fargo_Bank_1234.csv")
        self.assertEqual(name,  "Wells Fargo Bank")
        self.assertEqual(last4, "1234")

    def test_single_part_filename_defaults_last4(self):
        name, last4 = extract_account_info("Chase.csv")
        self.assertEqual(name,  "Chase")
        self.assertEqual(last4, "0000")

    def test_csv_uppercase_extension_removed(self):
        name, last4 = extract_account_info("Chase_CC_9809.CSV")
        self.assertEqual(name,  "Chase CC")
        self.assertEqual(last4, "9809")

    def test_amex_filename(self):
        name, last4 = extract_account_info("Amex_CC_31004.csv")
        self.assertEqual(name,  "Amex CC")
        self.assertEqual(last4, "31004")

    def test_citi_costco_filename(self):
        name, last4 = extract_account_info("Citi_Costco_5555.csv")
        self.assertEqual(name,  "Citi Costco")
        self.assertEqual(last4, "5555")


if __name__ == "__main__":
    unittest.main()
