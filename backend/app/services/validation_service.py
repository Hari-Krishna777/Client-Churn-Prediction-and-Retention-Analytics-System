import io
import math
from typing import Any
import pandas as pd
from dataclasses import dataclass, field

from app.config import (
    ALL_INPUT_FEATURES,
    INPUT_NUMERIC_FEATURES,
    INPUT_CATEGORICAL_FEATURES,
    VALID_CATEGORICAL_VALUES,
    CUSTOMER_ID_COLUMNS
)


@dataclass
class RecordValidationError:
    row_index: int
    customer_id: str | None
    reasons: list[str]


@dataclass
class ValidationResult:
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    duplicate_records: int = 0
    successfully_processed: int = 0
    errors: list[RecordValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    valid_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    missing_columns: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.valid_records > 0 and len(self.missing_columns) == 0

    def format_report(self) -> str:
        report = (
            f"Total records: {self.total_records}\n"
            f"Valid records: {self.valid_records}\n"
            f"Invalid records: {self.invalid_records}\n"
            f"Duplicate records: {self.duplicate_records}\n"
            f"Successfully processed: {self.successfully_processed}"
        )
        return report


class ValidationService:
    """
    Reusable validation service for customer churn prediction data.
    Validates CSV schema, data types, value boundaries, customer identifiers,
    missing values, duplicate records, and extra columns.
    """

    @classmethod
    def read_csv(cls, file_content: bytes | str) -> pd.DataFrame:
        """Parse raw CSV bytes or string into a DataFrame with string dtypes."""
        if isinstance(file_content, bytes):
            buffer = io.BytesIO(file_content)
        else:
            buffer = io.StringIO(file_content)

        try:
            df = pd.read_csv(buffer, dtype=str, keep_default_na=False)
        except pd.errors.EmptyDataError:
            raise ValueError("Empty CSV file: file contains no data or headers")
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file: {str(e)}")

        return df

    @classmethod
    def validate_csv(cls, file_content: bytes | str) -> ValidationResult:
        """Validate raw CSV content and produce a detailed ValidationResult."""
        try:
            df = cls.read_csv(file_content)
        except ValueError as e:
            result = ValidationResult()
            result.errors.append(RecordValidationError(row_index=0, customer_id=None, reasons=[str(e)]))
            return result

        return cls.validate_dataframe(df)

    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame) -> ValidationResult:
        """
        Validate a pandas DataFrame against the IBM Telco schema requirements.
        Returns a ValidationResult containing valid records and detailed error explanations.
        """
        result = ValidationResult()
        result.total_records = len(df)

        if df.empty:
            result.errors.append(
                RecordValidationError(
                    row_index=0,
                    customer_id=None,
                    reasons=["Empty CSV file: dataset contains 0 records"]
                )
            )
            return result

        # 1. Identify Customer Identifier column
        id_column = None
        for col_name in CUSTOMER_ID_COLUMNS:
            if col_name in df.columns:
                id_column = col_name
                break

        # 2. Check for missing required columns
        missing_required = []
        for feat in ALL_INPUT_FEATURES:
            if feat not in df.columns:
                missing_required.append(feat)

        if id_column is None:
            missing_required.insert(0, "customerID")

        if missing_required:
            result.missing_columns = missing_required
            result.errors.append(
                RecordValidationError(
                    row_index=0,
                    customer_id=None,
                    reasons=[f"Missing required columns: {', '.join(missing_required)}"]
                )
            )
            return result

        # 3. Detect extra columns
        expected_cols = set(ALL_INPUT_FEATURES) | {id_column, "Churn"}
        extra_cols = [c for c in df.columns if c not in expected_cols]
        if extra_cols:
            result.extra_columns = extra_cols
            result.warnings.append(f"Extra columns detected and ignored: {', '.join(extra_cols)}")

        # 4. Row-level validation
        seen_customer_ids: dict[str, int] = {}
        valid_rows: list[dict[str, Any]] = []

        for idx, row in df.iterrows():
            row_num = idx + 1  # 1-based line number (header is row 0)
            row_errors: list[str] = []

            # A. Customer Identifier validation
            raw_id = row[id_column]
            cust_id = str(raw_id).strip() if raw_id is not None else ""
            if not cust_id:
                row_errors.append("Missing customer identifier: identifier cannot be blank or empty")
                cust_id_label = None
            else:
                cust_id_label = cust_id
                if cust_id in seen_customer_ids:
                    prev_row = seen_customer_ids[cust_id]
                    row_errors.append(
                        f"Duplicate customer record: customer ID '{cust_id}' was already processed at row {prev_row}"
                    )
                    result.duplicate_records += 1
                    result.errors.append(
                        RecordValidationError(
                            row_index=row_num,
                            customer_id=cust_id_label,
                            reasons=row_errors
                        )
                    )
                    continue

            cleaned_row: dict[str, Any] = {"customer_id": cust_id_label}

            # B. Validate Numerical Features
            # SeniorCitizen: 0 or 1
            raw_sc = str(row.get("SeniorCitizen", "")).strip()
            if raw_sc in {"0", "1"}:
                cleaned_row["SeniorCitizen"] = int(raw_sc)
            else:
                row_errors.append(f"Invalid 'SeniorCitizen' value '{raw_sc}': must be 0 or 1")

            # tenure: integer >= 0 and <= 72
            raw_tenure = str(row.get("tenure", "")).strip()
            try:
                tenure_val = int(raw_tenure)
                if tenure_val < 0 or tenure_val > 72:
                    row_errors.append(f"Invalid 'tenure' value {tenure_val}: must be between 0 and 72")
                else:
                    cleaned_row["tenure"] = tenure_val
            except (ValueError, TypeError):
                row_errors.append(f"Invalid 'tenure' value '{raw_tenure}': must be an integer between 0 and 72")

            # MonthlyCharges: float >= 0
            raw_mc = str(row.get("MonthlyCharges", "")).strip()
            try:
                mc_val = float(raw_mc)
                if mc_val < 0 or math.isnan(mc_val):
                    row_errors.append(f"Invalid 'MonthlyCharges' value {mc_val}: must be non-negative")
                else:
                    cleaned_row["MonthlyCharges"] = mc_val
            except (ValueError, TypeError):
                row_errors.append(f"Invalid 'MonthlyCharges' value '{raw_mc}': must be a valid non-negative number")

            # TotalCharges: float >= 0, handling space/empty when tenure == 0
            raw_tc = str(row.get("TotalCharges", "")).strip()
            if raw_tc in {"", " "}:
                # If tenure is 0, empty TotalCharges is standard in Telco dataset -> 0.0
                if cleaned_row.get("tenure") == 0:
                    cleaned_row["TotalCharges"] = 0.0
                else:
                    row_errors.append("Missing 'TotalCharges': cannot be empty when tenure > 0")
            else:
                try:
                    tc_val = float(raw_tc)
                    if tc_val < 0 or math.isnan(tc_val):
                        row_errors.append(f"Invalid 'TotalCharges' value {tc_val}: must be non-negative")
                    else:
                        cleaned_row["TotalCharges"] = tc_val
                except (ValueError, TypeError):
                    row_errors.append(f"Invalid 'TotalCharges' value '{raw_tc}': must be a valid non-negative number")

            # C. Validate Categorical Features
            for cat_col in INPUT_CATEGORICAL_FEATURES:
                raw_val = str(row.get(cat_col, "")).strip()
                allowed_values = VALID_CATEGORICAL_VALUES.get(cat_col, set())
                if not raw_val:
                    row_errors.append(f"Missing required field '{cat_col}'")
                elif raw_val not in allowed_values:
                    sorted_allowed = sorted(list(allowed_values))
                    row_errors.append(
                        f"Invalid '{cat_col}' value '{raw_val}': expected one of {sorted_allowed}"
                    )
                else:
                    cleaned_row[cat_col] = raw_val

            # D. Evaluate record status
            if row_errors:
                result.invalid_records += 1
                result.errors.append(
                    RecordValidationError(
                        row_index=row_num,
                        customer_id=cust_id_label,
                        reasons=row_errors
                    )
                )
            else:
                if cust_id:
                    seen_customer_ids[cust_id] = row_num
                result.valid_records += 1
                valid_rows.append(cleaned_row)

        result.successfully_processed = result.valid_records
        if valid_rows:
            result.valid_df = pd.DataFrame(valid_rows)

        return result
