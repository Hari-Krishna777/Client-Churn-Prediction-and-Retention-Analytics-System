from typing import Any, Dict, List, Optional
import pandas as pd

from app.schemas.explanations import CustomerExplanation, FeatureContribution

FEATURE_LABELS = {
    # Contracts
    "cat__Contract_Month-to-month": "Month-to-month contract",
    "cat__Contract_One year": "One-year contract",
    "cat__Contract_Two year": "Two-year contract",
    # Security & Support
    "cat__OnlineSecurity_No": "No online security",
    "cat__OnlineSecurity_Yes": "Online security enabled",
    "cat__OnlineSecurity_No internet service": "No internet service (security)",
    "cat__TechSupport_No": "No technical support",
    "cat__TechSupport_Yes": "Technical support enabled",
    "cat__TechSupport_No internet service": "No internet service (support)",
    # Backup & Protection
    "cat__OnlineBackup_No": "No online backup",
    "cat__OnlineBackup_Yes": "Online backup active",
    "cat__DeviceProtection_No": "No device protection",
    "cat__DeviceProtection_Yes": "Device protection active",
    # Internet & Phone
    "cat__InternetService_Fiber optic": "Fiber optic internet",
    "cat__InternetService_DSL": "DSL internet",
    "cat__InternetService_No": "No internet service",
    "cat__PhoneService_No": "No phone service",
    "cat__PhoneService_Yes": "Phone service active",
    "cat__MultipleLines_No": "Single phone line",
    "cat__MultipleLines_Yes": "Multiple phone lines",
    "cat__MultipleLines_No phone service": "No phone service",
    # Payment & Billing
    "cat__PaymentMethod_Electronic check": "Electronic check payment",
    "cat__PaymentMethod_Credit card (automatic)": "Automatic credit card payment",
    "cat__PaymentMethod_Bank transfer (automatic)": "Automatic bank transfer payment",
    "cat__PaymentMethod_Mailed check": "Mailed check payment",
    "cat__PaperlessBilling_Yes": "Paperless billing enabled",
    "cat__PaperlessBilling_No": "Paper billing",
    # Streaming
    "cat__StreamingTV_No": "No streaming TV",
    "cat__StreamingTV_Yes": "Streaming TV active",
    "cat__StreamingMovies_No": "No streaming movies",
    "cat__StreamingMovies_Yes": "Streaming movies active",
    # Demographics
    "cat__Partner_No": "No partner",
    "cat__Partner_Yes": "Has partner",
    "cat__Dependents_No": "No dependents",
    "cat__Dependents_Yes": "Has dependents",
    "cat__gender_Female": "Female customer",
    "cat__gender_Male": "Male customer",
    # Tenure Groups
    "cat__TenureGroup_0-6 months": "New customer tenure (0-6 months)",
    "cat__TenureGroup_7-12 months": "Short customer tenure (7-12 months)",
    "cat__TenureGroup_13-24 months": "Moderate customer tenure (13-24 months)",
    "cat__TenureGroup_25-48 months": "Established customer tenure (25-48 months)",
    "cat__TenureGroup_49-72 months": "Long-term customer tenure (49-72 months)",
}


class ExplanationService:
    """
    Transforms raw model SHAP feature contributions into clear,
    interpretable explanations for business users.
    """

    @classmethod
    def format_feature_name(cls, feature_name: str, shap_val: float) -> str:
        """Translate raw model feature names into human-readable descriptions."""
        if feature_name in FEATURE_LABELS:
            return FEATURE_LABELS[feature_name]

        # Numerical features dynamically labeled by impact direction
        if feature_name == "num__tenure":
            return "Short customer tenure" if shap_val > 0 else "Long customer tenure"
        elif feature_name == "num__MonthlyCharges":
            return "Higher monthly charges" if shap_val > 0 else "Affordable monthly charges"
        elif feature_name == "num__TotalCharges":
            return "Total charges spend" if shap_val > 0 else "Lower lifetime spend"
        elif feature_name == "num__AvgMonthlySpend":
            return "High average monthly spend" if shap_val > 0 else "Lower average monthly spend"
        elif feature_name == "num__SeniorCitizen":
            return "Senior citizen demographic" if shap_val > 0 else "Non-senior demographic"
        elif feature_name.startswith("cat__ServiceCount_"):
            count = feature_name.split("_")[-1]
            return f"Low bundle count ({count} services)" if shap_val > 0 else f"High bundle count ({count} services)"

        # Generic fallback
        clean_name = feature_name.replace("cat__", "").replace("num__", "").replace("_", " ")
        return clean_name

    @classmethod
    def get_top_churn_drivers(
        cls,
        shap_row: pd.Series,
        top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """Identify features exerting positive force toward churn prediction."""
        positive_shap = shap_row[shap_row > 0].sort_values(ascending=False)
        drivers = []
        for feature, val in positive_shap.head(top_n).items():
            drivers.append({
                "feature": str(feature),
                "contribution": round(float(val), 4),
                "label": cls.format_feature_name(str(feature), float(val)),
                "direction": "increases_churn"
            })
        return drivers

    @classmethod
    def get_top_protective_factors(
        cls,
        shap_row: pd.Series,
        top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """Identify features exerting negative force away from churn prediction."""
        negative_shap = shap_row[shap_row < 0].sort_values()
        protective = []
        for feature, val in negative_shap.head(top_n).items():
            protective.append({
                "feature": str(feature),
                "contribution": round(float(val), 4),
                "label": cls.format_feature_name(str(feature), float(val)),
                "direction": "decreases_churn"
            })
        return protective

    @classmethod
    def explain_customer(
        cls,
        customer_id: Optional[str],
        churn_probability: float,
        shap_row: pd.Series,
        top_n: int = 3,
        include_details: bool = False
    ) -> CustomerExplanation:
        """
        Build full customer explanation with top churn factors and protective factors.
        """
        drivers = cls.get_top_churn_drivers(shap_row, top_n=top_n)
        protective = cls.get_top_protective_factors(shap_row, top_n=top_n)

        top_churn_factors = [d["label"] for d in drivers]
        top_protective_factors = [p["label"] for p in protective]

        detailed_contributions = None
        if include_details:
            detailed_contributions = []
            for item in drivers + protective:
                detailed_contributions.append(
                    FeatureContribution(
                        feature=item["feature"],
                        label=item["label"],
                        contribution=item["contribution"],
                        direction=item["direction"]
                    )
                )

        return CustomerExplanation(
            customer_id=customer_id,
            churn_probability=round(float(churn_probability), 4),
            top_churn_factors=top_churn_factors,
            top_protective_factors=top_protective_factors,
            detailed_contributions=detailed_contributions
        )
