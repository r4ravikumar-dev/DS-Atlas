import { describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { mockApi, renderWithQuery } from '@/test/utils'

const replace = vi.fn()
const push = vi.fn()
let search = new URLSearchParams('status=inspected')
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace, push }),
  usePathname: () => '/admin/sources',
  useSearchParams: () => search,
}))

// FIXTURE responses shaped like the backend contract
const SOURCE = { id: 7, key: 'S99', name: 'FIXTURE Source', url: 'https://fixture.example', domain: 'fixture.example', source_type: 'directory', adapter: 'x',
  origin: 'seed', status: 'inspected', is_paused: false, http_status: 200, pages_attempted: 4, pages_ok: 3, records_count: 1234, error_count: 1,
  last_attempted_at: null, last_success_at: null }

describe('Sources page', () => {
  it('renders rows from the API and forwards URL filters to the backend', async () => {
    const calls = mockApi({
      '/api/v1/sources': { data: [SOURCE], meta: { page: 1, page_size: 25, total_items: 1, total_pages: 1 } },
      '/api/v1/auth/me': { data: { id: 'u', email: 'v@fixture.example', name: '', role: 'viewer', is_active: true, created_at: '' } },
    })
    const { default: SourcesPage } = await import('./page')
    renderWithQuery(<SourcesPage />)
    expect(await screen.findByText('FIXTURE Source')).toBeInTheDocument()
    expect(screen.getByText('1,234')).toBeInTheDocument()
    expect(screen.getByText('3/4')).toBeInTheDocument()
    const listCall = calls.find((c) => c.url.startsWith('/api/v1/sources'))!
    expect(listCall.url).toContain('status=inspected')
    expect(listCall.url).toContain('page_size=25')
    // viewers do not see mutation controls (the API would reject them anyway)
    await waitFor(() => expect(screen.queryByRole('button', { name: /Crawl all/ })).not.toBeInTheDocument())
  })

  it('shows an error state with the backend message', async () => {
    search = new URLSearchParams()
    mockApi({ '/api/v1/sources': { error: { code: 'INTERNAL_ERROR', message: 'Database unavailable', details: [], request_id: 'req_x' } },
      '/api/v1/auth/me': { data: { id: 'u', email: 'v@fixture.example', name: '', role: 'viewer', is_active: true, created_at: '' } } }, 500)
    const { default: SourcesPage } = await import('./page')
    renderWithQuery(<SourcesPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Database unavailable')
  })
})
