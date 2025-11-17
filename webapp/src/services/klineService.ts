import { dataHubApi } from './api'
import type { KlineListResponse } from '@/types/kline'

class KlineService {
  async getKlines(params: {
    symbol: string
    interval: string
    limit?: number
  }): Promise<KlineListResponse> {
    const response = await dataHubApi.get<KlineListResponse>(
      `/v1/klines/${params.symbol}/${params.interval}`,
      { params: { limit: params.limit } }
    )
    return response.data
  }
}

export const klineService = new KlineService()
export default klineService

