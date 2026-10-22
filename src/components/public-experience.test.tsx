import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { mockApi, renderWithQuery } from '@/test/utils'
import { Providers } from '@/components/Providers'
import type { System } from '@/lib/api/types'
import { SiteHeader } from './navigation/SiteHeader'
import { SystemCard } from './catalog/SystemCard'
import { Monogram, initials } from './catalog/Monogram'
import { ResourceIndicators } from './catalog/ResourceIndicators'
import { ComparisonMatrix, type ComparisonResult } from './comparison/ComparisonMatrix'
import { HeroIllustration } from './landing/HeroIllustration'
import { Hero } from './landing/Hero'
import ComparePage from '@/app/(public)/compare/page'

let search = new URLSearchParams()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => '/components',
  useSearchParams: () => search,
}))

const SYSTEM = {
  id: 7, key: 'dsys:fixture', slug: 'fixture-system', name: 'FIXTURE System', organization: 'Fixture Org', description: 'A FIXTURE design system used in tests.',
  frameworks: ['React Vanilla'], platforms: [], verification_status: 'partially_verified', component_count: 12, token_count: 3, source_count: 2,
  links: [{ type: 'official_website', url: 'https://fixture.example', verified: true }, { type: 'github_repository', url: 'https://github.com/fixture/ds', verified: false }],
} as unknown as System

