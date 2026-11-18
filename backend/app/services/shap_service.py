import logging
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd
import shap
from scipy import sparse

from app.services.model_service import model
from app.config import ALL_MODEL_FEATURES

logger = logging.getLogger(__name__)


class ShapService:
    """
    Service for calculating SHAP explanations using TreeExplainer
    on the trained XGBoost churn model.
    """

    _explainer: Optional[shap.TreeExplainer] = None
    _feature_names: Optional[List[str]] = None

    @classmethod
    def get_explainer(cls) -> shap.TreeExplainer:
        """Initialize or retrieve singleton TreeExplainer."""
        if cls._explainer is None:
            xgb_model = model.named_steps["model"]
            cls._explainer = shap.TreeExplainer(xgb_model)
            logger.info("SHAP TreeExplainer initialized successfully.")
        return cls._explainer

    @classmethod
    def get_feature_names(cls) -> List[str]:
        """Get the transformed feature names produced by the ColumnTransformer."""
        if cls._feature_names is None:
            preprocessor = model.named_steps["preprocessor"]
            cls._feature_names = list(preprocessor.get_feature_names_out())
        return cls._feature_names

    @classmethod
    def transform_data(cls, data: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """
        Pass customer data through the pipeline ColumnTransformer.
        Returns dense array of transformed features and feature names.
        """
        preprocessor = model.named_steps["preprocessor"]
        expected_features = getattr(model, "feature_names_in_", ALL_MODEL_FEATURES)
        aligned_data = data[expected_features]

        transformed = preprocessor.transform(aligned_data)
        if sparse.issparse(transformed):
            transformed = transformed.toarray()

        feature_names = cls.get_feature_names()
        return transformed, feature_names

    @classmethod
    def calculate_shap_matrix(cls, data: pd.DataFrame) -> pd.DataFrame:
        """
        Compute SHAP values for each customer in data.
        Returns a DataFrame of shape (n_customers, 60) indexed like data.
        """
        transformed, feature_names = cls.transform_data(data)
        explainer = cls.get_explainer()
        shap_explanation = explainer(transformed)

        shap_df = pd.DataFrame(
            shap_explanation.values,
            columns=feature_names,
            index=data.index
        )
        return shap_df
