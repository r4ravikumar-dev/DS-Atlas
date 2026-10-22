'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { api } from '@/lib/api/client'
import { Button, EmptyState, ErrorState, ExtLink, fmtDate, Panel, Tag } from '@/components/ui'
import { DataTable } from '@/components/ui/DataTable'
import s from '@/components/platform/page.module.scss'

interface Asset {
  id: number; kind: string; url: string; page_url: string | null; source_host: string | null; source_organization: string | null; alt: string | null; mime: string | null
  width: number | null; height: number | null; bytes: number | null; attribution: string | null; license: string | null; status: string; error: string | null; is_primary: boolean
  retrieved_at: string | null; checked_at: string | null
}

/** Administrator view of a system's visual assets: provenance, licence notes, retrieval failures and which one the public site uses. */
export function AssetsPanel({ systemId }: { systemId: number }) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['system', systemId, 'assets'], queryFn: ({ signal }) => api<{ data: Asset[] }>(`/design-systems/${systemId}/assets`, { signal }).then((r) => r.data) })
  const collect = useMutation({
    mutationFn: () => api(`/design-systems/${systemId}/assets/collect`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['system', systemId, 'assets'] }),
  })
  return (
    <Panel title="Visual assets" actions={<Button size="sm" icon={<RefreshCw size={13} />} loading={collect.isPending} onClick={() => collect.mutate()}>Re-collect</Button>}>
      {collect.isSuccess && <p className={`${s.pad} ${s.muted}`} role="status">Collection queued — see Crawl jobs.</p>}
      {q.error ? <ErrorState error={q.error} onRetry={() => q.refetch()} /> : q.data?.length === 0 ? (
        <EmptyState title="No assets recorded">Assets are read from the system&apos;s official page (site icon and social image).</EmptyState>
      ) : (
        <DataTable caption="Visual assets" loading={q.isLoading} rows={q.data} rowKey={(r) => r.id}
          columns={[
            { key: 'k', header: 'Kind', cell: (r) => <span className={s.cell}><strong>{r.kind.replace('_', ' ')}</strong><small>{r.is_primary ? 'shown publicly' : 'not used'}</small></span> },
            { key: 'st', header: 'Status', cell: (r) => <span className={s.cell}><Tag tone={r.status === 'ok' ? 'accent' : undefined}>{r.status}</Tag>{r.error && <small>{r.error}</small>}</span> },
            { key: 'u', header: 'Asset', cell: (r) => <span className={s.cell}><ExtLink href={r.url} /><small>{[r.mime, r.width && r.height ? `${r.width}×${r.height}` : null, r.bytes ? `${Math.round(r.bytes / 1024)} KB` : null].filter(Boolean).join(' · ')}</small></span> },
            { key: 'p', header: 'Found on', cell: (r) => (r.page_url ? <ExtLink href={r.page_url} /> : '—'), hideBelow: 'md' },
            { key: 'l', header: 'Licence / attribution', cell: (r) => <span className={s.cell}><span>{r.license ?? 'not stated by the source'}</span><small>{r.attribution}</small></span>, hideBelow: 'lg' },
            { key: 'c', header: 'Checked', cell: (r) => fmtDate(r.checked_at), hideBelow: 'lg' },
          ]} />
      )}
    </Panel>
  )
}
