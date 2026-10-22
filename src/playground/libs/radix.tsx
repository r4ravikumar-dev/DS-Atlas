'use client'

import './headless.css'
import { Accordion, Checkbox, Collapsible, Dialog, Progress, Slider, Switch, Tabs, Toggle } from 'radix-ui'
import type { RenderProps } from './types'

/** Radix Primitives 1.8.1 — real primitives (behaviour and ARIA from the library); neutral platform styles only. */
export default function RadixRenderer({ impl, props, content, theme }: RenderProps) {
  const p = props as Record<string, never>
  return (
    <div className="pg-headless" data-theme={theme}>
      {impl === 'Switch' && <label className="pg-row"><Switch.Root {...p} className="pg-switch-track"><Switch.Thumb className="pg-switch-thumb" /></Switch.Root>Airplane mode</label>}
      {impl === 'Checkbox' && <label className="pg-row"><Checkbox.Root {...p} className="pg-box"><Checkbox.Indicator>✓</Checkbox.Indicator></Checkbox.Root>{content.label}</label>}
      {impl === 'Slider' && (
        <Slider.Root defaultValue={[40]} {...p} aria-label="Volume" style={{ position: 'relative', display: 'flex', alignItems: 'center', width: p.orientation === 'vertical' ? 20 : 280, height: p.orientation === 'vertical' ? 200 : 20, flexDirection: p.orientation === 'vertical' ? 'column' : 'row' }}>
          <Slider.Track className="pg-track" style={p.orientation === 'vertical' ? { width: 4, height: '100%' } : undefined}><Slider.Range className="pg-range" style={p.orientation === 'vertical' ? { width: '100%' } : undefined} /></Slider.Track>
          <Slider.Thumb className="pg-thumb" style={{ display: 'block' }} />
        </Slider.Root>
      )}
      {impl === 'Progress' && <Progress.Root value={66} {...p} className="pg-track" style={{ overflow: 'hidden' }}><Progress.Indicator className="pg-fill" style={{ width: `${(Number(p.value ?? 66) / Number(p.max ?? 100)) * 100}%` }} /></Progress.Root>}
      {impl === 'Toggle' && <Toggle.Root {...p} aria-label={content.children}>{content.children}</Toggle.Root>}
      {impl === 'Tabs' && (
        <Tabs.Root defaultValue="account" {...p} style={{ width: 360, display: p.orientation === 'vertical' ? 'flex' : 'block', gap: 12 }}>
          <Tabs.List className="pg-tabs-list" aria-label="Manage your account" style={p.orientation === 'vertical' ? { flexDirection: 'column', borderBottom: 0 } : undefined}><Tabs.Trigger value="account">Account</Tabs.Trigger><Tabs.Trigger value="password">Password</Tabs.Trigger></Tabs.List>
          <Tabs.Content value="account" className="pg-panel">Make changes to your account.</Tabs.Content><Tabs.Content value="password" className="pg-panel">Change your password.</Tabs.Content>
        </Tabs.Root>
      )}
      {impl === 'Accordion' && (
        // `type` decides the value shape, so the root is remounted when it changes (the frame keys on the configuration)
        <Accordion.Root {...(p as object)} type={(p.type as 'single' | 'multiple') ?? 'single'} style={{ width: 360 }}>
          {['Is it accessible?', 'Is it unstyled?', 'Can it be animated?'].map((q, i) => (
            <Accordion.Item key={q} value={`item-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
              <Accordion.Header style={{ margin: 0 }}><Accordion.Trigger style={{ width: '100%', textAlign: 'left', border: 0, background: 'none', padding: '10px 0' }}>{q}</Accordion.Trigger></Accordion.Header>
              <Accordion.Content className="pg-panel">Answer {i + 1}.</Accordion.Content>
            </Accordion.Item>
          ))}
        </Accordion.Root>
      )}
      {impl === 'Collapsible' && (
        <Collapsible.Root {...p} style={{ width: 320 }}>
          <div className="pg-row" style={{ justifyContent: 'space-between', width: '100%' }}><span>{content.title}</span><Collapsible.Trigger>Toggle</Collapsible.Trigger></div>
          <Collapsible.Content className="pg-panel">{content.children}</Collapsible.Content>
        </Collapsible.Root>
      )}
      {impl === 'Dialog' && (
        <Dialog.Root {...p}>
          <Dialog.Trigger>Open dialog</Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="pg-dialog-backdrop" />
            <Dialog.Content className="pg-dialog pg-headless" data-theme={theme}>
              <Dialog.Title style={{ margin: '0 0 8px', fontSize: 16 }}>{content.title}</Dialog.Title>
              <Dialog.Description style={{ margin: '0 0 16px', color: 'var(--muted)' }}>{content.children}</Dialog.Description>
              <Dialog.Close>Close</Dialog.Close>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      )}
    </div>
  )
}
