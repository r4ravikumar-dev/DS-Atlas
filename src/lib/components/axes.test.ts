import { describe, expect, it } from 'vitest'
import { propsSignature, variantAxes } from './axes'

const prop = (name: string, type: string | null, extra: Partial<{ subcomponent: string; default_value: string; required: string }> = {}) =>
  ({ name, type, subcomponent: extra.subcomponent ?? null, default_value: extra.default_value ?? null, description: null, required: extra.required ?? null })

describe('variant axes', () => {
  it('only reads unions of string literals from the documented type', () => {
    const axes = variantAxes([
      prop('variant', `"primary" | "secondary" | undefined`, { default_value: '"primary"' }),
      prop('size', 'string'),
      prop('color', 'MantineColor'),
      prop('onClick', `"a" | "b"`),
    ])
    expect(axes).toEqual([{ name: 'variant', part: null, values: ['primary', 'secondary'], default: 'primary' }])
  })

  it('generates a labelled signature from the documented props', () => {
    const sig = propsSignature('Button', [prop('disabled', 'boolean'), prop('aria-label', 'string', { required: 'true' })])
    expect(sig).toContain('interface ButtonProps')
    expect(sig).toContain('disabled?: boolean')
    expect(sig).toContain('"aria-label": string')
  })
})
