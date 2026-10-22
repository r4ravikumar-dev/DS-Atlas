'use client'

import './headless.css'
import { Checkbox } from '@base-ui/react/checkbox'
import { Collapsible } from '@base-ui/react/collapsible'
import { Dialog } from '@base-ui/react/dialog'
import { Progress } from '@base-ui/react/progress'
import { Slider } from '@base-ui/react/slider'
import { Switch } from '@base-ui/react/switch'
import { Tabs } from '@base-ui/react/tabs'
import { Toggle } from '@base-ui/react/toggle'
import type { RenderProps } from './types'

/** Base UI 1.9.0 — real components (behaviour and ARIA from the library); neutral platform styles only. */
export default function BaseUiRenderer({ impl, props, content, theme }: RenderProps) {
  const p = props as Record<string, never>
  return (
    <div className="pg-headless" data-theme={theme}>
      {impl === 'Switch' && <label className="pg-row"><Switch.Root {...p} className="pg-switch-track"><Switch.Thumb className="pg-switch-thumb" /></Switch.Root>Notifications</label>}
      {impl === 'Checkbox' && <label className="pg-row"><Checkbox.Root {...p} className="pg-box"><Checkbox.Indicator>✓</Checkbox.Indicator></Checkbox.Root>{content.label}</label>}
      {impl === 'Slider' && (
        <Slider.Root defaultValue={40} {...p} style={{ width: 280 }}>
          <Slider.Control style={{ display: 'flex', alignItems: 'center', height: 20 }}>
            <Slider.Track className="pg-track"><Slider.Indicator className="pg-range" /><Slider.Thumb className="pg-thumb" aria-label="Volume" /></Slider.Track>
          </Slider.Control>
        </Slider.Root>
      )}
      {impl === 'Toggle' && <Toggle {...p} aria-label={content.children}>{content.children}</Toggle>}
      {impl === 'Progress' && (
        <Progress.Root value={40} {...p} style={{ width: 280 }}>
          <Progress.Track className="pg-track" style={{ overflow: 'hidden' }}><Progress.Indicator className="pg-fill" /></Progress.Track>
        </Progress.Root>
      )}
      {impl === 'Tabs' && (
        <Tabs.Root defaultValue="overview" {...p} style={{ width: 360 }}>
          <Tabs.List className="pg-tabs-list"><Tabs.Tab value="overview">Overview</Tabs.Tab><Tabs.Tab value="projects">Projects</Tabs.Tab><Tabs.Tab value="account">Account</Tabs.Tab></Tabs.List>
          <Tabs.Panel value="overview" className="pg-panel">Overview panel</Tabs.Panel><Tabs.Panel value="projects" className="pg-panel">Projects panel</Tabs.Panel><Tabs.Panel value="account" className="pg-panel">Account panel</Tabs.Panel>
        </Tabs.Root>
      )}
      {impl === 'Collapsible' && (
        <Collapsible.Root {...p} style={{ width: 320 }}>
          <Collapsible.Trigger>{content.title}</Collapsible.Trigger>
          <Collapsible.Panel className="pg-panel">{content.children}</Collapsible.Panel>
        </Collapsible.Root>
      )}
      {impl === 'Dialog' && (
        <Dialog.Root {...p}>
          <Dialog.Trigger>View notifications</Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Backdrop className="pg-dialog-backdrop" />
            <Dialog.Popup className="pg-dialog pg-headless" data-theme={theme}>
              <Dialog.Title style={{ margin: '0 0 8px', fontSize: 16 }}>{content.title}</Dialog.Title>
              <Dialog.Description style={{ margin: '0 0 16px', color: 'var(--muted)' }}>{content.children}</Dialog.Description>
              <Dialog.Close>Close</Dialog.Close>
            </Dialog.Popup>
          </Dialog.Portal>
        </Dialog.Root>
      )}
    </div>
  )
}
