'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Search } from 'lucide-react'
import { useIntake, useIntakeCheck } from '@/features/quality/api'
import { ApiError } from '@/lib/api/client'
import { Button, EmptyState, ErrorState, Field, PageHeader, Panel, Select, Tag } from '@/components/ui'
import { RESOURCE_LABEL } from '@/components/platform/ResourceLinks'
import type { ResourceType } from '@/lib/api/types'
import s from '@/components/platform/page.module.scss'

const TYPES: ResourceType[] = ['official_website', 'official_documentation', 'github_repository', 'figma_file', 'storybook', 'additional_resource']
const MATCH: Record<string, string> = {
  same_url: 'Same URL', same_site: 'Same documentation site', same_host: 'Same host', same_repository_owner: 'Same repository owner', same_name: 'Same name',
}

export default function AddSourcePage() {
  const check = useIntakeCheck()
  const intake = useIntake()
  const [url, setUrl] = useState('')
  const [name, setName] = useState('')
  const [type, setType] = useState<ResourceType>('official_website')
  const [target, setTarget] = useState<number | 'new' | null>(null)
  const [newName, setNewName] = useState('')
  const [org, setOrg] = useState('')
  const [separate, setSeparate] = useState<number[]>([])
  const [verified, setVerified] = useState(false)
  const [crawl, setCrawl] = useState(true)
  const c = check.data
  const crawlable = type === 'official_website' || type === 'official_documentation'

  const runCheck = (e: React.FormEvent) => {
    e.preventDefault()
    intake.reset()
    check.mutate({ url, name: name || undefined }, {
      onSuccess: (r) => {
        setType(r.suggested_type)
        setTarget(r.candidates[0]?.system_id ?? 'new')
        setNewName(name)
        setSeparate([])
      },
    })
  }
  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (target === null) return
    intake.mutate({
      url, resource_type: type, verified, crawl: crawl && crawlable, separate_from: target === 'new' ? separate : [],
      ...(target === 'new' ? { new_system: { name: newName, organization: org || null } } : { system_id: target }),
    })
  }
  const conflict = intake.error instanceof ApiError && intake.error.status === 409 ? intake.error : null

  return (
    <>
      <PageHeader title="Add source" description="Add an official website, documentation, GitHub, Figma or other URL. Existing canonical systems are checked first, so a new crawl never creates a duplicate entry." />
      <Panel title="1 · URL">
        <form className={s.pad} style={{ display: 'grid', gap: 12, maxWidth: 720 }} onSubmit={runCheck}>
          <Field label="URL" hint="Official website or documentation URLs are crawled; other link types are attached to a system."><input type="url" required placeholder="https://design.example.com" value={url} onChange={(e) => setUrl(e.target.value)} /></Field>
          <Field label="System name (optional)" hint="Improves the duplicate check"><input value={name} onChange={(e) => setName(e.target.value)} maxLength={300} /></Field>
          {check.error && <ErrorState error={check.error} />}
          <span><Button type="submit" variant="primary" icon={<Search size={14} />} loading={check.isPending}>Check for existing systems</Button></span>
        </form>
      </Panel>

      {c && (
        <Panel title="2 · Attach or create" className={s.mt}>
          <form className={s.pad} style={{ display: 'grid', gap: 14, maxWidth: 820 }} onSubmit={submit}>
            <p className={s.muted} style={{ fontSize: '0.84rem' }}>Normalized URL: <span className={s.mono}>{c.canonical_url}</span></p>
            <Select label="Resource type" value={type} onChange={(v) => setType(v as ResourceType)} options={TYPES.map((t) => ({ value: t, label: RESOURCE_LABEL[t] }))} />
            {c.candidates.length === 0 ? (
              <EmptyState title="No likely existing system found">You can create a new canonical system for this URL.</EmptyState>
            ) : (
              <fieldset style={{ display: 'grid', gap: 8, border: 0, padding: 0 }}>
                <legend style={{ marginBottom: 6 }}>Likely existing systems — attach the URL to one of them:</legend>
                {c.candidates.map((cand) => (
                  <label key={cand.system_id} className={s.row} style={{ alignItems: 'flex-start' }}>
                    <input type="radio" name="target" checked={target === cand.system_id} onChange={() => setTarget(cand.system_id)} />
                    <span style={{ display: 'grid', gap: 2 }}>
                      <span className={s.row}><Link href={`/platform/systems/${cand.system_id}`} target="_blank"><strong>{cand.name}</strong></Link>
                        {cand.organization && <span className={s.muted}>{cand.organization}</span>}<Tag tone="accent">{MATCH[cand.match] ?? cand.match}</Tag></span>
                      <small className={s.muted}>{cand.detail}</small>
                    </span>
                  </label>
                ))}
              </fieldset>
            )}
            <label className={s.row}>
              <input type="radio" name="target" checked={target === 'new'} onChange={() => setTarget('new')} />
              <strong>Create a separate design system</strong>
            </label>
            {target === 'new' && (
              <div style={{ display: 'grid', gap: 10, paddingLeft: 24 }}>
                <Field label="Official name"><input required value={newName} onChange={(e) => setNewName(e.target.value)} maxLength={300} /></Field>
                <Field label="Organization"><input value={org} onChange={(e) => setOrg(e.target.value)} maxLength={300} /></Field>
                {c.candidates.length > 0 && (
                  <fieldset style={{ display: 'grid', gap: 6, border: 0, padding: 0 }}>
                    <legend>Confirm it is different from:</legend>
                    {c.candidates.map((cand) => (
                      <label key={cand.system_id} className={s.row}>
                        <input type="checkbox" checked={separate.includes(cand.system_id)}
                          onChange={(e) => setSeparate(e.target.checked ? [...separate, cand.system_id] : separate.filter((x) => x !== cand.system_id))} />
                        {cand.name} {cand.organization && <span className={s.muted}>({cand.organization})</span>}
                      </label>
                    ))}
                  </fieldset>
                )}
              </div>
            )}
            <label className={s.row} style={{ fontSize: '0.86rem' }}>
              <input type="checkbox" checked={verified} onChange={(e) => setVerified(e.target.checked)} /> I confirmed this URL is published by the system&apos;s organization
            </label>
            {crawlable && (
              <label className={s.row} style={{ fontSize: '0.86rem' }}>
                <input type="checkbox" checked={crawl} onChange={(e) => setCrawl(e.target.checked)} /> Crawl it now (official-docs crawl → rebuild → link verification)
              </label>
            )}
            {conflict ? (
              <div className={s.notice} role="alert">
                <span>{conflict.message}{conflict.details.length ? <> — {conflict.details.map((x) => String((x as Record<string, unknown>).name ?? '')).filter(Boolean).join(', ')}</> : null}</span>
              </div>
            ) : intake.error ? <ErrorState error={intake.error} /> : null}
            <span><Button type="submit" variant="primary" loading={intake.isPending} disabled={target === null || (target === 'new' && !newName.trim())}>Save to the knowledge base</Button></span>
          </form>
        </Panel>
      )}

      {intake.data && (
        <Panel title="3 · Saved" className={s.mt}>
          <div className={s.pad} style={{ display: 'grid', gap: 8 }} role="status">
            <p>Saved {RESOURCE_LABEL[intake.data.resource?.resource_type ?? type].toLowerCase()} for <span className={s.mono}>{intake.data.system_key}</span>.</p>
            {intake.data.system_id ? <Link href={`/platform/systems/${intake.data.system_id}`}>Open the system →</Link>
              : <p className={s.muted}>The new system appears in the catalog when the queued build finishes.</p>}
            {intake.data.job_ids.length > 0 && (
              <p>Queued: {intake.data.job_ids.map((j, i) => <Link key={j} href={`/platform/jobs/${j}`} style={{ marginRight: 10 }}>{['crawl', 'rebuild', 'verify links'][i] ?? 'job'} →</Link>)}</p>
            )}
          </div>
        </Panel>
      )}
    </>
  )
}
