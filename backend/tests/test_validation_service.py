import pytest
import pandas as pd
from pathlib import Path
from app.services.validation_service import ValidationService, ValidationResult


def test_valid_telco_csv_validation():
    """Verify validation succeeds on clean Telco customer dataset."""
    sample_path = Path(__file__).resolve().parent / "data" / "sample_50_telco.csv"
    assert sample_path.exists(), "sample_50_telco.csv missing"
    
    with open(sample_path, "rb") as f:
        content = f.read()
        
    result = ValidationService.validate_csv(content)
    assert result.is_valid
    assert result.total_records == 50
    assert result.valid_records == 50
    assert result.invalid_records == 0
    assert result.duplicate_records == 0
    assert result.successfully_processed == 50
    assert len(result.errors) == 0
    assert not result.valid_df.empty
    assert "customer_id" in result.valid_df.columns


def test_empty_csv_validation():
    """Verify empty CSV files are rejected with clear explanation."""
    # 0 bytes
    res1 = ValidationService.validate_csv(b"")
    assert not res1.is_valid
    assert any("Empty CSV file" in err.reasons[0] for err in res1.errors)

    # Whitespace only
    res2 = ValidationService.validate_csv(b"   \n  \n")
    assert not res2.is_valid


def test_missing_required_columns():
    """Verify CSV missing required features is identified and reported."""
    csv_content = """customerID,gender,SeniorCitizen
1234-ABCD,Male,0"""
    result = ValidationService.validate_csv(csv_content)
    assert not result.is_valid
    assert len(result.missing_columns) > 0
    assert "Partner" in result.missing_columns
    assert "Contract" in result.missing_columns
    assert "Missing required columns" in result.errors[0].reasons[0]


def test_extra_columns_reported_as_warnings():
    """Verify extra columns are detected, warned about, and ignored."""
    sample_path = Path(__file__).resolve().parent / "data" / "deepnote_cases.csv"
    df = pd.read_csv(sample_path)
    df["CustomExtraCol1"] = "extra_value"
    df["CustomExtraCol2"] = 12345
    
    csv_content = df.to_csv(index=False)
    result = ValidationService.validate_csv(csv_content)
    
    assert result.is_valid
    assert "CustomExtraCol1" in result.extra_columns
    assert "CustomExtraCol2" in result.extra_columns
    assert any("Extra columns detected and ignored" in w for w in result.warnings)


def test_missing_customer_identifier():
    """Verify records with missing or empty customer IDs are flagged."""
    sample_path = Path(__file__).resolve().parent / "data" / "deepnote_cases.csv"
    df = pd.read_csv(sample_path)
    # Blank out customerID on second record
    df.loc[1, "customerID"] = ""
    
    result = ValidationService.validate_dataframe(df)
    assert result.total_records == 6
    assert result.valid_records == 5
    assert result.invalid_records == 1
    assert any("Missing customer identifier" in r for r in result.errors[0].reasons)


def test_duplicate_customer_records():
    """Verify duplicate customer IDs are counted and explained."""
    sample_path = Path(__file__).resolve().parent / "data" / "deepnote_cases.csv"
    df = pd.read_csv(sample_path)
    # Duplicate first row
    duplicate_row = df.iloc[[0]].copy()
    df_with_dups = pd.concat([df, duplicate_row], ignore_index=True)
    
    result = ValidationService.validate_dataframe(df_with_dups)
    assert result.total_records == 7
    assert result.valid_records == 6
    assert result.duplicate_records == 1
    assert result.successfully_processed == 6
    dup_error = [e for e in result.errors if "Duplicate customer record" in e.reasons[0]]
    assert len(dup_error) == 1


def test_invalid_categorical_and_numerical_values():
    """Verify invalid values in categories or numbers are flagged."""
    sample_path = Path(__file__).resolve().parent / "data" / "deepnote_cases.csv"
    df = pd.read_csv(sample_path, dtype=object).copy()
    
    # Introduce bad values
    df.loc[0, "gender"] = "Alien"
    df.loc[1, "tenure"] = -10
    df.loc[2, "MonthlyCharges"] = "not_a_number"
    df.loc[3, "Contract"] = "Lifetime"
    
    result = ValidationService.validate_dataframe(df)
    assert result.invalid_records == 4
    assert result.valid_records == 2
    
    # Check that reasons explain each failure
    error_reasons = [r for err in result.errors for r in err.reasons]
    assert any("Alien" in r for r in error_reasons)
    assert any("tenure" in r for r in error_reasons)
    assert any("MonthlyCharges" in r for r in error_reasons)
    assert any("Lifetime" in r for r in error_reasons)


def test_format_validation_report():
    """Verify format_report produces the exact expected structure."""
    result = ValidationResult(
        total_records=1000,
        valid_records=965,
        invalid_records=25,
        duplicate_records=10,
        successfully_processed=965
    )
    report = result.format_report()
    expected = (
        "Total records: 1000\n"
        "Valid records: 965\n"
        "Invalid records: 25\n"
        "Duplicate records: 10\n"
        "Successfully processed: 965"
    )
    assert report == expected
