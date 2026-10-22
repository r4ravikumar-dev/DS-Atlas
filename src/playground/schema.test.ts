import { describe, expect, it } from 'vitest'
import { defaults, snippet, split, validateConfig, type PlaygroundSchema } from './schema'

const schema = {
  component_id: 1, component: 'Button', library: 'Mantine', system_id: 1, documentation_url: null, tier: 'live', themes: ['light'], states: [], limitations: [],
  implementation: { key: 'mantine.Button', library_key: 'mantine', package: '@mantine/core', version: '9.7.3', styling: '', headless: false },
  controls: [
    { name: 'disabled', kind: 'boolean', documented: true, provenance: 'documented', default: undefined, default_source: null },
    { name: 'size', kind: 'enum', options: ['sm', 'md'], documented: false, provenance: 'implementation', default: 'sm', default_source: 'implementation' },
    { name: 'value', kind: 'number', min: 0, max: 100, documented: false, provenance: 'implementation', default: 60, default_source: 'implementation' },
    { name: 'children', kind: 'string', max_length: 10, documented: false, provenance: 'preview', default: 'Button', default_source: 'preview' },
  ],
} satisfies PlaygroundSchema

describe('playground configuration', () => {
  it('starts from the defaults the schema states and invents none', () => {
    expect(defaults(schema)).toEqual({ size: 'sm', value: 60, children: 'Button' })
  })

  it('drops unknown props and rejects values of the wrong kind', () => {
    const cfg = validateConfig(schema, { size: 'xl', disabled: 'yes', value: 500, children: 'A very long label\u0007', onClick: 'alert(1)', dangerouslySetInnerHTML: { __html: 'x' } })
    expect(cfg).toEqual({ value: 100, children: 'A very lon' })
  })

  it('keeps other values when one changes, and separates preview content from component props', () => {
    const cfg = validateConfig(schema, { ...defaults(schema), disabled: true })
    expect(split(schema, cfg)).toEqual({ props: { size: 'sm', value: 60, disabled: true }, content: { children: 'Button' } })
  })

  it('renders a snippet from the real package and export name', () => {
    expect(snippet(schema, { size: 'md', disabled: true, children: 'Save' })).toBe("import { Button } from '@mantine/core'\n\n<Button disabled size=\"md\">Save</Button>")
    expect(snippet({ ...schema, tier: 'adapter' }, {})).toBeNull()
  })
})
