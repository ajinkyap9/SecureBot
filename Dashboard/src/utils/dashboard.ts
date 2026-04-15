export function maxTrendValue(values: Array<{ value: number }>) {
  return values.reduce((max, item) => Math.max(max, item.value), 0)
}

export function confidenceBand(value: number) {
  if (value >= 0.9) {
    return 'very high confidence'
  }
  if (value >= 0.8) {
    return 'high confidence'
  }
  if (value >= 0.7) {
    return 'medium confidence'
  }
  return 'low confidence'
}
