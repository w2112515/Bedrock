import { useQuery } from '@tanstack/react-query'
import { signalService } from '@/services/signalService'

export function useSignals(params?: {
  market?: string
  signal_type?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['signals', params],
    queryFn: () => signalService.getSignals(params)
  })
}

export function useSignal(signalId: string) {
  return useQuery({
    queryKey: ['signal', signalId],
    queryFn: () => signalService.getSignalById(signalId),
    enabled: !!signalId
  })
}

