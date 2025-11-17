import { portfolioApi } from './api'
import type { 
  Position, 
  PositionListResponse, 
  PositionEstimateRequest,
  PositionEstimateResponse,
  Account,
  Stats
} from '@/types/position'

class PortfolioService {
  async getPositions(params?: {
    market?: string
    status?: 'OPEN' | 'CLOSED'
    limit?: number
    offset?: number
  }): Promise<PositionListResponse> {
    const response = await portfolioApi.get<PositionListResponse>('/v1/positions', { params })
    return response.data
  }

  async getPositionById(positionId: string): Promise<Position> {
    const response = await portfolioApi.get<Position>(`/v1/positions/${positionId}`)
    return response.data
  }

  async estimatePosition(data: PositionEstimateRequest): Promise<PositionEstimateResponse> {
    const response = await portfolioApi.post<PositionEstimateResponse>('/v1/positions/estimate', data)
    return response.data
  }

  async getAccount(): Promise<Account> {
    const response = await portfolioApi.get<Account>('/v1/account')
    return response.data
  }

  async getStats(): Promise<Stats> {
    const response = await portfolioApi.get<Stats>('/v1/stats')
    return response.data
  }
}

export const portfolioService = new PortfolioService()
export default portfolioService

