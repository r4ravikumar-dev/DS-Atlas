import { describe, expect, it, vi } from 'vitest'
import { screen, within } from '@testing-library/react'
import { mockApi, renderWithQuery } from '@/test/utils'
import { Providers } from '@/components/Providers'
import { PublicShell } from './PublicShell'
import { ResourcesPanel } from '@/app/(public)/systems/[id]/ResourcesPanel'
import ComparePage from '@/app/(public)/compare/page'

let search = new URLSearchParams()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => '/',
  useSearchParams: () => search,
}))

const UNAUTH = { error: { code: 'UNAUTHENTICATED', message: 'Not signed in.', details: [] } }
const STATS = { data: { design_systems: 430, components: 3397, tokens: 1708, guidelines: 1942, patterns: 55, storybook_projects: 103, stories: 17600,
  variants: 12150, systems_with_github: 270, systems_with_figma: 18, content_updated_at: '2026-10-22T06:00:00Z', last_sync_at: '2026-10-22T03:00:00Z' } }

describe('Public shell', () => {
  it('works without an account and shows no admin entry point to anonymous visitors', async () => {
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      const path = new URL(String(input), 'http://localhost').pathname
      const [status, body] = path === '/api/v1/auth/me' ? [401, UNAUTH] : [200, STATS]
      return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
    }) as typeof fetch
    renderWithQuery(<Providers><PublicShell><p>content</p></PublicShell></Providers>)
    const nav = screen.getByRole('navigation', { name: 'Directory sections' })
    expect(within(nav).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/', '/components', '/tokens', '/guidelines', '/patterns', '/storybook', '/compare'])
    expect(await screen.findByText(/Checked for updates/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /admin/i })).not.toBeInTheDocument()
  })
})

describe('Official resources (public view)', () => {
  it('lists links with their status but no administrator controls', () => {
    const system = {
      id: 1, resources: [{ id: 9, system_id: 1, resource_type: 'github_repository', url: 'https://github.com/fixture/ds', label: null, origin: 'directory', source_keys: ['S01'],
        verification_status: 'verified', verification_method: 'verifier_official_page_link', evidence_url: 'https://fixture.example/', evidence_note: 'Linked from the official page.',
        http_status: null, access_note: null, is_primary: true, last_checked_at: null, updated_at: '2026-10-22T00:00:00Z' }],
    }
    renderWithQuery(<ResourcesPanel system={system as never} />)
    expect(screen.getByRole('link', { name: /github\.com\/fixture\/ds/ })).toHaveAttribute('href', 'https://github.com/fixture/ds')
    for (const name of [/confirm/i, /flag/i, /primary$/i, /remove/i, /add link/i, /re-check/i]) expect(screen.queryByRole('button', { name })).not.toBeInTheDocument()
    expect(screen.getByText('Figma resource not found (official page not checked yet).')).toBeInTheDocument()
  })
})

describe('Public compare', () => {
  it('computes a comparison from the API for the systems in the URL, without saving anything', async () => {
    search = new URLSearchParams('kind=systems&ids=1,2&labels=Alpha|Beta')
    const calls = mockApi({
      '/api/v1/design-systems': { data: [], meta: { page: 1, page_size: 8, total_items: 0, total_pages: 0 } },
      '/api/v1/compare': { data: { kind: 'systems', dimensions: ['overview'], result: {
        columns: [{ id: 1, name: 'Alpha', verification_status: 'verified' }, { id: 2, name: 'Beta', verification_status: 'unverified' }],
        dimensions: ['overview'], rows: { overview: { Organization: [{ status: 'documented', value: 'Acme', evidence: [] }, { status: 'not_documented', value: null, evidence: [] }] } },
        interpretation: [] } } },
    })
    renderWithQuery(<ComparePage />)
    expect(await screen.findByText('Acme')).toBeInTheDocument()
    expect(screen.getByText('Not documented')).toBeInTheDocument()
    const c = calls.find((x) => x.url.startsWith('/api/v1/compare'))!
    expect(c.url).toContain('ids=1%2C2')
    expect(calls.every((x) => (x.init?.method ?? 'GET') === 'GET')).toBe(true)
  })
})
