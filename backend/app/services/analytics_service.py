import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from app.config import (
    LOW_RISK_THRESHOLD,
    HIGH_RISK_THRESHOLD,
    DEFAULT_CLASSIFICATION_THRESHOLD,
    ALL_INPUT_FEATURES
)
from app.services.model_service import model, threshold, get_risk_category
from app.services.feature_engineering import engineer_features
from app.services.batch_service import BatchService, BatchJob
from app.services.shap_service import ShapService
from app.services.explanation_service import ExplanationService
from app.services.recommendation_service import (
    RecommendationService,
    assign_action_urgency
)
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    RiskDistributionResponse,
    ChurnFactorsResponse,
    ChurnFactorMetric,
    RecommendationSummaryResponse,
    CustomerSegmentsResponse,
    SegmentMetric
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Provides aggregated customer risk, SHAP explanations, and retention analytics."""

    @classmethod
    def get_dataset(
        cls, job_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Retrieve customer dataset for analytics:
        1. From specific job_id if provided.
        2. From latest completed batch job.
        3. From baseline test dataset if no batch jobs exist.
        """
        if job_id:
            job = BatchService.get_job(job_id)
            if job and job.predictions_df is not None:
                return job.predictions_df.copy(), job.job_id

        # Look for any completed job in memory
        for j_id, job in reversed(list(BatchService._jobs.items())):
            if (
                job.status == "COMPLETED"
                and job.predictions_df is not None
                and (user_id is None or str(job.user_id) == str(user_id))
            ):
                return job.predictions_df.copy(), job.job_id

        # Fallback to local sample dataset
        sample_path = Path(__file__).resolve().parents[2] / "tests" / "data" / "sample_50_telco.csv"
        if sample_path.exists():
            raw_df = pd.read_csv(sample_path)
            # Process sample dataset on the fly
            clean_df = raw_df.copy()
            clean_df["customer_id"] = clean_df["customerID"]
            clean_df["TotalCharges"] = pd.to_numeric(clean_df["TotalCharges"], errors="coerce").fillna(0.0)
            
            eng_df = engineer_features(clean_df.drop(columns=["customerID", "customer_id", "Churn"], errors="ignore"))
            expected_features = getattr(model, "feature_names_in_", None)
            probs = model.predict_proba(eng_df[expected_features])[:, 1]
            
            clean_df["churn_probability"] = [round(float(p), 4) for p in probs]
            clean_df["churn_prediction"] = ["Yes" if p >= threshold else "No" for p in probs]
            clean_df["risk_category"] = [get_risk_category(float(p)) for p in probs]
            clean_df["TenureGroup"] = eng_df["TenureGroup"]
            clean_df["AvgMonthlySpend"] = eng_df["AvgMonthlySpend"]
            clean_df["ServiceCount"] = eng_df["ServiceCount"]
            return clean_df, "sample_baseline"

        # Empty fallback
        return pd.DataFrame(), None

    @classmethod
    def get_overview(cls, job_id: Optional[str] = None, user_id: Optional[str] = None) -> AnalyticsOverviewResponse:
        """Compute top-level customer counts, churn rate, and risk summary."""
        df, resolved_job_id = cls.get_dataset(job_id, user_id=user_id)
        if df.empty:
            return AnalyticsOverviewResponse(
                total_customers=0,
                predicted_churners=0,
                predicted_retained=0,
                churn_rate_percentage=0.0,
                average_churn_probability=0.0,
                risk_distribution={"LOW": 0, "MEDIUM": 0, "HIGH": 0},
                avg_churn_by_risk={"LOW": 0.0, "MEDIUM": 0.0, "HIGH": 0.0},
                classification_threshold=threshold,
                job_id=resolved_job_id
            )

        total_customers = len(df)
        churners = int((df["churn_prediction"] == "Yes").sum())
        retained = total_customers - churners
        churn_rate = round((churners / total_customers) * 100, 2)
        avg_prob = round(float(df["churn_probability"].mean()), 4)

        risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for cat, cnt in df["risk_category"].value_counts().items():
            if cat in risk_counts:
                risk_counts[cat] = int(cnt)

        avg_by_risk = {}
        for risk_cat in ["LOW", "MEDIUM", "HIGH"]:
            subset = df[df["risk_category"] == risk_cat]
            avg_by_risk[risk_cat] = round(float(subset["churn_probability"].mean()), 4) if not subset.empty else 0.0

        return AnalyticsOverviewResponse(
            total_customers=total_customers,
            predicted_churners=churners,
            predicted_retained=retained,
            churn_rate_percentage=churn_rate,
            average_churn_probability=avg_prob,
            risk_distribution=risk_counts,
            avg_churn_by_risk=avg_by_risk,
            classification_threshold=threshold,
            job_id=resolved_job_id
        )

    @classmethod
    def get_risk_distribution(cls, job_id: Optional[str] = None, user_id: Optional[str] = None) -> RiskDistributionResponse:
        """Calculate distribution counts, percentages, and definitions for risk bands."""
        df, resolved_job_id = cls.get_dataset(job_id, user_id=user_id)
        total = len(df) if not df.empty else 1

        counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        percentages = {"LOW": 0.0, "MEDIUM": 0.0, "HIGH": 0.0}

        if not df.empty:
            for cat, cnt in df["risk_category"].value_counts().items():
                if cat in counts:
                    counts[cat] = int(cnt)
                    percentages[cat] = round((int(cnt) / total) * 100, 2)

        thresholds = {
            "low_risk_max": LOW_RISK_THRESHOLD,
            "high_risk_min": HIGH_RISK_THRESHOLD,
            "binary_classification_threshold": threshold
        }

        descriptions = {
            "LOW": f"Customers with churn probability < {LOW_RISK_THRESHOLD:.2f}. Routine monitoring.",
            "MEDIUM": f"Customers with churn probability between {LOW_RISK_THRESHOLD:.2f} and {HIGH_RISK_THRESHOLD:.2f}. Planned retention campaigns.",
            "HIGH": f"Customers with churn probability >= {HIGH_RISK_THRESHOLD:.2f}. Urgent proactive retention intervention."
        }

        return RiskDistributionResponse(
            counts=counts,
            percentages=percentages,
            thresholds=thresholds,
            descriptions=descriptions,
            job_id=resolved_job_id
        )

    @classmethod
    def get_churn_factors(
        cls,
        job_id: Optional[str] = None,
        top_n: int = 5,
        user_id: Optional[str] = None,
    ) -> ChurnFactorsResponse:
        """Analyze dataset-wide SHAP contributions to identify dominant churn drivers."""
        df, resolved_job_id = cls.get_dataset(job_id, user_id=user_id)
        if df.empty:
            return ChurnFactorsResponse(
                total_analyzed=0,
                top_churn_drivers=[],
                top_protective_factors=[],
                job_id=resolved_job_id
            )

        # Prepare feature engineered dataframe for SHAP computation
        feat_df = df.copy()
        if "TenureGroup" not in feat_df.columns:
            feat_df = engineer_features(feat_df)

        shap_df = ShapService.calculate_shap_matrix(feat_df)
        total_customers = len(shap_df)

        # Calculate positive impacts (churn drivers)
        positive_shap = shap_df.clip(lower=0)
        mean_pos = positive_shap.mean().sort_values(ascending=False)

        churn_drivers: List[ChurnFactorMetric] = []
        for feat, score in mean_pos.head(top_n).items():
            affected = int((shap_df[feat] > 0).sum())
            pct = round((affected / total_customers) * 100, 2)
            churn_drivers.append(
                ChurnFactorMetric(
                    factor=ExplanationService.format_feature_name(str(feat), 1.0),
                    feature_name=str(feat),
                    impact_score=round(float(score), 4),
                    affected_customers_count=affected,
                    affected_percentage=pct,
                    direction="increases_churn"
                )
            )

        # Calculate negative impacts (protective factors)
        negative_shap = shap_df.clip(upper=0)
        mean_neg = negative_shap.mean().sort_values(ascending=True)

        protective_factors: List[ChurnFactorMetric] = []
        for feat, score in mean_neg.head(top_n).items():
            affected = int((shap_df[feat] < 0).sum())
            pct = round((affected / total_customers) * 100, 2)
            protective_factors.append(
                ChurnFactorMetric(
                    factor=ExplanationService.format_feature_name(str(feat), -1.0),
                    feature_name=str(feat),
                    impact_score=round(float(abs(score)), 4),
                    affected_customers_count=affected,
                    affected_percentage=pct,
                    direction="decreases_churn"
                )
            )

        return ChurnFactorsResponse(
            total_analyzed=total_customers,
            top_churn_drivers=churn_drivers,
            top_protective_factors=protective_factors,
            job_id=resolved_job_id
        )

    @classmethod
    def get_recommendations_summary(
        cls,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> RecommendationSummaryResponse:
        """Generate retention recommendations summary across customers."""
        df, resolved_job_id = cls.get_dataset(job_id, user_id=user_id)
        if df.empty:
            return RecommendationSummaryResponse(
                total_recommendations=0,
                unique_customers_receiving_recommendations=0,
                by_reason={},
                by_priority={},
                by_urgency={},
                top_suggested_actions=[],
                job_id=resolved_job_id
            )

        feat_df = df.copy()
        if "TenureGroup" not in feat_df.columns:
            feat_df = engineer_features(feat_df)

        shap_df = ShapService.calculate_shap_matrix(feat_df)

        all_recs = []
        unique_customers = set()
        reason_counts = Counter()
        priority_counts = Counter()
        urgency_counts = Counter()
        action_map: Dict[str, Dict[str, Any]] = {}

        for idx, row in df.iterrows():
            cust_id = row.get("customer_id") or str(idx)
            prob = float(row.get("churn_probability", 0.0))
            shap_row = shap_df.loc[idx] if idx in shap_df.index else None

            recs = RecommendationService.generate_customer_recommendations(
                customer_id=cust_id,
                customer_data=row.to_dict(),
                churn_probability=prob,
                shap_row=shap_row
            )

            if recs:
                unique_customers.add(cust_id)
                for r in recs:
                    all_recs.append(r)
                    reason_counts[r.recommendation_reason] += 1
                    priority_counts[r.priority] += 1
                    urgency_counts[r.action_urgency] += 1

                    action_key = r.suggested_action
                    if action_key not in action_map:
                        action_map[action_key] = {
                            "action": r.suggested_action,
                            "reason": r.recommendation_reason,
                            "priority": r.priority,
                            "customer_count": 0
                        }
                    action_map[action_key]["customer_count"] += 1

        sorted_actions = sorted(
            action_map.values(),
            key=lambda x: x["customer_count"],
            reverse=True
        )

        return RecommendationSummaryResponse(
            total_recommendations=len(all_recs),
            unique_customers_receiving_recommendations=len(unique_customers),
            by_reason=dict(reason_counts),
            by_priority=dict(priority_counts),
            by_urgency=dict(urgency_counts),
            top_suggested_actions=sorted_actions,
            job_id=resolved_job_id
        )

    @classmethod
    def get_segments(cls, job_id: Optional[str] = None, user_id: Optional[str] = None) -> CustomerSegmentsResponse:
        """Break down churn risk and churn rate across customer dimensions."""
        df, resolved_job_id = cls.get_dataset(job_id, user_id=user_id)
        if df.empty:
            return CustomerSegmentsResponse(
                by_contract=[],
                by_tenure_group=[],
                by_internet_service=[],
                by_payment_method=[],
                highest_risk_segments=[],
                job_id=resolved_job_id
            )

        if "TenureGroup" not in df.columns:
            df = engineer_features(df)

        def analyze_dimension(dim_col: str) -> List[SegmentMetric]:
            segments = []
            if dim_col not in df.columns:
                return segments

            for val, group in df.groupby(dim_col):
                total = len(group)
                churn_cnt = int((group["churn_prediction"] == "Yes").sum())
                churn_rate = round((churn_cnt / total) * 100, 2)
                avg_prob = round(float(group["churn_probability"].mean()), 4)
                dominant_risk = group["risk_category"].mode()[0] if not group.empty else "LOW"

                segments.append(
                    SegmentMetric(
                        segment_name=str(val),
                        customer_count=total,
                        churn_count=churn_cnt,
                        churn_rate_percentage=churn_rate,
                        avg_churn_probability=avg_prob,
                        dominant_risk_category=dominant_risk
                    )
                )
            return sorted(segments, key=lambda s: s.churn_rate_percentage, reverse=True)

        contract_segments = analyze_dimension("Contract")
        tenure_segments = analyze_dimension("TenureGroup")
        internet_segments = analyze_dimension("InternetService")
        payment_segments = analyze_dimension("PaymentMethod")

        all_segments = contract_segments + tenure_segments + internet_segments + payment_segments
        highest_risk = sorted(all_segments, key=lambda s: s.churn_rate_percentage, reverse=True)[:5]

        return CustomerSegmentsResponse(
            by_contract=contract_segments,
            by_tenure_group=tenure_segments,
            by_internet_service=internet_segments,
            by_payment_method=payment_segments,
            highest_risk_segments=highest_risk,
            job_id=resolved_job_id
        )
