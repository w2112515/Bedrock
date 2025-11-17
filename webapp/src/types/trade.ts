export interface Trade {
  id: string
  position_id: string
  trade_type: 'ENTRY' | 'EXIT'
  market: string
  quantity: number
  price: number
  timestamp: string
  commission: number
  realized_pnl: number | null
}

export interface TradeListResponse {
  trades: Trade[]
  total: number
  limit: number
  offset: number
}

export const TRADE_TYPES = {
  ENTRY: 'ENTRY',
  EXIT: 'EXIT'
} as const

