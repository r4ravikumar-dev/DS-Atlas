'use client'

import '@mantine/core/styles.css'
import { useState } from 'react'
import { Alert, Badge, Button, Checkbox, MantineProvider, Modal, Progress, Rating, SegmentedControl, Slider, Switch, Tabs } from '@mantine/core'
import type { RenderProps } from './types'

/** Mantine 9.7.3 — the real components, with Mantine's own stylesheet and default theme. */
export default function MantineRenderer({ impl, props, content, theme }: RenderProps) {
  const p = props as Record<string, never>
  return (
    <MantineProvider forceColorScheme={theme}>
      {impl === 'Button' && <Button {...p}>{content.children}</Button>}
      {impl === 'Badge' && <Badge {...p}>{content.children}</Badge>}
      {impl === 'Switch' && <Switch {...p} label={content.label} />}
      {impl === 'Checkbox' && <Checkbox {...p} label={content.label} />}
      {impl === 'Slider' && <div style={{ width: 320 }}><Slider {...p} defaultValue={40} /></div>}
      {impl === 'Progress' && <div style={{ width: 320 }}><Progress value={60} {...p} /></div>}
      {impl === 'Alert' && <div style={{ width: 420 }}><Alert {...p} title={content.title}>{content.children}</Alert></div>}
      {impl === 'SegmentedControl' && <SegmentedControl {...p} data={['Preview', 'Code', 'Export']} />}
      {impl === 'Rating' && <Rating defaultValue={3} {...p} />}
      {impl === 'Tabs' && (
        <Tabs defaultValue="gallery" {...p} style={{ width: 420 }}>
          <Tabs.List><Tabs.Tab value="gallery">Gallery</Tabs.Tab><Tabs.Tab value="messages">Messages</Tabs.Tab><Tabs.Tab value="settings">Settings</Tabs.Tab></Tabs.List>
          <Tabs.Panel value="gallery" pt="sm">Gallery tab content</Tabs.Panel>
          <Tabs.Panel value="messages" pt="sm">Messages tab content</Tabs.Panel>
          <Tabs.Panel value="settings" pt="sm">Settings tab content</Tabs.Panel>
        </Tabs>
      )}
      {impl === 'Modal' && <MantineModal p={p} content={content} />}
    </MantineProvider>
  )
}

function MantineModal({ p, content }: { p: Record<string, never>; content: Record<string, string> }) {
  const [opened, setOpened] = useState(false)
  return (
    <>
      <Button onClick={() => setOpened(true)}>Open modal</Button>
      <Modal {...p} opened={opened} onClose={() => setOpened(false)} title={content.title}>{content.children}</Modal>
    </>
  )
}
