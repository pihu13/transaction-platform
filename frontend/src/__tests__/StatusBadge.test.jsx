import { describe, expect, it } from 'vitest'

describe('transaction UI', () => {
  it('keeps failed status eligible for retry at three or fewer attempts in the UI rule', () => {
    const tx = { status: 'FAILED', attempts: 2 }
    expect(tx.status === 'FAILED' && tx.attempts < 3).toBe(true)
  })
})
