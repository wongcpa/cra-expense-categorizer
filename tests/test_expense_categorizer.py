"""
tests/test_expense_categorizer.py
Run: pytest tests/ -v
"""
import sys, os, csv, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from expense_categorizer import categorize, load_transactions, generate_report, CRA_CATEGORIES

F = os.path.join(os.path.dirname(__file__), 'fixtures')

class TestCategorize:
    def test_rogers_is_telephone(self):    assert categorize("ROGERS COMMUNICATIONS WIRELESS") == "TELEPHONE_INTERNET"
    def test_rent_is_rent(self):           assert categorize("RENT JAN 2025 - 100 MAIN ST") == "RENT"
    def test_tim_hortons_is_meals(self):   assert categorize("TIM HORTONS #4821") == "MEALS_ENTERTAINMENT"
    def test_petro_canada_is_vehicle(self):assert categorize("PETRO CANADA FUEL #2219") == "MOTOR_VEHICLE"
    def test_janeapp_is_software(self):    assert categorize("JANEAPP SUBSCRIPTION") == "SOFTWARE_SUBSCRIPTIONS"
    def test_adp_is_payroll(self):         assert categorize("ADP PAYROLL DIRECT DEPOSIT") == "PAYROLL"
    def test_hydro_is_utilities(self):     assert categorize("HYDRO ONE ELECTRICITY") == "UTILITIES"
    def test_intact_is_insurance(self):    assert categorize("INTACT INSURANCE PREMIUM") == "INSURANCE"
    def test_staples_is_office(self):      assert categorize("STAPLES BUSINESS DEPOT") == "OFFICE_SUPPLIES"
    def test_cpa_is_professional(self):    assert categorize("CPA CANADA ANNUAL MEMBERSHIP") == "PROFESSIONAL_FEES"
    def test_medichair_is_medical(self):   assert categorize("MEDICHAIR SUPPLY CO") == "MEDICAL_SUPPLIES"
    def test_cmcc_is_education(self):      assert categorize("CMCC CONTINUING EDUCATION SEMINAR") == "CONTINUING_EDUCATION"
    def test_google_ads_is_advertising(self): assert categorize("GOOGLE ADS - CLINIC MARKETING") == "ADVERTISING"
    def test_td_fee_is_bank(self):         assert categorize("TD BANK MONTHLY FEE") == "BANK_CHARGES"
    def test_unknown_is_uncategorized(self): assert categorize("MYSTERY VENDOR XYZ 999") == "UNCATEGORIZED"
    def test_case_insensitive(self):       assert categorize("rogers communications") == "TELEPHONE_INTERNET"
    def test_microsoft_is_software(self):  assert categorize("MICROSOFT 365 BUSINESS") == "SOFTWARE_SUBSCRIPTIONS"
    def test_impark_is_vehicle(self):      assert categorize("IMPARK PARKING #0088") == "MOTOR_VEHICLE"

class TestCRACategories:
    def test_meals_deductibility_50pct(self):
        assert CRA_CATEGORIES["MEALS_ENTERTAINMENT"]["deductibility"] == 0.5
    def test_all_others_100pct_or_zero(self):
        for k,v in CRA_CATEGORIES.items():
            if k != "MEALS_ENTERTAINMENT" and k != "UNCATEGORIZED":
                assert v["deductibility"] == 1.0
    def test_uncategorized_zero_deductibility(self):
        assert CRA_CATEGORIES["UNCATEGORIZED"]["deductibility"] == 0.0
    def test_all_categories_have_t2125_line(self):
        for k,v in CRA_CATEGORIES.items():
            assert "t2125_line" in v and len(v["t2125_line"]) > 3

class TestLoadTransactions:
    def test_loads_from_fixture(self):
        txns = load_transactions(f'{F}/bank_statement.csv')
        assert len(txns) > 0
    def test_only_expenses_loaded(self):
        txns = load_transactions(f'{F}/bank_statement.csv')
        assert all(t['amount'] > 0 for t in txns)
    def test_required_keys(self):
        txns = load_transactions(f'{F}/bank_statement.csv')
        assert {'date','description','amount'}.issubset(txns[0].keys())
    def test_amounts_are_positive_floats(self):
        txns = load_transactions(f'{F}/bank_statement.csv')
        assert all(isinstance(t['amount'], float) and t['amount'] > 0 for t in txns)
    def test_credits_excluded(self):
        """Patient payments (credits) should not appear in expense list."""
        txns = load_transactions(f'{F}/bank_statement.csv')
        descs = [t['description'].upper() for t in txns]
        assert not any('PATIENT PAYMENT' in d for d in descs)

class TestGenerateReport:
    @pytest.fixture
    def report(self):
        txns = load_transactions(f'{F}/bank_statement.csv')
        return generate_report(txns)

    def test_returns_list(self, report):     assert isinstance(report, list)
    def test_all_have_category(self, report): assert all('category' in t for t in report)
    def test_all_have_deductible(self, report): assert all('deductible_amount' in t for t in report)
    def test_deductible_lte_amount(self, report):
        assert all(t['deductible_amount'] <= t['amount'] + 0.01 for t in report)
    def test_meals_50pct_deductible(self, report):
        meals = [t for t in report if t['category'] == 'MEALS_ENTERTAINMENT']
        assert all(abs(t['deductible_amount'] - t['amount']*0.5) < 0.01 for t in meals)
    def test_uncategorized_zero_deductible(self, report):
        uncats = [t for t in report if t['category'] == 'UNCATEGORIZED']
        assert all(t['deductible_amount'] == 0.0 for t in uncats)
    def test_has_t2125_line(self, report):
        assert all('t2125_line' in t for t in report)
    def test_default_assumes_full_business_use(self, report):
        vehicle = [t for t in report if t['category'] == 'MOTOR_VEHICLE']
        assert vehicle and all(t['deductible_amount'] == t['amount'] for t in vehicle)

class TestBusinessUse:
    def test_business_use_applied_to_vehicle_and_phone(self):
        txns = [{'date':'2025-01-01','description':'PETRO CANADA FUEL','amount':100.0},
                {'date':'2025-01-02','description':'ROGERS COMMUNICATIONS','amount':80.0},
                {'date':'2025-01-03','description':'STAPLES BUSINESS DEPOT','amount':50.0}]
        r = generate_report(txns, {'MOTOR_VEHICLE':0.6, 'TELEPHONE_INTERNET':0.5})
        assert [t['deductible_amount'] for t in r] == [60.0, 40.0, 50.0]
        assert [t['deductibility_pct'] for t in r] == [60.0, 50.0, 100.0]
    def test_business_use_does_not_affect_meals(self):
        r = generate_report([{'date':'2025-01-01','description':'TIM HORTONS','amount':20.0}],
                            {'MOTOR_VEHICLE':0.5})
        assert r[0]['deductible_amount'] == 10.0

class TestIntegration:
    def test_full_pipeline(self, tmp_path):
        from expense_categorizer import export_csv
        txns = load_transactions(f'{F}/bank_statement.csv')
        report = generate_report(txns)
        out = str(tmp_path / 'categorized.csv')
        export_csv(report, out)
        assert os.path.exists(out)
        with open(out, newline='', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        assert len(rows) > 0
        assert 'category' in rows[0]
        assert 'deductible_amount' in rows[0]
