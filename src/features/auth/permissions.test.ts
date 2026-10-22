import { describe, expect, it } from 'vitest'
import { isAdmin } from './api'
import type { User } from '@/lib/api/types'

const u = (role: User['role']) => ({ id: '1', email: 'x@y.z', name: '', role, is_active: true, created_at: '' }) as User

describe('isAdmin()', () => {
  it('only an administrator session unlocks the workspace (UI hint only; the API enforces access)', () => {
    expect(isAdmin(undefined)).toBe(false)
    expect(isAdmin(u('viewer'))).toBe(false)
    expect(isAdmin(u('researcher'))).toBe(false)
    expect(isAdmin(u('admin'))).toBe(true)
  })
})
