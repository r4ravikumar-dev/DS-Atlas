/**
 * Adapted from the open-source Design System Checklist
 * https://github.com/ardakaracizmeli/design-system-checklist — descriptions paraphrased.
 */
export interface ChecklistItem {
  id: string
  title: string
  desc?: string
}
export interface ChecklistSection {
  id: string
  title: string
  items: ChecklistItem[]
}
export interface ChecklistCategory {
  id: string
  title: string
  summary: string
  sections: ChecklistSection[]
}

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')

type Raw = [title: string, desc?: string]
const section = (title: string, items: (Raw | string)[]): ChecklistSection => ({
  id: slug(title),
  title,
  items: items.map((it) => {
    const [t, d] = typeof it === 'string' ? [it] : it
    return { id: `${slug(title)}--${slug(t)}`, title: t, desc: d }
  }),
})

export const CHECKLIST: ChecklistCategory[] = [
  {
    id: 'design-language',
    title: 'Design language',
    summary: 'Brand, principles and the written voice that every component inherits.',
    sections: [
      section('Brand', [
        ['Vision', 'Why the product exists, its values, and how they guide the future.'],
        ['Design principles', 'The core beliefs that shape everyday design decisions.'],
        ['Tone of voice', 'How the product speaks to users at each stage of their journey.'],
        ['Terminology', 'Standard terms and phrases used consistently across the experience.'],
        ['Brand assets', 'Consistent logo, fonts, icons and illustrations across product and marketing.'],
      ]),
      section('Guidelines', [
        ['Accessibility', 'How colour, hierarchy and assistive technologies support every user.'],
        ['Writing guidelines', 'A house style for grammar, style choices and action-oriented language.'],
        ['Microcopy guidelines', 'Standards for the text inside system components.'],
        ['Shared terminology', 'One vocabulary to speed up design and unify voice.'],
        ['Internationalisation', 'Rules for translated content, edge cases and bidirectional text.'],
      ]),
    ],
  },
  {
    id: 'foundations',
    title: 'Design foundations',
    summary: 'The tokens: colour, layout, type, elevation, motion and iconography.',
    sections: [
      section('Color', [
        ['Accessibility', 'Text and background pairs meet at least WCAG AA contrast.'],
        ['Semantic colors', 'Role-based variables for actions, backgrounds, disabled and high-contrast text.'],
        ['Dark mode', 'A dark palette that follows the user’s OS preference.'],
        ['Guidelines', 'When to use each colour, what to watch for and what to avoid.'],
      ]),
      section('Layout', [
        ['Units', 'A granular base increment (e.g. 4-point) for grid and spacing.'],
        ['Grid', 'Column, gutter and margin definitions for mobile, tablet and desktop.'],
        ['Breakpoints', 'Predefined screen sizes and orientations the grid adapts to.'],
        ['Spacing', 'Grid-independent ways to add space between elements.'],
      ]),
      section('Typography', [
        ['Responsiveness', 'Font sizes scale with the viewport.'],
        ['Grid relation', 'Sizes and line heights align with the grid so text pairs with icons.'],
        ['Readability', 'Tuned letter spacing, line height and line length.'],
        ['Performance', 'Fast-loading fonts, fallbacks or system stacks.'],
        ['Guidelines', 'How and when to use each type pairing.'],
      ]),
      section('Elevation', [
        ['Shadows', 'Three to four shadow values for supported elevation levels.'],
        ['Background colors', 'A surface colour per level so depth reads in dark mode.'],
        ['Z-index', 'A layering scale controlling what renders on top.'],
      ]),
      section('Motion', [
        ['Easing', 'Standard, accelerated and decelerated easing curves.'],
        ['Duration', 'A shared set of durations for consistent transitions.'],
        ['Accessibility', 'Respect prefers-reduced-motion by toning down animation.'],
      ]),
      section('Iconography', [
        ['Accessibility', 'Meaningful icons get an accessible name; decorative ones stay hidden.'],
        ['Style', 'One consistent style — outlined or filled.'],
        ['Naming', 'Name icons by purpose, not appearance.'],
        ['Relation with grid', 'Bounding boxes that align with the grid and pair with text.'],
        ['Keywords', 'Searchable keywords for each icon.'],
        ['Reserved icons', 'Common actions (navigation, add, delete) are never repurposed.'],
        ['Guidelines', 'How and when to use icons, and what to avoid.'],
      ]),
    ],
  },
  {
    id: 'components',
    title: 'Components',
    summary: 'States, variants and accessibility requirements for 30 core components.',
    sections: [
      section('Accordion', ['Active state', 'Composition', 'Toggle transition', 'Content and trigger relation']),
      section('Alert', ['Colors', 'Title support', 'Icon support', 'Supplementary actions', 'Responsiveness', 'Accessibility roles']),
      section('Avatar', ['Image', 'Image fallback', 'Sizes', 'Colors', 'Shape', 'Avatar groups', 'Accessibility label']),
      section('Badge', ['Colors', 'Variants', 'Sizes', 'Icon support', 'Dismissible action', 'Empty state', 'Positioning']),
      section('Button', ['Colors', 'Variants', 'Sizes', 'Icon support', 'Hover state', 'Active state', 'Loading state', 'Disabled state', 'Accessibility role', 'Focus indicator']),
      section('Breadcrumbs', ['Icon support', 'Disabled state', 'Collapsed state', 'Custom separator']),
      section('Calendar', ['Display modes', 'Selected state', 'Month selection', 'Day names', 'Internationalisation', 'Keyboard navigation', 'State announcement']),
      section('Card', ['Content composition', 'Media sections', 'Supplementary actions', 'Responsiveness', 'Card groups']),
      section('Carousel', ['Navigation controls', 'Item composition', 'Item sizes', 'Touch navigation', 'Responsiveness', 'Keyboard navigation']),
      section('Checkbox', ['Label', 'Checked state', 'Error state', 'Disabled state', 'Indeterminate state', 'Checkbox group', 'Keyboard support']),
      section('Divider', ['Direction', 'Accessibility role']),
      section('Dropdown', ['Content composition', 'Hover trigger', 'Dynamic positioning', 'Responsiveness', 'Focus trapping', 'Keyboard navigation']),
      section('Icon', ['Colors', 'Sizes', 'Interactivity']),
      section('Image', ['Sizes', 'Image fallback', 'Screen density support', 'Alt text']),
      section('Link', ['Icon support', 'Colors', 'Disabled state', 'Font inheritance', 'Multiline display', 'Accessibility role']),
      section('List', ['Order', 'Content composition', 'Accessibility role']),
      section('Loading indicator', ['Colors', 'Sizes', 'Loading duration', 'Reduced motion', 'Accessibility label']),
      section('Modal', ['Content composition', 'Supplementary actions', 'Close action', 'Positioning', 'Sizes', 'Focus trapping', 'Keyboard navigation', 'Title and subtitle labeling']),
      section('Pagination', ['Selected page state', 'Page display ranges', 'Items per page', 'Indeterminate amount of pages', 'Full page label announcements', 'State announcement']),
      section('Progress bar', ['Label', 'Sizes', 'Duration', 'Accessibility label']),
      section('Radio', ['Label', 'Checked state', 'Error state', 'Disabled state', 'Radio group', 'Keyboard support']),
      section('Select', ['Label', 'Error state', 'Disabled state', 'Placeholder', 'Helper text', 'Icon support', 'Prefix', 'Sizes', 'Accessibility label']),
      section('Skeleton', ['Sizes', 'Shapes', 'Composition', 'Reduced motion']),
      section('Switch', ['Label', 'Checked state', 'Disabled state', 'Keyboard navigation', 'Accessibility label']),
      section('Tabs', ['Content composition', 'Variants', 'Selected state', 'Disabled state', 'Icon support', 'Equal width layout', 'Keyboard support']),
      section('Text area', ['Label', 'Error state', 'Disabled state', 'Placeholder', 'Helper text', 'Sizes', 'Accessibility label']),
      section('Text field', ['Label', 'Error state', 'Disabled state', 'Placeholder', 'Helper text', 'Icon support', 'Prefix / Suffix', 'Sizes', 'Accessibility label']),
      section('Toast', ['Content composition', 'Colors', 'Icon support', 'Timeout', 'Stacking', 'Actions', 'Accessibility role']),
      section('Tooltip', ['Positioning', 'Hover and focus trigger', 'Delay', 'Keyboard dismissal', 'Accessibility role']),
    ],
  },
  {
    id: 'maintenance',
    title: 'Maintenance',
    summary: 'Documentation, processes, support and contribution that keep it alive.',
    sections: [
      section('Documentation', [
        ['Design system principles', 'The core values that guide team decisions.'],
        ['Getting started', 'First setup steps so people can build without asking you.'],
        ['Design best practices', 'Scalable design tips, pitfalls and tool usage.'],
        ['Development best practices', 'Recommended dependencies, tips and pitfalls.'],
        ['Component anatomy', 'Layout, limits and customisable parts of each component.'],
        ['Component properties', 'Props documented in design and code, aligned across platforms.'],
        ['Composition examples', 'How low-level components combine via slots.'],
        ['Sandbox product example', 'A realistic app to test components before release.'],
        ['Browser / OS support', 'Which browsers and platforms are supported.'],
        ['Release cycle', 'A predictable schedule for breaking-change releases.'],
      ]),
      section('Local libraries', [
        ['When to build', 'When teams should build their own components vs. request or reuse.'],
        ['Horizontal and vertical libraries', 'Shared cross-product libraries vs. single-team ones.'],
        ['Library expectations', 'Minimum standards for quality, docs and maintenance.'],
        ['Release cycle alignment', 'Local libraries stay in sync with system majors.'],
      ]),
      section('Team processes', [
        ['Decision-making log', 'Recorded decisions and context to avoid re-litigating.'],
        ['Roadmap', 'Long-term plans that reserve time for community support.'],
        ['Stakeholder mapping', 'Who influences the system, including leadership.'],
        ['Analytics', 'Docs traffic, feedback surveys and component usage data.'],
        ['Support shifts', 'Rotating support duty so others can focus.'],
        ['SLA', 'Response times for requests and bug reports.'],
      ]),
      section('Community support', [
        ['Support channels', 'Communication channels separated by platform.'],
        ['Templates', 'Feature-request and bug-report forms that collect context.'],
        ['Regular updates', 'A cadence for announcing changes.'],
        ['Open hours', 'Bookable slots for consultations.'],
      ]),
      section('Contribution', [
        ['House rules', 'The process, and why system work moves slower than product work.'],
        ['Contribution guidelines', 'How to set up the environment to add and test features.'],
        ['Feature proposal template', 'A standard format ensuring cross-platform, non-breaking changes.'],
        ['Engagement', 'Public recognition for contributors and manager support.'],
      ]),
    ],
  },
]

export const CHECKLIST_TOTAL = CHECKLIST.reduce(
  (n, c) => n + c.sections.reduce((m, s) => m + s.items.length, 0),
  0,
)
