import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { mockApi, renderWithQuery } from '@/test/utils'

const replace = vi.fn()
const push = vi.fn()
let search = new URLSearchParams()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace, push }),
  usePathname: () => '/platform/storybook',
  useSearchParams: () => search,
}))

const PROJECT = {
  id: 1,
  slug: 'carbon-react',
  name: 'Carbon React',
  title: 'IBM Carbon Design System (React)',
  storybook_url: 'https://react.carbondesignsystem.com',
  resolved_url: 'https://react.carbondesignsystem.com',
  status: 'public_available',
  framework: 'react',
  storybook_version: '7.6.0',
  total_entries: 450,
  component_entries: 120,
  docs_entries: 50,
  stories_extracted: 380,
  variants_extracted: 210,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('Storybook explorer page', () => {
  it('renders showcase projects list with counts and framework tags', async () => {
    mockApi({
      '/api/v1/storybook/projects': {
        data: [PROJECT],
        meta: { page: 1, page_size: 25, total_items: 1, total_pages: 1 },
      },
      '/api/v1/storybook/stories': {
        data: [],
        meta: { page: 1, page_size: 25, total_items: 0, total_pages: 0 },
      },
      '/api/v1/storybook/variants': {
        data: [],
        meta: { page: 1, page_size: 25, total_items: 0, total_pages: 0 },
      },
      '/api/v1/auth/me': {
        data: { id: 'u1', email: 'user@example.com', name: 'User', role: 'viewer', is_active: true, created_at: '' },
      },
    })

    const { default: StorybookPage } = await import('./page')
    renderWithQuery(<StorybookPage />)

    expect(await screen.findByText('IBM Carbon Design System (React)')).toBeInTheDocument()
    expect(screen.getByText('react')).toBeInTheDocument()
    expect(screen.getByText('380')).toBeInTheDocument()
    expect(screen.getByText('210')).toBeInTheDocument()
  })
})
