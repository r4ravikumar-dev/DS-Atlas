export interface RenderProps {
  /** registry implementation name, e.g. "Button" */
  impl: string
  /** validated component props (documented or implementation-provided) */
  props: Record<string, unknown>
  /** preview-only text content */
  content: Record<string, string>
  theme: 'light' | 'dark'
  /** design tokens of the component's own system (used by adapters only) */
  tokens?: { path: string; theme: string | null; value: string }[]
}
