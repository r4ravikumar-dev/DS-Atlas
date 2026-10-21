import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'

export function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

/** Mock fetch with a router of path → JSON body (FIXTURE responses shaped like the backend contract). */
export function mockApi(routes: Record<string, unknown | ((url: URL, init?: RequestInit) => unknown)>, status = 200) {
  const calls: { url: string; init?: RequestInit }[] = []
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    calls.push({ url: url.pathname + url.search, init })
    const key = Object.keys(routes).find((k) => url.pathname === k || url.pathname.startsWith(k + '/') && k.endsWith('*'))
      ?? Object.keys(routes).find((k) => url.pathname === k)
    const body = key ? routes[key] : { error: { code: 'NOT_FOUND', message: 'no mock', details: [] } }
    const data = typeof body === 'function' ? (body as (u: URL, i?: RequestInit) => unknown)(url, init) : body
    return new Response(JSON.stringify(data), { status: key ? status : 404, headers: { 'content-type': 'application/json' } })
  }) as typeof fetch
  return calls
}
