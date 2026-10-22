import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithQuery } from '@/test/utils'
import { ResourcesPanel } from './[id]/ResourcesPanel'

describe('Official resources panel (anonymous view of the admin component)', () => {
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
