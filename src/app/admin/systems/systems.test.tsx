import { describe, expect, it, vi } from 'vitest'
import { screen, within } from '@testing-library/react'
import { mockApi, renderWithQuery } from '@/test/utils'
import { ResourceLinks } from '@/components/platform/ResourceLinks'
import SystemsPage from './page'

let search = new URLSearchParams()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => '/admin/systems',
  useSearchParams: () => search,
}))

const SYSTEM = {
  id: 7, key: 'dsys:fixture-example', name: 'FIXTURE System', organization: 'FIXTURE Org', description: 'FIXTURE description.',
  documentation_url: null, repository_url: null, storybook_url: null, official_docs_url: null, related_urls: [], verification_coverage: {},
  frameworks: ['React'], platforms: ['Web'], styling_strategy: null, token_architecture: null, accessibility_documentation: null,
  source_count: 3, source_keys: ['S01', 'S02', 'S03'], verification_status: 'partially_verified', component_count: 12, token_count: 4,
  deprecated: false, last_verified_at: null, created_at: null, updated_at: null, resource_count: 3,
  links: [
    { type: 'official_website', url: 'https://fixture.example/', verified: true },
    { type: 'github_repository', url: 'https://github.com/fixture/system', verified: false },
    { type: 'additional_resource', url: 'https://fixture.example/blog', verified: false },
  ],
}
const FACETS = { data: { frameworks: [], sources: [], verification_status: [], platforms: [], resources: [] } }
const page = (rows: unknown[], total = rows.length) => ({ data: rows, meta: { page: 1, page_size: 24, total_items: total, total_pages: Math.max(1, Math.ceil(total / 24)) } })

describe('ResourceLinks', () => {
  it('renders only links that exist, marks verification, and opens safely', () => {
    renderWithQuery(<ResourceLinks links={SYSTEM.links as never} />)
    const list = screen.getByRole('list', { name: 'Resources' })
    const links = within(list).getAllByRole('link')
    expect(links).toHaveLength(2) // additional resources are excluded by default; no Figma/Storybook placeholders
    expect(links[0]).toHaveAttribute('href', 'https://fixture.example/')
    expect(links[0]).toHaveAttribute('rel', expect.stringContaining('noopener'))
    expect(links[0]).toHaveAttribute('referrerpolicy', 'no-referrer')
    expect(links[0]).toHaveAttribute('target', '_blank')
    expect(within(links[0]).getByLabelText('verified')).toBeInTheDocument()
    expect(within(links[1]).getByText('unverified')).toBeInTheDocument()
    expect(screen.queryByText(/Figma/)).not.toBeInTheDocument()
  })

  it('renders nothing when a system has no links (no inactive buttons)', () => {
    const { container } = renderWithQuery(<ResourceLinks links={[]} />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('Design-system catalog', () => {
  it('shows backend records with links and counts, and sends filters to the server', async () => {
    search = new URLSearchParams('resource=github_repository&platform=Web')
    const calls = mockApi({ '/api/v1/design-systems': page([SYSTEM], 61), '/api/v1/design-systems/facets': FACETS })
    renderWithQuery(<SystemsPage />)
    const card = await screen.findByTestId('system-card')
    expect(within(card).getByRole('link', { name: 'FIXTURE System' })).toHaveAttribute('href', '/admin/systems/7')
    expect(within(card).getByText('12')).toBeInTheDocument()
    expect(within(card).getAllByRole('link').map((a) => a.getAttribute('href'))).toContain('https://github.com/fixture/system')
    expect(screen.getByText('61 systems')).toBeInTheDocument()
    const listCall = calls.find((c) => c.url.startsWith('/api/v1/design-systems?'))!
    expect(listCall.url).toContain('resource=github_repository')
    expect(listCall.url).toContain('platform=Web')
  })

  it('distinguishes an empty result from loading and from errors', async () => {
    search = new URLSearchParams('q=nothing-matches')
    mockApi({ '/api/v1/design-systems': page([]), '/api/v1/design-systems/facets': FACETS })
    renderWithQuery(<SystemsPage />)
    expect(await screen.findByText('No systems match these filters')).toBeInTheDocument()
  })

  it('shows the API error instead of an empty list', async () => {
    search = new URLSearchParams()
    mockApi({ '/api/v1/design-systems': { error: { code: 'INTERNAL', message: 'boom', details: [] } }, '/api/v1/design-systems/facets': FACETS }, 500)
    renderWithQuery(<SystemsPage />)
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByTestId('system-card')).not.toBeInTheDocument()
  })
})
