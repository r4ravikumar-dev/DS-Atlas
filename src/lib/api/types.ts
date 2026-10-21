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
export type UserCreate = S['UserCreate']
export type UserUpdate = S['UserUpdate']
export type VerificationStatus = System['verification_status']

export interface Facet {
  value: string
  count: number
}
