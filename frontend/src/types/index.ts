export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'analyst' | 'viewer';
}

export interface AuthResponse {
  access_token: string;
  token_type: 'bearer';
  id: string;
  username: string;
  email: string;
  role: User['role'];
}

export interface AnalyticsOverview {
  total_customers: number;
  predicted_churners: number;
  predicted_retained: number;
  churn_rate_percentage: number;
  average_churn_probability: number;
  risk_distribution: {
    LOW?: number;
    MEDIUM?: number;
    HIGH?: number;
  };
  avg_churn_by_risk?: {
    LOW?: number;
    MEDIUM?: number;
    HIGH?: number;
  };
  classification_threshold: number;
  job_id?: string;
}

export interface RiskDistributionResponse {
  counts: Record<string, number>;
  percentages: Record<string, number>;
  thresholds: Record<string, number>;
  descriptions: Record<string, string>;
  job_id?: string;
}

export interface ChurnFactorItem {
  factor: string;
  feature_name: string;
  impact_score: number;
  affected_customers_count: number;
  affected_percentage: number;
  direction: 'increases_churn' | 'decreases_churn';
}

export interface ChurnFactorsResponse {
  total_analyzed: number;
  top_churn_drivers: ChurnFactorItem[];
  top_protective_factors: ChurnFactorItem[];
  job_id?: string;
}

export interface SegmentMetric {
  segment_name: string;
  customer_count: number;
  churn_count: number;
  churn_rate_percentage: number;
  avg_churn_probability: number;
  dominant_risk_category: string;
}

export interface CustomerSegmentsResponse {
  by_contract: SegmentMetric[];
  by_tenure_group: SegmentMetric[];
  by_internet_service: SegmentMetric[];
  by_payment_method: SegmentMetric[];
  highest_risk_segments: SegmentMetric[];
  job_id?: string;
}

export interface SuggestedActionItem {
  action: string;
  reason: string;
  priority: string;
  customer_count: number;
}

export interface RecommendationSummaryResponse {
  total_recommendations: number;
  unique_customers_receiving_recommendations: number;
  by_reason: Record<string, number>;
  by_priority: Record<string, number>;
  by_urgency: Record<string, number>;
  top_suggested_actions: SuggestedActionItem[];
  job_id?: string;
}

export interface CustomerListItem {
  id: string;
  customer_id: string;
  dataset_id?: string;
  gender?: string;
  senior_citizen?: number;
  partner?: string;
  dependents?: string;
  tenure: number;
  phone_service?: string;
  multiple_lines?: string;
  internet_service?: string;
  online_security?: string;
  online_backup?: string;
  device_protection?: string;
  tech_support?: string;
  streaming_tv?: string;
  streaming_movies?: string;
  contract: string;
  paperless_billing?: string;
  payment_method?: string;
  monthly_charges: number;
  total_charges: number;
  churn_probability: number;
  churn_prediction: 'Yes' | 'No';
  risk_category: 'LOW' | 'MEDIUM' | 'HIGH';
  action_urgency: 'MONITOR' | 'PLANNED' | 'URGENT';
  created_at?: string;
}

export interface ShapExplanationItem {
  feature_name: string;
  feature_label: string;
  contribution: number;
  direction: 'increases_churn' | 'decreases_churn';
  rank: number;
}

export interface RetentionAction {
  id: string;
  prediction_id?: string;
  customer_id: string;
  customer_uuid?: string;
  tenure?: number;
  contract?: string;
  monthly_charges?: number;
  churn_probability?: number;
  risk_category?: string;
  recommendation_reason: string;
  suggested_action: string;
  priority: 'High' | 'Medium' | 'Low';
  action_urgency: 'URGENT' | 'PLANNED' | 'MONITOR';
  supporting_shap_contribution?: number;
  shap_feature?: string;
  status: 'Pending' | 'In Progress' | 'Contacted' | 'Retained' | 'Escalated' | 'Closed';
  notes?: string;
  created_at?: string;
}

export interface PredictionSnapshot {
  prediction_id: string;
  churn_probability: number;
  churn_prediction: string;
  risk_category: string;
  action_urgency: string;
  threshold?: number;
  created_at?: string;
}

export interface CustomerDetailsResponse {
  customer: CustomerListItem;
  prediction: {
    churn_probability: number;
    churn_prediction: 'Yes' | 'No';
    risk_category: 'LOW' | 'MEDIUM' | 'HIGH';
    action_urgency: 'MONITOR' | 'PLANNED' | 'URGENT';
    threshold: number;
    top_churn_factors: string[];
    top_protective_factors: string[];
  };
  shap_explanations: ShapExplanationItem[];
  recommendations: RetentionAction[];
  history: PredictionSnapshot[];
}

export interface BatchJobItem {
  job_id: string;
  filename: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  total_records: number;
  valid_records: number;
  invalid_records: number;
  duplicate_records: number;
  successfully_processed: number;
  risk_distribution?: {
    LOW: number;
    MEDIUM: number;
    HIGH: number;
  };
  created_at?: string;
  completed_at?: string;
  download_url?: string;
}

export interface BatchPredictResponse {
  job_id: string;
  status: string;
  filename: string;
  created_at: string;
  completed_at?: string;
  validation_summary: {
    total_records: number;
    valid_records: number;
    invalid_records: number;
    duplicate_records: number;
    successfully_processed: number;
    warnings: string[];
  };
  invalid_records: Array<{
    row_index: number;
    customer_id?: string;
    reasons: string[];
  }>;
  total_predictions: number;
  risk_distribution: {
    LOW: number;
    MEDIUM: number;
    HIGH: number;
  };
  download_url: string;
}

export interface RetentionStats {
  total_actions: number;
  status_breakdown: Record<string, number>;
  priority_breakdown: Record<string, number>;
  urgency_breakdown: Record<string, number>;
  actioned_count: number;
  retained_count: number;
  retention_success_rate: number;
}
