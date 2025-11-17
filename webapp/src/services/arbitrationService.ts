import { decisionEngineApi } from './api'
import type { ArbitrationConfig, ArbitrationStats } from '@/types/arbitration'

class ArbitrationService {
  async getActiveConfig(): Promise<ArbitrationConfig> {
    const response = await decisionEngineApi.get<ArbitrationConfig>(
      '/v1/arbitration/config'
    )
    return response.data
  }

  async getStats(params?: { days?: number }): Promise<ArbitrationStats> {
    const response = await decisionEngineApi.get<ArbitrationStats>(
      '/v1/arbitration/stats',
      { params }
    )
    return response.data
  }
}

export const arbitrationService = new ArbitrationService()

