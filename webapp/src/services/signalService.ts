import { decisionEngineApi } from './api'
import type { Signal, SignalListResponse, SignalGenerateRequest } from '@/types/signal'

class SignalService {
  async getSignals(params?: {
    market?: string
    signal_type?: string
    limit?: number
    offset?: number
  }): Promise<SignalListResponse> {
    const response = await decisionEngineApi.get<SignalListResponse>('/v1/signals/list', { params })
    return response.data
  }

  async getSignalById(signalId: string): Promise<Signal> {
    const response = await decisionEngineApi.get<Signal>(`/v1/signals/${signalId}`)
    return response.data
  }

  async generateSignal(data: SignalGenerateRequest): Promise<Signal> {
    const response = await decisionEngineApi.post<Signal>('/v1/signals/generate', data)
    return response.data
  }

  async triggerSignalGeneration(): Promise<{ status: string }> {
    const response = await decisionEngineApi.post<{ status: string }>('/v1/signals/trigger')
    return response.data
  }
}

export const signalService = new SignalService()
export default signalService

