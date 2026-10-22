'use client'

import { Suspense, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { ExternalLink, Layers, Play, Search } from 'lucide-react'
import { isAdmin, useMe } from '@/features/auth/api'
import { useCrawlStorybook, useStorybookProjects, useStorybookStories, useStorybookVariants } from '@/features/storybook/api'
import {
  Button,
  Drawer,
  ExtLink,
  Field,
  fmtDate,
  KV,
  Missing,
  PageHeader,
  Pagination,
  Panel,
  SearchInput,
  Select,
  Skeleton,
  Tabs,
  Tag,
} from '@/components/ui'
import { ErrorNotice } from '@/components/kit/states'
import { DataTable } from '@/components/ui/DataTable'
import type { StorybookProject, StorybookStory, StorybookVariant } from '@/lib/api/types'
import s from '@/components/platform/page.module.scss'

type Tab = 'projects' | 'stories' | 'variants'

function StorybookInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const initialTab = (searchParams.get('tab') as Tab) || 'projects'
  const [tab, setTab] = useState<Tab>(initialTab)

  return (
    <>
      <PageHeader
        title="Storybook & component variants"
        description="Public Storybook showcase projects, Component Story Format (CSF) story indexes, and extracted component variants with props and arg_types."
      />

      <div style={{ marginBottom: 14 }}>
        <Tabs<Tab>
          value={tab}
          onChange={(t) => {
            setTab(t)
            router.push(`/storybook?tab=${t}`, { scroll: false })
          }}
          tabs={[
            { value: 'projects', label: 'Showcase projects' },
            { value: 'stories', label: 'Stories & CSF indexes' },
            { value: 'variants', label: 'Component variants' },
          ]}
        />
      </div>

      {tab === 'projects' && <ProjectsView />}
      {tab === 'stories' && <StoriesView />}
      {tab === 'variants' && <VariantsView />}
    </>
  )
}

function ProjectsView() {
  const { data: me } = useMe()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState<string>('')
  const [sort, setSort] = useState<string>('title')
  const [page, setPage] = useState(1)
  const crawl = useCrawlStorybook()

  const queryParams = useMemo(
    () => ({
      q: q || undefined,
      status: status || undefined,
      sort,
      page,
      page_size: 25,
    }),
    [q, status, sort, page],
  )

  const projects = useStorybookProjects(queryParams)
  const [selected, setSelected] = useState<StorybookProject | null>(null)

  return (
    <div className={s.stack}>
      <Panel
        title="Showcase projects"
        actions={
          isAdmin(me) && (
            <Button
              icon={<Play size={14} />}
              loading={crawl.isPending}
              onClick={() => crawl.mutate(false)}
            >
              Crawl storybooks
            </Button>
          )
        }
      >
        <div className={s.filters}>
          <SearchInput
            value={q}
            onChange={(val) => {
              setQ(val)
              setPage(1)
            }}
            placeholder="Search projects by title, org or slug…"
          />
          <Select
            label="Sort by"
            value={sort}
            onChange={(v) => {
              setSort(v)
              setPage(1)
            }}
            options={[
              { value: 'title', label: 'Title (A-Z)' },
              { value: '-stories', label: 'Most stories' },
              { value: '-variants', label: 'Most variants' },
            ]}
          />
        </div>

        {projects.error ? (
          <ErrorNotice title="Storybook data could not be loaded" onRetry={() => projects.refetch()} />
        ) : (
          <>
            <DataTable
              caption="Storybook showcase projects"
              loading={projects.isFetching}
              rows={projects.data?.data}
              rowKey={(r) => r.id}
              onRowClick={(r) => setSelected(r)}
              columns={[
                {
                  key: 't',
                  header: 'Project',
                  cell: (r) => (
                    <span className={s.cell}>
                      <strong>{r.title}</strong>
                      <small>{r.organization || r.slug}</small>
                    </span>
                  ),
                },
                {
                  key: 'fw',
                  header: 'Tech & Version',
                  cell: (r) => (
                    <span className={s.cell}>
                      <span>{r.framework || 'unknown framework'}</span>
                      <small className={s.muted}>
                        {r.storybook_version ? `v${r.storybook_version}` : 'unversioned'}
                      </small>
                    </span>
                  ),
                  hideBelow: 'md',
                },
                {
                  key: 's',
                  header: 'Stories',
                  cell: (r) => r.stories_extracted.toLocaleString(),
                  align: 'right',
                },
                {
                  key: 'v',
                  header: 'Variants',
                  cell: (r) => r.variants_extracted.toLocaleString(),
                  align: 'right',
                },
                {
                  key: 'link',
                  header: 'Storybook',
                  cell: (r) =>
                    r.resolved_url || r.storybook_url ? (
                      <ExtLink href={(r.resolved_url || r.storybook_url)!}>Open</ExtLink>
                    ) : (
                      <Missing label="—" />
                    ),
                  hideBelow: 'md',
                },
              ]}
            />
            {projects.data && (
              <Pagination
                page={page}
                pageSize={25}
                total={projects.data.meta.total_items}
                totalPages={projects.data.meta.total_pages}
                onPage={setPage}
              />
            )}
          </>
        )}
      </Panel>

      {selected && (
        <Drawer
          title={selected.title}
          open={!!selected}
          onClose={() => setSelected(null)}
        >
          <div className={s.pad} style={{ display: 'grid', gap: 14 }}>
            <p className={s.muted} style={{ fontSize: '0.84rem' }}>Project slug: {selected.slug}</p>
            <KV
              items={[
                ['Framework', selected.framework],
                ['Storybook version', selected.storybook_version],
                ['Index kind', selected.index_kind],
                ['Stories discovered', selected.stories_discovered.toLocaleString()],
                ['Stories extracted', selected.stories_extracted.toLocaleString()],
                ['Documentation entries', selected.docs_entries.toLocaleString()],
                ['Variants extracted', selected.variants_extracted.toLocaleString()],
                ['Source files parsed', selected.source_files_parsed.toLocaleString()],
                [
                  'Storybook URL',
                  selected.resolved_url || selected.storybook_url ? (
                    <ExtLink href={(selected.resolved_url || selected.storybook_url)!} />
                  ) : null,
                ],
                [
                  'Repository',
                  selected.repository_url ? <ExtLink href={selected.repository_url} /> : null,
                ],
              ]}
            />
          </div>
        </Drawer>
      )}
    </div>
  )
}

