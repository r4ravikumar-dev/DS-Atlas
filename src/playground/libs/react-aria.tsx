'use client'

import './headless.css'
import { Button, Checkbox, Disclosure, DisclosurePanel, Heading, Input, Label, Meter, ProgressBar, Slider, SliderOutput, SliderThumb, SliderTrack, Switch, Tab, TabList, TabPanel, Tabs, TextField, ToggleButton } from 'react-aria-components'
import type { RenderProps } from './types'

/** React Aria Components 1.22.1 — real components (behaviour, focus and ARIA from the library); neutral platform styles only. */
export default function ReactAriaRenderer({ impl, props, content, theme }: RenderProps) {
  const p = props as Record<string, never>
  return (
    <div className="pg-headless" data-theme={theme}>
      {impl === 'Button' && <Button {...p}>{content.children}</Button>}
      {impl === 'ToggleButton' && <ToggleButton {...p}>{content.children}</ToggleButton>}
      {impl === 'Switch' && <Switch {...p} className="pg-row"><span className="pg-switch-track"><span className="pg-switch-thumb" /></span>{content.children}</Switch>}
      {impl === 'Checkbox' && (
        <Checkbox {...p} className="pg-row">
          {({ isSelected, isIndeterminate }) => <><span className="pg-box" aria-hidden>{isIndeterminate ? '–' : isSelected ? '✓' : ''}</span>{content.children}</>}
        </Checkbox>
      )}
      {impl === 'Slider' && (
        <Slider defaultValue={40} {...p} className="pg-field">
          <span className="pg-row" style={{ justifyContent: 'space-between' }}><Label>{content.label}</Label><SliderOutput /></span>
          <SliderTrack className="pg-track" style={{ height: 20, background: 'none' }}>
            {({ state }) => <>
              <span className="pg-track" style={{ position: 'absolute', top: 8 }}><span className="pg-fill" style={{ width: `${state.getThumbPercent(0) * 100}%` }} /></span>
              <SliderThumb className="pg-thumb" style={{ top: 10 }} />
            </>}
          </SliderTrack>
        </Slider>
      )}
      {impl === 'ProgressBar' && (
        <ProgressBar {...p} className="pg-field">
          {({ percentage, valueText }) => <><span className="pg-row" style={{ justifyContent: 'space-between' }}><Label>{content.label}</Label><span>{valueText}</span></span>
            <span className="pg-track"><span className="pg-fill" style={{ width: `${percentage ?? 30}%` }} /></span></>}
        </ProgressBar>
      )}
      {impl === 'Meter' && (
        <Meter {...p} className="pg-field">
          {({ percentage, valueText }) => <><span className="pg-row" style={{ justifyContent: 'space-between' }}><Label>{content.label}</Label><span>{valueText}</span></span>
            <span className="pg-track"><span className="pg-fill" style={{ width: `${percentage}%` }} /></span></>}
        </Meter>
      )}
      {impl === 'TextField' && <TextField {...p} className="pg-field"><Label>{content.label}</Label><Input placeholder={content.placeholder} /></TextField>}
      {impl === 'Tabs' && (
        <Tabs {...p} style={{ width: 360 }}>
          <TabList aria-label="Example tabs" className="pg-tabs-list"><Tab id="a">Founding</Tab><Tab id="b">Monarchy</Tab><Tab id="c">Empire</Tab></TabList>
          <TabPanel id="a" className="pg-panel">Founding content</TabPanel><TabPanel id="b" className="pg-panel">Monarchy content</TabPanel><TabPanel id="c" className="pg-panel">Empire content</TabPanel>
        </Tabs>
      )}
      {impl === 'Disclosure' && (
        <Disclosure {...p} style={{ width: 360 }}>
          <Heading><Button slot="trigger">{content.title}</Button></Heading>
          <DisclosurePanel className="pg-panel">{content.children}</DisclosurePanel>
        </Disclosure>
      )}
    </div>
  )
}
