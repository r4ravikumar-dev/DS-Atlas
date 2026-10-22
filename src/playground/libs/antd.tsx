'use client'

import { useState } from 'react'
import { Alert, Avatar, Button, Checkbox, ConfigProvider, Modal, Progress, Rate, Segmented, Slider, Spin, Switch, Tabs, Tag, theme as antTheme } from 'antd'
import type { RenderProps } from './types'

/** Ant Design 6.6.7 — the real components with antd's default or dark algorithm. */
export default function AntdRenderer({ impl, props, content, theme }: RenderProps) {
  const p = props as Record<string, never>
  return (
    <ConfigProvider theme={{ algorithm: theme === 'dark' ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm }}>
      <div style={{ padding: 4, color: theme === 'dark' ? '#fff' : undefined }}>
        {impl === 'Button' && <Button {...p}>{content.children}</Button>}
        {impl === 'Tag' && <Tag {...p}>{content.children}</Tag>}
        {impl === 'Switch' && <Switch {...p} />}
        {impl === 'Checkbox' && <Checkbox {...p}>{content.children}</Checkbox>}
        {impl === 'Slider' && <div style={{ width: 320 }}><Slider defaultValue={40} {...p} /></div>}
        {impl === 'Progress' && <div style={{ width: 320 }}><Progress {...p} /></div>}
        {impl === 'Alert' && <div style={{ width: 420 }}><Alert {...p} title={content.title} description={content.description} /></div>}
        {impl === 'Rate' && <Rate defaultValue={3} {...p} />}
        {impl === 'Segmented' && <Segmented {...p} options={['Daily', 'Weekly', 'Monthly']} />}
        {impl === 'Spin' && <Spin {...p} />}
        {impl === 'Avatar' && <Avatar {...p}>{content.children}</Avatar>}
        {impl === 'Tabs' && <div style={{ width: 420 }}><Tabs {...p} items={[1, 2, 3].map((i) => ({ key: String(i), label: `Tab ${i}`, children: `Content of tab ${i}` }))} /></div>}
        {impl === 'Modal' && <AntdModal p={p} content={content} />}
      </div>
    </ConfigProvider>
  )
}

function AntdModal({ p, content }: { p: Record<string, never>; content: Record<string, string> }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <Button type="primary" onClick={() => setOpen(true)}>Open modal</Button>
      <Modal {...p} open={open} title={content.title} onOk={() => setOpen(false)} onCancel={() => setOpen(false)}>{content.children}</Modal>
    </>
  )
}
