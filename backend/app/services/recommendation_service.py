from typing import Any, Dict, List, Optional
import pandas as pd

from app.schemas.recommendations import (
    RetentionRecommendation,
    CustomerRecommendationResponse
)
from app.services.model_service import get_risk_category

# Benchmark for identifying higher monthly charges (e.g. median 70.35 / 75th percentile ~89.85)
DEFAULT_MONTHLY_CHARGE_BENCHMARK = 70.0


def assign_action_urgency(risk_category: str) -> str:
    """
    Assign action urgency strictly matching Deepnote specification:
    - HIGH risk -> URGENT
    - MEDIUM risk -> PLANNED
    - LOW risk -> MONITOR
    """
    if risk_category == "HIGH":
        return "URGENT"
    elif risk_category == "MEDIUM":
        return "PLANNED"
    else:
        return "MONITOR"


class RecommendationService:
    """
    Retention Recommendation Engine combining customer conditions,
    risk categorization, and supporting SHAP contributions.
    """

    @classmethod
    def generate_customer_recommendations(
        cls,
        customer_id: Optional[str],
        customer_data: Dict[str, Any],
        churn_probability: float,
        risk_category: Optional[str] = None,
        shap_row: Optional[pd.Series] = None,
        monthly_charge_benchmark: float = DEFAULT_MONTHLY_CHARGE_BENCHMARK
    ) -> List[RetentionRecommendation]:
        """
        Generate actionable retention recommendations for a customer record.
        Integrates SHAP feature validation when shap_row is provided.
        """
        if risk_category is None:
            risk_category = get_risk_category(churn_probability)

        urgency = assign_action_urgency(risk_category)
        recommendations: List[RetentionRecommendation] = []

        def get_shap_val(feat_name: str) -> Optional[float]:
            if shap_row is not None and feat_name in shap_row.index:
                return float(shap_row[feat_name])
            return None

        def is_shap_positive(feat_name: str) -> bool:
            # If no SHAP row is provided, allow condition to trigger purely rule-based
            if shap_row is None:
                return True
            val = get_shap_val(feat_name)
            return val is not None and val > 0

        # 1. Month-to-month contract
        contract_feat = "cat__Contract_Month-to-month"
        if customer_data.get("Contract") == "Month-to-month" and is_shap_positive(contract_feat):
            shap_c = get_shap_val(contract_feat)
            recommendations.append(
                RetentionRecommendation(
                    customer_id=customer_id,
                    churn_probability=round(float(churn_probability), 4),
                    risk_category=risk_category,
                    recommendation_reason="Month-to-month contract",
                    suggested_action="Offer a longer-term contract (one-year or two-year plan with incentive)",
                    priority="High",
                    action_urgency=urgency,
                    supporting_shap_contribution=round(shap_c, 4) if shap_c is not None else None,
                    shap_feature=contract_feat
                )
            )

        # 2. Short customer tenure
        tenure_feat = "num__tenure"
        raw_tenure = customer_data.get("tenure", 999)
        try:
            tenure_val = int(raw_tenure)
        except (ValueError, TypeError):
            tenure_val = 999

        if tenure_val <= 12 and is_shap_positive(tenure_feat):
            shap_c = get_shap_val(tenure_feat)
            recommendations.append(
                RetentionRecommendation(
                    customer_id=customer_id,
                    churn_probability=round(float(churn_probability), 4),
                    risk_category=risk_category,
                    recommendation_reason="Short customer tenure",
                    suggested_action="Provide onboarding assistance and schedule a satisfaction check-in",
                    priority="High",
                    action_urgency=urgency,
                    supporting_shap_contribution=round(shap_c, 4) if shap_c is not None else None,
                    shap_feature=tenure_feat
                )
            )

        # 3. No online security service
        sec_feat = "cat__OnlineSecurity_No"
        if customer_data.get("OnlineSecurity") == "No" and is_shap_positive(sec_feat):
            shap_c = get_shap_val(sec_feat)
            recommendations.append(
                RetentionRecommendation(
                    customer_id=customer_id,
                    churn_probability=round(float(churn_probability), 4),
                    risk_category=risk_category,
                    recommendation_reason="No online security",
                    suggested_action="Offer a security package with complimentary trial protection",
                    priority="Medium",
                    action_urgency=urgency,
                    supporting_shap_contribution=round(shap_c, 4) if shap_c is not None else None,
                    shap_feature=sec_feat
                )
            )

        # 4. No technical support service
        tech_feat = "cat__TechSupport_No"
        if customer_data.get("TechSupport") == "No" and is_shap_positive(tech_feat):
            shap_c = get_shap_val(tech_feat)
            recommendations.append(
                RetentionRecommendation(
                    customer_id=customer_id,
                    churn_probability=round(float(churn_probability), 4),
                    risk_category=risk_category,
                    recommendation_reason="No technical support",
                    suggested_action="Offer a support plan with 24/7 priority customer care",
                    priority="Medium",
                    action_urgency=urgency,
                    supporting_shap_contribution=round(shap_c, 4) if shap_c is not None else None,
                    shap_feature=tech_feat
                )
            )

        # 5. Electronic check payment method
        pay_feat = "cat__PaymentMethod_Electronic check"
        if customer_data.get("PaymentMethod") == "Electronic check" and is_shap_positive(pay_feat):
            shap_c = get_shap_val(pay_feat)
            recommendations.append(
                RetentionRecommendation(
                    customer_id=customer_id,
                    churn_probability=round(float(churn_probability), 4),
                    risk_category=risk_category,
                    recommendation_reason="Electronic check",
                    suggested_action="Encourage an alternative automatic payment method (credit card or bank transfer)",
                    priority="Low",
                    action_urgency=urgency,
                    supporting_shap_contribution=round(shap_c, 4) if shap_c is not None else None,
                    shap_feature=pay_feat
                )
            )

        # 6. Higher monthly charges
        charges_feat = "num__MonthlyCharges"
        raw_mc = customer_data.get("MonthlyCharges", 0)
        try:
            mc_val = float(raw_mc)
        except (ValueError, TypeError):
            mc_val = 0.0

        if mc_val >= monthly_charge_benchmark and is_shap_positive(charges_feat):
            shap_c = get_shap_val(charges_feat)
            recommendations.append(
                RetentionRecommendation(
                    customer_id=customer_id,
                    churn_probability=round(float(churn_probability), 4),
                    risk_category=risk_category,
                    recommendation_reason="High monthly charges",
                    suggested_action="Review suitable pricing plans and identify cost-effective alternatives or bundle discounts",
                    priority="Medium",
                    action_urgency=urgency,
                    supporting_shap_contribution=round(shap_c, 4) if shap_c is not None else None,
                    shap_feature=charges_feat
                )
            )

        return recommendations

    @classmethod
    def build_recommendation_response(
        cls,
        customer_id: Optional[str],
        customer_data: Dict[str, Any],
        churn_probability: float,
        shap_row: Optional[pd.Series] = None
    ) -> CustomerRecommendationResponse:
        """Construct full recommendation response container for a single customer."""
        risk = get_risk_category(churn_probability)
        urgency = assign_action_urgency(risk)
        recs = cls.generate_customer_recommendations(
            customer_id=customer_id,
            customer_data=customer_data,
            churn_probability=churn_probability,
            risk_category=risk,
            shap_row=shap_row
        )

        return CustomerRecommendationResponse(
            customer_id=customer_id,
            churn_probability=round(float(churn_probability), 4),
            risk_category=risk,
            action_urgency=urgency,
            total_recommendations=len(recs),
            recommendations=recs
        )
