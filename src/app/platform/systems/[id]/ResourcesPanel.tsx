'use client'

import { useState } from 'react'
import { Check, Plus, RefreshCw, ShieldAlert, Star, Trash2 } from 'lucide-react'
import { useAddResource, useDeleteResource, useUpdateResource, useVerifyResources } from '@/features/design-systems/api'
import { Button, ErrorState, ExtLink, Field, fmtAgo, Panel, Select, Tag, VerifyBadge } from '@/components/ui'
import { RESOURCE_LABEL } from '@/components/platform/ResourceLinks'
import type { ResourceOut, ResourceType, SystemDetail } from '@/lib/api/types'
import s from '@/components/platform/page.module.scss'

const ORDER: ResourceType[] = ['official_website', 'official_documentation', 'github_repository', 'figma_file', 'storybook', 'additional_resource']
const ORIGIN: Record<string, string> = {
  manual: 'added by administrator', official_site: 'found on official page', official_docs: 'official docs crawl', resolver: 'identity review',
  storybook_showcase: 'Storybook showcase', directory: 'directory listing',
}

export function ResourcesPanel({ system }: { system: SystemDetail }) {
  const res = system.resources
  const upd = useUpdateResource(system.id)
  const del = useDeleteResource(system.id)
  const verify = useVerifyResources()
  const [adding, setAdding] = useState(false)
  const officialChecked = res.some((r) => r.is_primary && (r.resource_type === 'official_website' || r.resource_type === 'official_documentation') && r.last_checked_at && r.http_status && r.http_status < 400)
  const byType = (t: ResourceType) => res.filter((r) => r.resource_type === t)

  return (
    <Panel
      title="Official resources"
      id="resources"
      actions={
        <span className={s.row}>
          <Button size="sm" variant="ghost" icon={<RefreshCw size={13} />} loading={verify.isPending} onClick={() => verify.mutate(system.id)}>
            Re-check official page
          </Button>
          <Button size="sm" icon={<Plus size={13} />} onClick={() => setAdding((a) => !a)}>Add link</Button>
        </span>
      }
    >
      {verify.isSuccess && <p className={s.pad} role="status">Verification queued — see <a href={`/platform/jobs/${verify.data.data.job_ids[0]}`}>job progress</a>.</p>}
      {adding && <AddResource systemId={system.id} onDone={() => setAdding(false)} />}
      <div className={s.resourceGroups}>
        {ORDER.map((t) => {
          const items = byType(t)
          if (items.length === 0) {
            if (t === 'additional_resource') return null
            return (
              <section key={t} className={s.resourceGroup} data-empty>
                <h4>{RESOURCE_LABEL[t]}</h4>
                <p className={s.muted}>
                  {t === 'figma_file'
                    ? officialChecked ? 'Figma resource not found on the official page.' : 'Figma resource not found (official page not checked yet).'
                    : 'Not found in any source.'}
                </p>
              </section>
            )
          }
          return (
            <section key={t} className={s.resourceGroup}>
              <h4>{RESOURCE_LABEL[t]} {items.length > 1 && <Tag tone="muted">{items.length}</Tag>}</h4>
              <ul>
                {items.map((r) => <ResourceRow key={r.id} r={r} busy={upd.isPending || del.isPending}
                  onUpdate={(body) => upd.mutate({ id: r.id, body })} onDelete={() => del.mutate(r.id)} />)}
              </ul>
            </section>
          )
        })}
      </div>
      {(upd.error || del.error) && <div className={s.pad}><ErrorState error={upd.error ?? del.error} /></div>}
    </Panel>
  )
}

function ResourceRow({ r, busy, onUpdate, onDelete }: { r: ResourceOut; busy: boolean; onUpdate: (b: { verification_status?: 'verified' | 'invalid' | 'unverified'; is_primary?: boolean }) => void; onDelete: () => void }) {
  return (
    <li className={s.resourceRow} data-primary={r.is_primary || undefined}>
      <div className={s.resourceMain}>
        <ExtLink href={r.url}>{r.label || undefined}</ExtLink>
        <span className={s.row}>
          <VerifyBadge status={r.verification_status} />
          {r.is_primary && <Tag tone="accent">primary</Tag>}
          <span className={s.muted} style={{ fontSize: '0.74rem' }}>
            {ORIGIN[r.origin] ?? r.origin}{r.source_keys.length > 0 && ` · ${r.source_keys.join(', ')}`}
            {r.last_checked_at && ` · checked ${fmtAgo(r.last_checked_at)}${r.http_status ? ` (HTTP ${r.http_status})` : ''}`}
          </span>
        </span>
        {(r.evidence_note || r.access_note) && (
          <small className={s.muted}>
            {r.evidence_note}{r.evidence_url && r.evidence_url !== r.url && <> — <ExtLink href={r.evidence_url}>evidence</ExtLink></>}
            {r.access_note && <> {r.access_note}</>}
          </small>
        )}
      </div>
      <span className={s.resourceActions}>
        {r.verification_status !== 'verified' && <Button size="sm" variant="ghost" icon={<Check size={13} />} disabled={busy} onClick={() => onUpdate({ verification_status: 'verified' })} title="Confirm this link belongs to the system">Confirm</Button>}
        {r.verification_status !== 'invalid' && <Button size="sm" variant="ghost" icon={<ShieldAlert size={13} />} disabled={busy} onClick={() => onUpdate({ verification_status: 'invalid' })} title="Flag as wrong or broken">Flag</Button>}
        {!r.is_primary && r.verification_status !== 'invalid' && <Button size="sm" variant="ghost" icon={<Star size={13} />} disabled={busy} onClick={() => onUpdate({ is_primary: true })} title="Show this link on the catalog card">Primary</Button>}
        {r.origin === 'manual' && <Button size="sm" variant="ghost" icon={<Trash2 size={13} />} disabled={busy} onClick={onDelete} title="Remove (administrator-added links only)">Remove</Button>}
      </span>
    </li>
  )
}

function AddResource({ systemId, onDone }: { systemId: number; onDone: () => void }) {
  const add = useAddResource(systemId)
  const [type, setType] = useState<ResourceType>('figma_file')
  const [url, setUrl] = useState('')
  const [verified, setVerified] = useState(false)
  return (
    <form className={s.pad} style={{ display: 'grid', gap: 10, borderBottom: '1px solid var(--line)' }}
      onSubmit={(e) => (e.preventDefault(), add.mutate({ resource_type: type, url, verification_status: verified ? 'verified' : 'unverified' }, { onSuccess: onDone }))}>
      <div className={s.row} style={{ alignItems: 'end' }}>
        <Select label="Type" value={type} onChange={(v) => setType(v as ResourceType)} options={ORDER.map((t) => ({ value: t, label: RESOURCE_LABEL[t] }))} />
        <Field label="URL"><input type="url" required placeholder="https://…" value={url} onChange={(e) => setUrl(e.target.value)} style={{ minWidth: 320 }} /></Field>
      </div>
      <label className={s.row} style={{ fontSize: '0.84rem' }}>
        <input type="checkbox" checked={verified} onChange={(e) => setVerified(e.target.checked)} /> I confirmed this link is published by the system&apos;s organization
      </label>
      {add.error && <ErrorState error={add.error} />}
      <span className={s.row}><Button type="submit" variant="primary" loading={add.isPending}>Save link</Button><Button type="button" variant="ghost" onClick={onDone}>Cancel</Button></span>
    </form>
  )
}
