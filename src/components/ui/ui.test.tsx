import { describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { ApiError } from '@/lib/api/client'
import { ErrorState, JobBadge, KV, Pagination, SearchInput, VerifyBadge } from './index'
import { DataTable } from './DataTable'

describe('status badges', () => {
  it('labels verification and job states distinctly', () => {
    render(<><VerifyBadge status="partially_verified" /><JobBadge status="partially_succeeded" /><JobBadge status="failed" /></>)
    expect(screen.getByText('Partially verified')).toHaveAttribute('title', expect.stringContaining('≥2 independent sources'))
    expect(screen.getByText('Partial')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
  })
})

describe('KV', () => {
  it('renders missing values as “Not documented” rather than blanks', () => {
    render(<KV items={[['Repository', null], ['Docs', 'x']]} />)
    expect(screen.getByText('Not documented')).toBeInTheDocument()
  })
})

describe('ErrorState', () => {
  it('shows message, request id and retry', () => {
    const onRetry = vi.fn()
    render(<ErrorState error={new ApiError(500, { code: 'X', message: 'Boom', details: [], request_id: 'req_9' }, '')} onRetry={onRetry} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Boom')
    expect(screen.getByText(/req_9/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalled()
  })
})

describe('Pagination', () => {
  it('reports range and pages, disables at bounds', () => {
    const onPage = vi.fn()
    render(<Pagination page={1} pageSize={25} total={60} totalPages={3} onPage={onPage} />)
    expect(screen.getByText(/1–25 of/)).toBeInTheDocument()
    expect(screen.getByLabelText('Previous page')).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Next page'))
    expect(onPage).toHaveBeenCalledWith(2)
  })
})

describe('SearchInput', () => {
  it('debounces changes', () => {
    vi.useFakeTimers()
    const onChange = vi.fn()
    render(<SearchInput value="" onChange={onChange} delay={300} />)
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'dia' } })
    expect(onChange).not.toHaveBeenCalled()
    act(() => vi.advanceTimersByTime(310))
    expect(onChange).toHaveBeenCalledWith('dia')
    vi.useRealTimers()
  })
})

describe('DataTable', () => {
  const cols = [{ key: 'n', header: 'Name', cell: (r: { id: number; n: string }) => r.n }]
  it('renders rows and activates rows with Enter', () => {
    const onRowClick = vi.fn()
    render(<DataTable columns={cols} rows={[{ id: 1, n: 'Dialog' }]} rowKey={(r) => r.id} onRowClick={onRowClick} />)
    const row = screen.getByText('Dialog').closest('tr')!
    fireEvent.keyDown(row, { key: 'Enter' })
    expect(onRowClick).toHaveBeenCalledWith({ id: 1, n: 'Dialog' })
  })
  it('shows loading skeleton and empty state', () => {
    const { rerender } = render(<DataTable columns={cols} rows={undefined} loading rowKey={(r) => r.id} />)
    expect(screen.getByRole('status', { name: 'Loading' })).toBeInTheDocument()
    rerender(<DataTable columns={cols} rows={[]} rowKey={(r) => r.id} />)
    expect(screen.getByText('No results')).toBeInTheDocument()
  })
})
