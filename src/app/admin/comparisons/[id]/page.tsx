'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { RefreshCw, Trash2 } from 'lucide-react'
import { isAdmin, useMe } from '@/features/auth/api'
import { useComparison, useDeleteComparison, useRegenerate } from '@/features/comparisons/api'
import { Button, ConfirmDialog, ErrorState, fmtDate, PageHeader, Skeleton } from '@/components/ui'
import s from '@/components/platform/page.module.scss'
import { ComparisonMatrix, type ComparisonResult } from '@/components/comparison/ComparisonMatrix'


export default function ComparisonPage() {
  const id = useParams<{ id: string }>().id
  const router = useRouter()
  const { data: me } = useMe()
  const c = useComparison(id)
  const regen = useRegenerate(id)
  const del = useDeleteComparison()
  const [confirm, setConfirm] = useState(false)
  if (c.error) return <ErrorState error={c.error} onRetry={() => c.refetch()} />
  const d = c.data
  const r = d?.result as unknown as ComparisonResult | undefined
  const base = d?.kind === 'systems' ? '/systems' : '/components'
  return (
    <>
      <PageHeader crumbs={[{ href: '/compare', label: 'Compare' }]} title={d ? d.name : <Skeleton w={300} h={30} />}
        description={d && `${d.kind} · generated ${fmtDate(d.generated_at)} from current records`}
        actions={d && isAdmin(me) && (<>
          <Button icon={<RefreshCw size={14} />} loading={regen.isPending} onClick={() => regen.mutate()}>Regenerate</Button>
          <Button variant="ghost" icon={<Trash2 size={14} />} onClick={() => setConfirm(true)}>Delete</Button>
        </>)} />
      {r && (
        <>
          <ComparisonMatrix result={r} base={base} />
        </>
      )}
      <ConfirmDialog open={confirm} danger title="Delete this comparison?" body="The saved configuration and generated result will be removed. Source records are not affected." confirmLabel="Delete" loading={del.isPending}
        onCancel={() => setConfirm(false)} onConfirm={() => del.mutate(id, { onSuccess: () => router.push('/compare') })} />
    </>
  )
}
