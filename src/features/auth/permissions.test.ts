import { describe, expect, it } from 'vitest'
import { can } from './api'
import type { User } from '@/lib/api/types'

const u = (role: User['role']) => ({ id: '1', email: 'x@y.z', name: '', role, is_active: true, created_at: '' }) as User

describe('can()', () => {
  it('mirrors the backend role ranking (UI hint only; the API enforces access)', () => {
    expect(can(undefined, 'viewer')).toBe(false)
    expect(can(u('viewer'), 'researcher')).toBe(false)
    expect(can(u('researcher'), 'researcher')).toBe(true)
    expect(can(u('admin'), 'researcher')).toBe(true)
    expect(can(u('researcher'), 'admin')).toBe(false)
  })
})
