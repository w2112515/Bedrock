export interface Kline {
  symbol: string
  interval: string
  open_time: number
  close_time: number
  open_price: number
  high_price: number
  low_price: number
  close_price: number
  volume: number
  quote_volume?: number
  trade_count?: number
  taker_buy_base_volume?: number
  taker_buy_quote_volume?: number
  source: string
}

// 后端API直接返回数组，不是包装对象
export type KlineListResponse = Kline[]

