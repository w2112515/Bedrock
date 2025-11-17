export interface Position {
  id: string
  market: string
  signal_id: string
  position_size: number
  entry_price: number
  current_price: number
  stop_loss_price: number
  profit_target_price: number
  position_weight_used: number
  status: 'OPEN' | 'CLOSED'
  unrealized_pnl: number | null
  created_at: string
  closed_at: string | null
  exit_reason: string | null
}

export interface PositionListResponse {
  positions: Position[]
  total: number
  limit: number
  offset: number
}

export interface PositionEstimateRequest {
  signal_id?: string
  market: string
  entry_price: number
  stop_loss_price: number
  profit_target_price: number
  risk_unit_r: number
  suggested_position_weight?: number
}

export interface PositionEstimateResponse {
  signal_id: string | null
  market: string
  estimated_position_size: number
  estimated_cost: number
  position_weight_used: number
  commission: number
  slippage: number
  risk_percentage: number
  entry_price: number
  stop_loss_price: number
  profit_target_price: number
}

export interface Account {
  id: string
  balance: number
  available_balance: number
  frozen_balance: number
  updated_at: string
}

export interface Stats {
  total_positions: number
  open_positions: number
  closed_positions: number
  total_pnl: number
  win_rate: number
  average_win: number
  average_loss: number
}

