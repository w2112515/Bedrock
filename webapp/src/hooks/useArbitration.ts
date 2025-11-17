import { useQuery } from '@tanstack/react-query'
import { arbitrationService } from '@/services/arbitrationService'

export function useArbitrationConfig() {
  return useQuery({
    queryKey: ['arbitration-config'],
    queryFn: () => arbitrationService.getActiveConfig(),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000
  })
}

export function useArbitrationStats(params?: { days?: number }) {
  return useQuery({
    queryKey: ['arbitration-stats', params],
    queryFn: () => arbitrationService.getStats(params),
    staleTime: 30 * 1000,
    gcTime: 2 * 60 * 1000
  })
}

