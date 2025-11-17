import { describe, it, expect } from 'vitest'
import { formatPrice, formatPercentage, formatWeight } from '@/utils/format'

describe('format utils', () => {
  describe('formatPrice', () => {
    it('should format price with default 2 decimals', () => {
      expect(formatPrice(1234.5678)).toBe('1,234.57')
    })

    it('should format price with custom decimals', () => {
      expect(formatPrice(1234.5678, 4)).toBe('1,234.5678')
    })

    it('should handle zero', () => {
      expect(formatPrice(0)).toBe('0.00')
    })
  })

  describe('formatPercentage', () => {
    it('should format percentage correctly', () => {
      expect(formatPercentage(0.1234)).toBe('12.34%')
    })

    it('should format with custom decimals', () => {
      expect(formatPercentage(0.1234, 1)).toBe('12.3%')
    })
  })

  describe('formatWeight', () => {
    it('should format weight correctly', () => {
      expect(formatWeight(0.8)).toBe('80.0%')
    })

    it('should handle 1.0', () => {
      expect(formatWeight(1.0)).toBe('100.0%')
    })

    it('should handle 0', () => {
      expect(formatWeight(0)).toBe('0.0%')
    })
  })
})

