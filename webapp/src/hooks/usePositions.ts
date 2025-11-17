import { useQuery } from '@tanstack/react-query'
import { portfolioService } from '@/services/portfolioService'

export function usePositions(params?: {
  market?: string
  status?: 'OPEN' | 'CLOSED'
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['positions', params],
    queryFn: () => portfolioService.getPositions(params)
  })
}

export function usePosition(positionId: string) {
  return useQuery({
    queryKey: ['position', positionId],
    queryFn: () => portfolioService.getPositionById(positionId),
    enabled: !!positionId
  })
}

export function useAccount() {
  return useQuery({
    queryKey: ['account'],
    queryFn: () => portfolioService.getAccount()
  })
}

export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: () => portfolioService.getStats()
  })
}

