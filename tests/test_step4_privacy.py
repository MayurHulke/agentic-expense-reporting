"""Step 4: PII redaction and EU data-residency enforcement."""
import pytest

from expense_pipeline.models import Employee
from expense_pipeline.privacy import (
    DataResidencyError,
    RegionalDataStore,
    pseudonymize,
    redact_text,
)


def test_card_numbers_are_masked():
    out = redact_text("card 4111 1111 1111 1234 on file")
    assert "4111 1111 1111 1234" not in out
    assert out.endswith("1234 on file")


def test_employee_is_pseudonymized():
    emp = Employee("emp-9", "Jane Doe", "Analyst", "Finance", "US")
    assert pseudonymize(emp) == "employee:emp-9"
    assert "Jane" not in pseudonymize(emp)


def test_eu_employee_data_blocked_from_us_store():
    eu = Employee("emp-200", "Mateo Ruiz", "Sales Rep", "Sales", "EU")
    store = RegionalDataStore(region="US")
    with pytest.raises(DataResidencyError):
        store.write(eu, {"total": "10"})


def test_eu_employee_data_allowed_in_eu_store():
    eu = Employee("emp-200", "Mateo Ruiz", "Sales Rep", "Sales", "EU")
    store = RegionalDataStore(region="EU")
    store.write(eu, {"total": "10"})
    assert store.rows[0]["owner"] == "employee:emp-200"


def test_pipeline_blocks_eu_report_on_us_store(make_pipeline, report):
    with pytest.raises(DataResidencyError):
        make_pipeline(store_region="US").run_report(report("eu_resident"))


def test_pipeline_allows_eu_report_on_eu_store(make_pipeline, report):
    result = make_pipeline(store_region="EU").run_report(report("eu_resident"))
    assert result.decision.paid is True
