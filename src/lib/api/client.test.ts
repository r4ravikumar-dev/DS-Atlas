import { describe, expect, it } from 'vitest'
import { api, ApiError, toQueryString } from './client'
import { mockApi } from '@/test/utils'

describe('toQueryString', () => {
  it('encodes arrays as repeated params and skips empty values', () => {
    expect(toQueryString({ q: 'a b', family: ['Dialog', 'Tabs'], empty: '', none: undefined, page: 2 })).toBe('?q=a+b&family=Dialog&family=Tabs&page=2')
    expect(toQueryString({})).toBe('')
  })
})

describe('api()', () => {
  it('returns parsed JSON for successful responses', async () => {
    mockApi({ '/api/v1/health': { status: 'ok' } })
    await expect(api('/health')).resolves.toEqual({ status: 'ok' })
  })

  it('throws ApiError carrying the backend error envelope', async () => {
    mockApi({ '/api/v1/sources': { error: { code: 'FORBIDDEN', message: 'Nope', details: [{ field: 'x', reason: 'y' }], request_id: 'req_1' } } }, 403)
    const err = (await api('/sources').catch((e) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err).toMatchObject({ status: 403, code: 'FORBIDDEN', message: 'Nope', requestId: 'req_1' })
    expect(err.details[0].field).toBe('x')
  })

  it('sends the CSRF header from the cookie on unsafe methods only', async () => {
    document.cookie = 'dsrp_csrf=tok123'
    const calls = mockApi({ '/api/v1/comparisons': { data: {} } })
    await api('/comparisons', { method: 'POST', body: { a: 1 } })
    await api('/comparisons')
    const h0 = calls[0].init!.headers as Record<string, string>
    const h1 = calls[1].init!.headers as Record<string, string>
    expect(h0['X-CSRF-Token']).toBe('tok123')
    expect(h0['Content-Type']).toBe('application/json')
    expect(h1['X-CSRF-Token']).toBeUndefined()
    expect(calls[0].init!.credentials).toBe('same-origin')
  })

  it('maps network failures to a NETWORK_ERROR ApiError', async () => {
    globalThis.fetch = (async () => { throw new TypeError('Failed to fetch') }) as typeof fetch
    const err = (await api('/health').catch((e) => e)) as ApiError
    expect(err).toMatchObject({ status: 0, code: 'NETWORK_ERROR' })
  })
})
