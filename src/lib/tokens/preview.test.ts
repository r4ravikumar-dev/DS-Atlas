import { describe, expect, it } from 'vitest'
import { groupFoundations, isColor, isShadow, previewKind, toMs, toPx } from './preview'

const t = (path: string, raw: string | null, type: string | null = null, resolved: string | null = null) => ({ path, raw_value: raw, resolved_value: resolved, type })

describe('token previews', () => {
  it('recognises colours only when the stored value is valid CSS', () => {
    expect(isColor('#228be6')).toBe(true)
    expect(isColor('rgba(0,0,0,0.45)')).toBe(true)
    expect(isColor('oklch(0.7 0.1 200)')).toBe(true)
    expect(isColor('blue')).toBe(false) // named presets with no stored value are not guessed
    expect(isColor('red;background:url(https://x)')).toBe(false)
  })

  it('never assumes units for bare numbers', () => {
    expect(previewKind(t('Anchor.linkPaddingBlock', '4', 'number'))).toBe('none')
    expect(previewKind(t('space-200', '8px'))).toBe('spacing')
    expect(previewKind(t('radius-card', '12px'))).toBe('radius')
    expect(previewKind(t('font-size-lg', '1.125rem'))).toBe('font-size')
  })

  it('prefers the resolved value when the backend has one', () => {
    expect(previewKind(t('color.brand', '{color.blue.500}', 'color', '#0055ff'))).toBe('color')
    expect(previewKind(t('color.brand', '{color.blue.500}', 'color'))).toBe('none')
  })

  it('handles motion, weight, family and shadow tokens', () => {
    expect(previewKind(t('duration-fast-02', '110ms'))).toBe('duration')
    expect(previewKind(t('motion.easing.standard', 'cubic-bezier(0.2, 0, 0.38, 0.9)'))).toBe('easing')
    expect(previewKind(t('--mantine-font-weight-bold', '700', 'fontWeight'))).toBe('font-weight')
    expect(previewKind(t('font-family-product', 'Cereal, Helvetica, sans-serif'))).toBe('font-family')
    expect(isShadow('0 1px 2px rgba(0,0,0,0.2), 0 4px 8px #0003')).toBe(true)
    expect(previewKind(t('--mantine-shadow-lg', '1', 'shadow'))).toBe('none')
  })

  it('converts units for proportional diagrams', () => {
    expect(toPx('1.5rem')).toBe(24)
    expect(toPx('12px')).toBe(12)
    expect(toMs('0.2s')).toBe(200)
  })

  it('groups foundations in display order and drops what it cannot show', () => {
    const groups = groupFoundations([t('space-1', '4px'), t('c', '#fff'), t('x', 'n/a')])
    expect(groups.map((g) => g.kind)).toEqual(['color', 'spacing'])
  })
})
