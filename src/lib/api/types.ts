/** Re-exports of backend contract types generated from OpenAPI (`npm run api:types`). Do not hand-edit schema.d.ts. */
import type { components } from './schema'

type S = components['schemas']

export type ErrorBody = S['ErrorBody']
export type PageMeta = S['PageMeta']
export interface Page<T> {
  data: T[]
  meta: PageMeta
}
export interface Item<T> {
  data: T
}

export type User = S['UserOut']
export type Session = S['SessionOut']
export type Source = S['SourceOut']
export type SourceDetail = S['SourceDetail']
export type SourceCreate = S['SourceCreate']
export type SourceUpdate = S['SourceUpdate']
export type Coverage = S['CoverageOut']
export type DiscoveredUrl = S['DiscoveredUrlOut']
export type Job = S['JobOut']
export type JobEvent = S['JobEventOut']
export type JobStatus = Job['status']
export type JobAccepted = S['JobAccepted']
export type System = S['SystemOut']
export type SystemDetail = S['SystemDetail']
export type Component = S['ComponentOut']
export type ComponentDetail = S['ComponentDetail']
export type Prop = S['PropOut']
export type Token = S['TokenOut']
export type Guideline = S['GuidelineOut']
export type GuidelineDetail = S['GuidelineDetail']
export type Evidence = S['EvidenceOut']
export type SearchHit = S['SearchHit']
export type DashboardSummary = S['DashboardSummary']
export type Comparison = S['ComparisonOut']
export type ComparisonCreate = S['ComparisonCreate']
export type Report = S['ReportOut']
export type ReportDetail = S['ReportDetail']
export type ExportCreate = S['ExportCreate']
export type ExportJob = S['ExportJobOut']
export type ReviewItem = S['ReviewItemOut']
export type AuditEvent = S['AuditEventOut']
export type Config = S['ConfigOut']
export type ConfigUpdate = S['ConfigUpdate']
export type VerificationStatus = System['verification_status']

export type AttributeEvidence = S['AttributeEvidenceOut']
export type ComponentStorybook = S['ComponentStorybookOut']

export interface StorybookProject {
  id: number
  slug: string
  title: string
  organization?: string | null
  storybook_url?: string | null
  resolved_url?: string | null
  repository_url?: string | null
  framework?: string | null
  storybook_version?: string | null
  system_key?: string | null
  status: string
  index_kind?: string | null
  stories_discovered: number
  stories_extracted: number
  docs_entries: number
  variants_extracted: number
  source_files_parsed: number
  failed_requests: number
  limitation?: string | null
  retry_eligible: boolean
  last_checked_at?: string | null
}

export interface StorybookStory {
  id: number
  project_id: number
  entry_id: string
  entry_type: 'story' | 'docs' | 'autodocs' | 'unknown'
  title: string
  name: string
  export_name?: string | null
  component_name?: string | null
  component_id?: number | null
  resolution_status: 'linked' | 'unresolved' | 'not_applicable'
  tags: string[]
  import_path?: string | null
  story_url: string
  args?: Record<string, unknown> | null
  arg_types?: Record<string, unknown> | null
  source_file_url?: string | null
  extraction_status: string
  evidence: unknown[]
  last_verified_at?: string | null
  variants?: StorybookVariant[]
}

export interface StorybookVariant {
  id: number
  story_id: number
  project_id: number
  component_id?: number | null
  component_name?: string | null
  label: string
  props: Record<string, unknown>
  method: string
  confidence: string
  evidence: unknown[]
}

export interface Facet {
  value: string
  count: number
}

export type ResourceOut = S['ResourceOut']
export type ResourceLink = S['ResourceLink']
export type ResourceType = ResourceOut['resource_type']
export type ResourceCreate = S['ResourceCreate']
export type ResourceUpdate = S['ResourceUpdate']
export type IntakeCheckOut = S['IntakeCheckOut']
export type IntakeRequest = S['IntakeRequest']
export type IntakeOut = S['IntakeOut']