describe('Site header', () => {
  it('shows the public sections, marks the current one, and never asks anonymous visitors for a session', () => {
    const calls = mockApi({})
    renderWithQuery(<Providers><SiteHeader /></Providers>)
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    expect(within(nav).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/systems', '/components', '/tokens', '/patterns', '/playground', '/compare'])
    expect(within(nav).getByRole('link', { name: 'Components' })).toHaveAttribute('aria-current', 'page')
    expect(screen.queryByRole('link', { name: /admin/i })).not.toBeInTheDocument()
    expect(calls.some((c) => c.url.startsWith('/api/v1/auth/me'))).toBe(false)
  })

  it('opens the search dialog from the keyboard shortcut', () => {
    mockApi({})
    renderWithQuery(<Providers><SiteHeader /></Providers>)
    fireEvent.keyDown(window, { key: 'k', metaKey: true })
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Search' })).toBeInTheDocument()
  })
})

describe('System card', () => {
  it('links into the system workspace and lists only the resources that exist, with no status labels', () => {
    renderWithQuery(<Providers><SystemCard system={SYSTEM} /></Providers>)
    expect(screen.getByRole('link', { name: 'FIXTURE System' })).toHaveAttribute('href', '/systems/fixture-system')
    expect(screen.getAllByRole('link')).toHaveLength(1)
    expect(screen.getByText('Fixture Org')).toBeInTheDocument()
    const res = screen.getByRole('list', { name: 'Official resources' })
    expect(within(res).getAllByRole('listitem').map((li) => li.textContent)).toEqual(['Website', 'GitHub'])
    expect(document.body.textContent).not.toMatch(/verified|unverified|directory-listed|not recorded|missing/i)
  })

  it('shows the official logo when the system publishes one, and falls back to initials when it fails to load', () => {
    const { container } = renderWithQuery(<Providers><SystemCard system={{ ...SYSTEM, logo: { url: 'https://fixture.example/icon.svg', alt: 'FIXTURE icon' } }} /></Providers>)
    const img = container.querySelector('img')!
    expect(img).toHaveAttribute('src', 'https://fixture.example/icon.svg')
    expect(img).toHaveAttribute('referrerpolicy', 'no-referrer')
    fireEvent.error(img)
    expect(container.querySelector('img')).toBeNull()
    expect(container.textContent).toContain('FS')
  })

  it('uses initials, not an invented logo', () => {
    expect(initials('Ant Design')).toBe('AD')
    expect(initials('Carbon')).toBe('Ca')
    const { container } = renderWithQuery(<Monogram name="Ant Design" />)
    expect(container.querySelector('img')).toBeNull()
  })

  it('renders nothing (no "missing" labels) when no links were recorded', () => {
    const { container } = renderWithQuery(<ResourceIndicators links={[]} />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('Comparison matrix', () => {
  const result: ComparisonResult = {
    columns: [{ id: 1, name: 'Alpha', verification_status: 'verified' }, { id: 2, name: 'Beta', verification_status: 'unverified' }],
    dimensions: ['overview'],
    rows: { overview: {
      Organization: [{ status: 'documented', value: 'Acme', evidence: ['https://alpha.example'] }, { status: 'not_documented', value: null, evidence: [] }],
      Kind: [{ status: 'documented', value: 'system', evidence: [] }, { status: 'documented', value: 'system', evidence: [] }],
      Keyboard: [{ status: 'not_inspected', value: null, evidence: [] }, { status: 'not_applicable', value: null, evidence: [] }],
    } },
    interpretation: [],
  }

  it('never presents an undocumented value as unsupported, and can hide identical rows', async () => {
    renderWithQuery(<Providers><ComparisonMatrix result={result} base="/systems" /></Providers>)
    expect(screen.getByText('Acme')).toBeInTheDocument()
    expect(screen.getAllByText('Not documented').length).toBeGreaterThan(0)
    expect(screen.queryByText(/inspected/i)).not.toBeInTheDocument() // internal processing states are never shown
    expect(screen.queryByText(/unsupported$/i)).not.toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: /Kind/ })).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Only show differences'))
    await waitFor(() => expect(screen.queryByRole('rowheader', { name: /^Kind/ })).not.toBeInTheDocument())
    expect(screen.getByRole('rowheader', { name: /Organization/ })).toHaveTextContent('differs')
  })
})

describe('Compare workspace', () => {
  it('computes from the URL selection with read-only requests', async () => {
    search = new URLSearchParams('kind=systems&ids=1,2&labels=Alpha|Beta')
    const calls = mockApi({
      '/api/v1/design-systems': { data: [], meta: { page: 1, page_size: 8, total_items: 0, total_pages: 0 } },
      '/api/v1/compare': { data: { kind: 'systems', dimensions: ['overview'], result: {
        columns: [{ id: 1, name: 'Alpha', verification_status: 'verified' }, { id: 2, name: 'Beta', verification_status: 'unverified' }],
        dimensions: ['overview'], rows: { overview: { Organization: [{ status: 'documented', value: 'Acme', evidence: [] }, { status: 'not_documented', value: null, evidence: [] }] } },
        interpretation: [] } } },
    })
    renderWithQuery(<Providers><ComparePage /></Providers>)
    expect(await screen.findByText('Acme')).toBeInTheDocument()
    expect(calls.find((c) => c.url.startsWith('/api/v1/compare'))!.url).toContain('ids=1%2C2')
    expect(calls.every((c) => (c.init?.method ?? 'GET') === 'GET')).toBe(true)
  })
})

describe('Hero', () => {
  it('is a plain, script-free search form with two ways in and a decorative illustration', () => {
    const { container } = renderWithQuery(<Hero systems={432} />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Explore design systems, component by component.')
    const form = screen.getByRole('search')
    expect(form).toHaveAttribute('action', '/search')
    expect(within(form).getByRole('searchbox')).toHaveAttribute('name', 'q')
    expect(screen.getByRole('link', { name: /browse design systems/i })).toHaveAttribute('href', '/systems')
    expect(screen.getByRole('link', { name: /try components live/i })).toHaveAttribute('href', '/playground')
    expect(container.querySelector('canvas')).toBeNull()
  })

  it('keeps the illustration out of the accessibility tree', () => {
    const { container } = renderWithQuery(<HeroIllustration />)
    expect(container.firstElementChild).toHaveAttribute('aria-hidden', 'true')
  })
})

describe('Automated accessibility (axe, WCAG 2.2 AA rules that jsdom can evaluate)', () => {
  it('finds no violations in the card, resource indicators and comparison matrix', async () => {
    const axe = (await import('axe-core')).default
    const result: ComparisonResult = {
      columns: [{ id: 1, name: 'Alpha', verification_status: 'verified' }, { id: 2, name: 'Beta', verification_status: 'unverified' }],
      dimensions: ['overview'],
      rows: { overview: { Organization: [{ status: 'documented', value: 'Acme', evidence: [] }, { status: 'not_documented', value: null, evidence: [] }] } },
      interpretation: ['FIXTURE observation.'],
    }
    const { container } = renderWithQuery(<Providers><main><SystemCard system={SYSTEM} /><ComparisonMatrix result={result} base="/systems" /></main></Providers>)
    const res = await axe.run(container, { runOnly: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'], rules: { 'color-contrast': { enabled: false } } })
    expect(res.violations.map((v) => `${v.id}: ${v.nodes[0]?.target.join(' ')}`)).toEqual([])
  })
})

describe('Public empty and error states', () => {
  it('offer the page-specific action plus "Back to Site" to the public homepage — never the admin area', async () => {
    const { EmptyState, ErrorNotice, RecoveryLink } = await import('./kit/states')
    const { container } = renderWithQuery(
      <>
        <EmptyState title="No results" action={<RecoveryLink href="/search">Clear search</RecoveryLink>} />
        <ErrorNotice title="Failed" retryHref="/systems" />
      </>,
    )
    const back = screen.getAllByRole('link', { name: /back to site/i })
    expect(back).toHaveLength(2)
    back.forEach((a) => expect(a).toHaveAttribute('href', '/'))
    expect(screen.getByRole('link', { name: 'Clear search' })).toHaveAttribute('href', '/search')
    expect(screen.getByRole('link', { name: /try again/i })).toHaveAttribute('href', '/systems')
    expect([...container.querySelectorAll('a')].some((a) => /admin|dashboard/i.test(a.getAttribute('href') ?? '') || /dashboard/i.test(a.textContent ?? ''))).toBe(false)
  })

  it('can omit "Back to Site" for inline sections of a working page', async () => {
    const { EmptyState } = await import('./kit/states')
    renderWithQuery(<EmptyState title="No prop tables" backToSite={false} />)
    expect(screen.queryByRole('link', { name: /back to site/i })).toBeNull()
  })
})
