export interface Signal {
  id: string
  market: string
  signal_type: 'PULLBACK_BUY' | 'OOPS_BUY' | 'OOPS_SELL'
  entry_price: number
  stop_loss_price: number
  profit_target_price: number
  risk_unit_r: number
  suggested_position_weight: number
  reward_risk_ratio: number | null
  onchain_signals: OnchainSignalsData | null
  rule_engine_score: number
  ml_confidence_score: number | null
  llm_sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL' | null
  final_decision: 'APPROVED' | 'REJECTED' | null
  explanation: string | null
  created_at: string
}

export interface OnchainSignalsData {
  whale_active?: boolean
  fund_outflow?: boolean
  smart_money_buy?: boolean
  address_active_increase?: boolean
  large_transfer_count?: number
  exchange_netflow?: number
  smart_money_netbuy?: number
  active_address_growth?: number
}

export interface SignalListResponse {
  signals: Signal[]
  total_count: number
  limit: number
  offset: number
}

export interface SignalGenerateRequest {
  market: string
  force_analysis?: boolean
}