function StoriesView() {
  const [q, setQ] = useState('')
  const [entryType, setEntryType] = useState<string>('')
  const [resolution, setResolution] = useState<string>('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<StorybookStory | null>(null)

  const queryParams = useMemo(
    () => ({
      q: q || undefined,
      entry_type: entryType || undefined,
      resolution: resolution || undefined,
      page,
      page_size: 25,
    }),
    [q, entryType, resolution, page],
  )

  const stories = useStorybookStories(queryParams)

  return (
    <div className={s.stack}>
      <Panel title="Stories & index entries">
        <div className={s.filters}>
          <SearchInput
            value={q}
            onChange={(val) => {
              setQ(val)
              setPage(1)
            }}
            placeholder="Search stories by component name or title…"
          />
          <Select
            label="Entry type"
            value={entryType}
            onChange={(v) => {
              setEntryType(v)
              setPage(1)
            }}
            options={[
              { value: '', label: 'All entry types' },
              { value: 'story', label: 'Story' },
              { value: 'docs', label: 'Docs' },
              { value: 'autodocs', label: 'Autodocs' },
            ]}
          />
        </div>

        {stories.error ? (
          <ErrorNotice title="Storybook data could not be loaded" onRetry={() => stories.refetch()} />
        ) : (
          <>
            <DataTable
              caption="Storybook stories"
              loading={stories.isFetching}
              rows={stories.data?.data}
              rowKey={(r) => r.id}
              onRowClick={(r) => setSelected(r)}
              columns={[
                {
                  key: 't',
                  header: 'Title & Name',
                  cell: (r) => (
                    <span className={s.cell}>
                      <strong>{r.title}</strong>
                      <small>{r.name}</small>
                    </span>
                  ),
                },
                {
                  key: 'comp',
                  header: 'Component',
                  cell: (r) =>
                    r.component_id ? (
                      <Link href={`/components/${r.component_id}`}>
                        {r.component_name || `Component #${r.component_id}`}
                      </Link>
                    ) : (
                      <span>{r.component_name || '—'}</span>
                    ),
                },
                {
                  key: 'type',
                  header: 'Type',
                  cell: (r) => <Tag>{r.entry_type}</Tag>,
                  hideBelow: 'md',
                },
                {
                  key: 'url',
                  header: 'Storybook link',
                  cell: (r) => <ExtLink href={r.story_url}>Open</ExtLink>,
                  hideBelow: 'md',
                },
              ]}
            />
            {stories.data && (
              <Pagination
                page={page}
                pageSize={25}
                total={stories.data.meta.total_items}
                totalPages={stories.data.meta.total_pages}
                onPage={setPage}
              />
            )}
          </>
        )}
      </Panel>

      {selected && (
        <Drawer
          title={selected.name}
          open={!!selected}
          onClose={() => setSelected(null)}
        >
          <div className={s.pad} style={{ display: 'grid', gap: 14 }}>
            <p className={s.muted} style={{ fontSize: '0.84rem' }}>Story title: {selected.title}</p>
            <KV
              items={[
                ['Entry ID', <span key="id" className={s.mono}>{selected.entry_id}</span>],
                ['Entry type', <Tag key="et">{selected.entry_type}</Tag>],
                ['Export name', selected.export_name],
                [
                  'Component',
                  selected.component_id ? (
                    <Link href={`/components/${selected.component_id}`}>
                      {selected.component_name || `Component #${selected.component_id}`}
                    </Link>
                  ) : (
                    selected.component_name
                  ),
                ],
                ['Import path', selected.import_path],
                ['Story URL', <ExtLink key="url" href={selected.story_url} />],
                [
                  'Tags',
                  selected.tags.length ? (
                    <span key="tags" className={s.row}>
                      {selected.tags.map((t) => (
                        <Tag key={t}>{t}</Tag>
                      ))}
                    </span>
                  ) : null,
                ],
              ]}
            />

            {selected.args && (
              <Panel title="Story arguments (args)">
                <pre className={s.code} style={{ margin: 12 }}>
                  {JSON.stringify(selected.args, null, 2)}
                </pre>
              </Panel>
            )}

            {selected.arg_types && (
              <Panel title="Controls & ArgTypes">
                <pre className={s.code} style={{ margin: 12 }}>
                  {JSON.stringify(selected.arg_types, null, 2)}
                </pre>
              </Panel>
            )}
          </div>
        </Drawer>
      )}
    </div>
  )
}

function VariantsView() {
  const [q, setQ] = useState('')
  const [method, setMethod] = useState<string>('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<StorybookVariant | null>(null)

  const queryParams = useMemo(
    () => ({
      q: q || undefined,
      method: method || undefined,
      page,
      page_size: 25,
    }),
    [q, method, page],
  )

  const variants = useStorybookVariants(queryParams)

  return (
    <div className={s.stack}>
      <Panel title="Component variants">
        <div className={s.filters}>
          <SearchInput
            value={q}
            onChange={(val) => {
              setQ(val)
              setPage(1)
            }}
            placeholder="Search variants by label or component…"
          />
        </div>

        {variants.error ? (
          <ErrorNotice title="Storybook data could not be loaded" onRetry={() => variants.refetch()} />
        ) : (
          <>
            <DataTable
              caption="Component variants"
              loading={variants.isFetching}
              rows={variants.data?.data}
              rowKey={(r) => r.id}
              onRowClick={(r) => setSelected(r)}
              columns={[
                {
                  key: 'l',
                  header: 'Variant Label',
                  cell: (r) => <strong>{r.label}</strong>,
                },
                {
                  key: 'comp',
                  header: 'Component',
                  cell: (r) =>
                    r.component_id ? (
                      <Link href={`/components/${r.component_id}`}>
                        {r.component_name || `Component #${r.component_id}`}
                      </Link>
                    ) : (
                      <span>{r.component_name || '—'}</span>
                    ),
                },
                {
                  key: 'props',
                  header: 'Props Preview',
                  cell: (r) => (
                    <span className={s.mono} style={{ fontSize: '0.78rem' }}>
                      {Object.keys(r.props || {}).length > 0
                        ? Object.entries(r.props)
                            .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                            .join(' · ')
                        : '—'}
                    </span>
                  ),
                },
              ]}
            />
            {variants.data && (
              <Pagination
                page={page}
                pageSize={25}
                total={variants.data.meta.total_items}
                totalPages={variants.data.meta.total_pages}
                onPage={setPage}
              />
            )}
          </>
        )}
      </Panel>

      {selected && (
        <Drawer
          title={selected.label}
          open={!!selected}
          onClose={() => setSelected(null)}
        >
          <div className={s.pad} style={{ display: 'grid', gap: 14 }}>
            <p className={s.muted} style={{ fontSize: '0.84rem' }}>Component: {selected.component_name || 'unlinked'}</p>
            <KV
              items={[
                ['Label', selected.label],
                [
                  'Component',
                  selected.component_id ? (
                    <Link href={`/components/${selected.component_id}`}>
                      {selected.component_name || `Component #${selected.component_id}`}
                    </Link>
                  ) : (
                    selected.component_name
                  ),
                ],
              ]}
            />
            <Panel title="Variant properties (JSON)">
              <pre className={s.code} style={{ margin: 12 }}>
                {JSON.stringify(selected.props, null, 2)}
              </pre>
            </Panel>
          </div>
        </Drawer>
      )}
    </div>
  )
}


export default function StorybookPage() {
  return <Suspense><StorybookInner /></Suspense>
}
