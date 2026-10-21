'use client'

import { ArrowDown, ArrowUp } from 'lucide-react'
import { EmptyState, SkeletonRows } from './index'
import s from './DataTable.module.scss'

export interface Column<T> {
  key: string
  header: React.ReactNode
  cell: (row: T) => React.ReactNode
  sortKey?: string
  width?: string
  align?: 'left' | 'right'
  hideBelow?: 'md' | 'lg'
}

interface Props<T> {
  columns: Column<T>[]
  rows: T[] | undefined
  rowKey: (row: T) => string | number
  loading?: boolean
  onRowClick?: (row: T) => void
  sort?: string
  onSort?: (key: string) => void
  empty?: React.ReactNode
  caption?: string
}

/** Accessible, keyboard-operable table. Rows with onRowClick are focusable and activate on Enter. */
export function DataTable<T>({ columns, rows, rowKey, loading, onRowClick, sort, onSort, empty, caption }: Props<T>) {
  if (loading && !rows) return <SkeletonRows cols={Math.min(columns.length, 5)} />
  if (rows && rows.length === 0) return <>{empty ?? <EmptyState title="No results" />}</>
  const active = sort?.replace(/^-/, '')
  const desc = sort?.startsWith('-')
  return (
    <div className={s.wrap} data-loading={loading || undefined}>
      <table className={s.table}>
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} style={{ width: c.width, textAlign: c.align }} data-hide={c.hideBelow}
                  aria-sort={c.sortKey && active === c.sortKey ? (desc ? 'descending' : 'ascending') : undefined}>
                {c.sortKey && onSort ? (
                  <button type="button" onClick={() => onSort(active === c.sortKey && !desc ? `-${c.sortKey}` : c.sortKey!)}>
                    {c.header}
                    {active === c.sortKey && (desc ? <ArrowDown size={12} /> : <ArrowUp size={12} />)}
                  </button>
                ) : (
                  c.header
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows?.map((r) => (
            <tr key={rowKey(r)} onClick={onRowClick ? () => onRowClick(r) : undefined} tabIndex={onRowClick ? 0 : undefined}
                onKeyDown={onRowClick ? (e) => e.key === 'Enter' && onRowClick(r) : undefined} data-clickable={onRowClick ? true : undefined}>
              {columns.map((c) => (
                <td key={c.key} style={{ textAlign: c.align }} data-hide={c.hideBelow}>
                  {c.cell(r)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
