import { portfolioApi } from './api'
import type { Trade, TradeListResponse } from '@/types/trade'

class TradeService {
  async getTrades(params?: {
    position_id?: string
    trade_type?: 'ENTRY' | 'EXIT'
    limit?: number
    offset?: number
  }): Promise<TradeListResponse> {
    const response = await portfolioApi.get<TradeListResponse>('/v1/trades', { params })
    return response.data
  }

  async getTradeById(tradeId: string): Promise<Trade> {
    const response = await portfolioApi.get<Trade>(`/v1/trades/${tradeId}`)
    return response.data
  }
}

export const tradeService = new TradeService()
export default tradeService

