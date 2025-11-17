export interface ArbitrationConfig {
  id: string
  version: number
  rule_weight: number
  ml_weight: number
  llm_weight: number
  min_approval_score: number
  adaptive_threshold_enabled: boolean
  is_active: boolean
  created_at: string
}

export interface ArbitrationStats {
  total_signals: number
  approved_signals: number
  rejected_signals: number
  approval_rate: number
  
  ml_llm_agreement_rate: number | null
  rule_ml_agreement_rate: number | null
  rule_llm_agreement_rate: number | null
  
  avg_rule_score: number
  avg_ml_score: number | null
  avg_llm_score: number | null
  avg_final_score: number
  
  top_rejection_reasons: Array<{
    reason: string
    count: number
  }>
}

