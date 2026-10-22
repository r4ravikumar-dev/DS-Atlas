import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { Providers } from '@/components/Providers'
import type { PlaygroundSchema } from '@/playground/schema'
import { Playground } from './Playground'

const schema: PlaygroundSchema = {
  component_id: 42, component: 'Button', library: 'FIXTURE UI', system_id: 1, documentation_url: 'https://fixture.example/button', tier: 'live',
  themes: ['light', 'dark'], states: [], limitations: [], metadata_only_props: ['onClick', 'icon'], metadata_only_count: 2,
  implementation: { key: 'fixture.Button', library_key: 'fixture', package: 'fixture-ui', version: '1.0.0', styling: 'FIXTURE', headless: false },
  controls: [
    { name: 'disabled', kind: 'boolean', documented: true, provenance: 'documented', default: false, default_source: 'documented', type_text: 'boolean' },
    { name: 'size', kind: 'enum', options: ['small', 'medium', 'large'], documented: true, provenance: 'documented', default: 'medium', default_source: 'documented', type_text: '`small` | `medium` | `large`' },
    { name: 'variant', kind: 'enum', options: ['solid', 'outlined', 'dashed', 'text', 'link'], documented: false, provenance: 'implementation', default: undefined, default_source: null },
    { name: 'children', kind: 'string', max_length: 20, documented: false, provenance: 'preview', default: 'Button', default_source: 'preview' },
  ],
}

const config = () => JSON.parse(screen.getByText(/"size"/).textContent!)

describe('Playground', () => {
  it('generates one control per schema property, with type and default provenance', () => {
    render(<Providers><Playground schema={schema} /></Providers>)
    const panel = screen.getByRole('complementary', { name: 'Properties' })
    expect(within(panel).getByRole('switch', { name: /disabled/ })).not.toBeChecked()
    expect(within(panel).getByRole('radiogroup', { name: /size/ })).toBeInTheDocument()
    expect(within(panel).getByRole('combobox', { name: /variant/ })).toBeInTheDocument()
    expect(within(panel).getByRole('textbox', { name: /children/ })).toHaveValue('Button')
    expect(panel).toHaveTextContent('documented default: medium')
    expect(panel).toHaveTextContent('preview sample: Button')
    expect(panel).toHaveTextContent('2 more documented props aren')
    expect(within(panel).queryByRole('textbox', { name: /onClick/ })).toBeNull()
  })

  it('updates one property without touching the others, and resets to the stated defaults', () => {
    render(<Providers><Playground schema={schema} /></Providers>)
    fireEvent.click(screen.getByRole('radio', { name: 'large' }))
    fireEvent.click(screen.getByRole('switch', { name: /disabled/ }))
    fireEvent.change(screen.getByRole('combobox', { name: /variant/ }), { target: { value: 'dashed' } })
    expect(config()).toEqual({ disabled: true, size: 'large', variant: 'dashed', children: 'Button' })
    fireEvent.change(screen.getByRole('textbox', { name: /children/ }), { target: { value: 'x'.repeat(50) } })
    expect(config().children).toHaveLength(20)
    fireEvent.click(screen.getByRole('button', { name: /reset/i }))
    expect(config()).toEqual({ disabled: false, size: 'medium', children: 'Button' })
  })

  it('keeps each instance’s state separate and shows a real import snippet for live packages', () => {
    render(<Providers><Playground schema={schema} /><Playground schema={{ ...schema, component_id: 43 }} /></Providers>)
    fireEvent.click(screen.getAllByRole('radio', { name: 'small' })[0])
    const sizes = screen.getAllByText(/"size"/).map((n) => JSON.parse(n.textContent!).size)
    expect(sizes).toEqual(['small', 'medium'])
    expect(screen.getAllByText(/import \{ Button \} from 'fixture-ui'/)).toHaveLength(2)
    expect(screen.getAllByTitle(/preview/)[0].tagName).toBe('IFRAME')
  })
})
