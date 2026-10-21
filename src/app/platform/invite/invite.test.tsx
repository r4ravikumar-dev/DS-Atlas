import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { mockApi, renderWithQuery } from '@/test/utils'

const replace = vi.fn()
const push = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace, push }),
  usePathname: () => '/platform/invite',
  useSearchParams: () => new URLSearchParams(),
}))

describe('Invite acceptance page', () => {
  it('displays error if no token in fragment or search', async () => {
    window.location.hash = ''
    window.location.search = ''

    const { default: InvitePage } = await import('./page')
    renderWithQuery(<InvitePage />)

    expect(await screen.findByText('Missing Invitation Token')).toBeInTheDocument()
  })

  it('validates token from fragment and renders role and email hint', async () => {
    window.location.hash = '#token=test-valid-token'
    window.location.search = ''

    mockApi({
      '/api/v1/auth/invitations/validate': {
        data: {
          kind: 'invitation',
          email_hint: 'r***@example.com',
          role: 'researcher',
          expires_at: '2026-12-31T23:59:59Z',
          email_delivery: false,
        },
      },
    })

    const { default: InvitePage } = await import('./page')
    renderWithQuery(<InvitePage />)

    expect(await screen.findByText('Accept Invitation')).toBeInTheDocument()
    expect(screen.getAllByText('r***@example.com').length).toBeGreaterThan(0)
    expect(screen.getByText('researcher')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Send Verification Code/i })).toBeInTheDocument()
  })
})
