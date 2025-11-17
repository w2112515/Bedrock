import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useSignals } from '@/hooks/useSignals'
import { signalService } from '@/services/signalService'
import type { ReactNode } from 'react'

vi.mock('@/services/signalService', () => ({
  signalService: {
    getSignals: vi.fn()
  }
}))

describe('useSignals', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false
        }
      }
    })
    vi.clearAllMocks()
  })

  it('should fetch signals successfully', async () => {
    const mockData = {
      signals: [
        {
          id: '1',
          market: 'BTC/USDT',
          signal_type: 'PULLBACK_BUY',
          suggested_position_weight: 0.8
        }
      ],
      total_count: 1,
      limit: 20,
      offset: 0
    }

    vi.mocked(signalService.getSignals).mockResolvedValue(mockData)

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useSignals(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockData)
    expect(signalService.getSignals).toHaveBeenCalledTimes(1)
  })

  it('should handle error', async () => {
    vi.mocked(signalService.getSignals).mockRejectedValue(new Error('API Error'))

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useSignals(), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBeTruthy()
  })
})

