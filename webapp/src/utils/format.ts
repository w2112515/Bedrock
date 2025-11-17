export function formatPrice(price: number, decimals: number = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(price)
}

export function formatPercentage(value: number, decimals: number = 2): string {
  return `${(value * 100).toFixed(decimals)}%`
}

export function formatWeight(weight: number): string {
  return `${(weight * 100).toFixed(1)}%`
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('zh-CN')
}

