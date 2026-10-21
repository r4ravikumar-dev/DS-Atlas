export interface Resource {
  name: string
  url: string
  desc: string
  repo?: string
  /** Extra label, e.g. author or "Figma plugin" */
  meta?: string
  /** Where this entry was curated from */
  source?: string
}

export interface ResourceGroup {
  id: string
  title: string
  kicker: string
  intro: string
  items: Resource[]
}

const DSG = 'thedesignsystem.guide'
const DSC = 'designsystems.com'

/* ───────────── 1. Directories & meta-collections ───────────── */
export const DIRECTORIES: Resource[] = [
  { name: 'The Component Gallery', url: 'https://component.gallery', meta: 'Closed source', desc: 'Best for UI benchmarking. Compares 60+ components across 95+ design systems with direct links to each company’s live docs.' },
  { name: 'Design Systems Surf', url: 'https://designsystems.surf', meta: 'Closed source', desc: 'Best for Figma & token discovery. Indexes systems by components, tokens and public Figma Community files.' },
  { name: 'Adele by UXPin', url: 'https://adele.uxpin.com', repo: 'https://github.com/uxpin/adele', desc: 'Best for technical architecture audits. Filter systems by CSS architecture, token naming, accessibility standards and testing tools.' },
  { name: 'Design Systems Repo', url: 'https://designsystemsrepo.com', meta: 'Closed source', desc: 'Best for team resources. A curated gallery paired with articles, talks, books and documentation tooling.' },
  { name: 'Storybook Showcase', url: 'https://storybook.js.org/showcase', repo: 'https://github.com/storybookjs/storybook', desc: 'Best for live code inspection. Browse production Storybooks from BBC, GitLab, Monday.com and more to inspect props and states.' },
  { name: 'Design Systems Directory', url: 'https://designsystems.directory', meta: 'Closed source', desc: 'Best for broad alphabetical lookup. A straightforward index of 150+ public style guides and pattern libraries.' },
  { name: 'designsystems.one', url: 'https://www.designsystems.one/design-systems', meta: 'Gallery', desc: '120+ systems tagged by stack, token pipeline, source model, Figma kit availability and an AI-readiness score.' },
  { name: 'designsystems.com', url: 'https://www.designsystems.com', meta: 'By Figma', desc: 'Figma’s design-systems publication: getting-started guides, operations stories, Schema talks and open Figma files.' },
  { name: 'The Design System Guide', url: 'https://thedesignsystem.guide/resources', meta: 'By Romina Kavcic', desc: 'A practitioner’s library of tools, plugins, books, podcasts and courses for building and measuring systems.' },
  { name: 'Design Principles FTW', url: 'https://www.designprinciplesftw.com', meta: 'Collection', desc: 'A regularly updated collection of published design principles from teams around the world.' },
  { name: 'DesignSystems.Media', url: 'https://designsystems.media', meta: 'Video', desc: 'A collection of design-systems talks and videos.' },
]

/* ───────────── 2. GitHub awesome lists & token pipelines ───────────── */
export const REPOS: Resource[] = [
  { name: 'alexpate/awesome-design-systems', url: 'https://github.com/alexpate/awesome-design-systems', meta: '26k+ stars', desc: 'The largest index. Tags every system by what it makes public: source code, voice & tone, designer kit and coded components.' },
  { name: 'klaufel/awesome-design-systems', url: 'https://github.com/klaufel/awesome-design-systems', meta: 'Engineering & DesignOps', desc: 'W3C token validators, documentation engines and visual regression testing tools.' },
  { name: 'saadeghi/design-systems', url: 'https://github.com/saadeghi/design-systems', meta: 'Markdown table', desc: 'A zero-fluff table of 90+ major design systems with direct documentation links.' },
  { name: 'Style Dictionary', url: 'https://styledictionary.com', repo: 'https://github.com/amzn/style-dictionary', meta: 'Amazon', desc: 'Build system for design tokens. Compile one JSON token set into CSS variables, Swift and Android XML/Compose.' },
  { name: 'W3C Design Tokens Community Group', url: 'https://tr.designtokens.org/format/', repo: 'https://github.com/design-tokens/community-group', meta: 'Specification', desc: 'The official cross-tool token format ($value, $type). Use it from day one so tokens move between Figma Variables and code.' },
  { name: 'Design System Checklist', url: 'https://www.designsystemchecklist.com', repo: 'https://github.com/ardakaracizmeli/design-system-checklist', meta: 'Planning', desc: 'Open-source planning checklist: tokens, component states, accessibility and governance. Interactive version on this site.' },
  { name: 'Cobalt', url: 'https://www.cobaltui.dev', meta: 'Token tooling', desc: 'Turns W3C design tokens into code for any platform.' },
  { name: 'React Scanner', url: 'https://github.com/moroshko/react-scanner', meta: 'Adoption metrics', desc: 'Extracts React component and prop usage from your codebase for adoption tracking.' },
  { name: 'Adobe Spectrum Token Visualizer', url: 'https://opensource.adobe.com/spectrum-tokens/visualizer/', repo: 'https://github.com/adobe/spectrum-tokens', meta: 'Reference', desc: 'Explore how Spectrum’s token aliases resolve across themes and platforms.' },
]

/* ───────────── 3. Resource library (thedesignsystem.guide + designsystems.com) ───────────── */
export const RESOURCE_GROUPS: ResourceGroup[] = [
  {
    id: 'platforms', title: 'Design system platforms', kicker: 'Docs & ops',
    intro: 'Where the system lives: documentation hubs, token management and code workshops.',
    items: [
      { name: 'Storybook', url: 'https://storybook.js.org', desc: 'The code-side workshop for building, testing and documenting components.', source: DSG },
      { name: 'Zeroheight', url: 'https://zeroheight.com', desc: 'Central documentation hub shared by design and engineering.', source: DSG },
      { name: 'Supernova', url: 'https://www.supernova.io', desc: 'System-as-a-service: docs, tokens and code pipelines in one platform.', source: DSG },
      { name: 'Knapsack', url: 'https://www.knapsack.cloud', desc: 'Documentation, token management and CI/CD for design systems.', source: DSG },
      { name: 'Penpot', url: 'https://penpot.app', desc: 'Open-source, web-based design tool built on open standards.', source: DSG },
      { name: 'Frontify', url: 'https://www.frontify.com/en/', desc: 'Brand management platform and guideline portal.', source: DSG },
      { name: 'Backlight.dev', url: 'https://backlight.dev', desc: 'Collaborative code-side environment for design systems.', source: DSG },
      { name: 'Figmayo', url: 'https://www.figmayo.com', desc: 'Publish documentation sites directly from Figma.', source: DSG },
    ],
  },
  {
    id: 'ai', title: 'AI & automation', kicker: 'Speed',
    intro: 'Tools that automate repetitive Figma work or generate UI from prompts.',
    items: [
      { name: 'Automator', url: 'https://automator.design', desc: 'One-click Figma automations with 100+ actions over the Plugin API.', source: DSG },
      { name: 'Magician', url: 'https://magician.design', desc: 'AI-powered copywriting, icons and imagery inside Figma.', source: DSG },
      { name: 'Patterns', url: 'https://www.designpatterns.io/ai', desc: 'AI front-end assistant for pattern generation.', source: DSG },
      { name: 'Galileo UI', url: 'https://www.usegalileo.ai/explore', desc: 'Generate UI designs quickly from text prompts.', source: DSG },
      { name: 'Ando', url: 'https://www.figma.com/community/plugin/1145446664512862540/ando-ai-copilot-for-designers', meta: 'Figma plugin', desc: 'AI copilot for designers.', source: DSG },
      { name: 'Anima', url: 'https://www.animaapp.com/use-cases/design-systems', desc: 'Sync Storybook components into Figma and export designs to code.', source: DSG },
      { name: 'Design System Concierge', url: 'https://www.kickstartds.com/concierge', desc: 'AI-powered assistant for planning a design system.', source: DSG },
      { name: 'AI Design Guide', url: 'https://www.aidesign.guide', desc: 'Companion guide on designing with and for AI.', source: DSG },
    ],
  },
  {
    id: 'plugins', title: 'Figma plugins', kicker: 'Craft',
    intro: 'Plugins that keep libraries tidy, documented and token-driven.',
    items: [
      { name: 'Tokens Studio', url: 'https://tokens.studio', desc: 'Design tokens in Figma with themes, sets and Git sync.', source: DSG },
      { name: 'Story.to.design', url: 'https://story.to.design', desc: 'Generate Figma components and variants from Storybook stories.', source: DSG },
      { name: 'EightShapes Specs', url: 'https://www.figma.com/community/search?resource_type=plugins&query=eightshapes%20specs', desc: 'Automate component specification sheets.', source: DSG },
      { name: 'Gist', url: 'https://www.figma.com/community/plugin/1073059820691713754/Gist', desc: 'Attach Markdown documentation to components.', source: DSG },
      { name: 'Design System Manager', url: 'https://www.toolabs.com', desc: 'Visual token manager with a documentation designer.', source: DSG },
      { name: 'Similayer', url: 'https://www.figma.com/community/plugin/735733267883397781/Similayer', desc: 'Select layers that share properties.', source: DSG },
      { name: 'Figma Autoname', url: 'https://www.figma.com/community/search?resource_type=plugins&query=autoname', desc: 'Rename all layers in one click. Free and open source.', source: DSG },
      { name: 'Instance Finder', url: 'https://www.figma.com/community/plugin/741895659787979282/Instance-Finder', desc: 'Find every instance of a component in a file.', source: DSG },
      { name: 'Propstar', url: 'https://www.figma.com/community/plugin/1116018586739867857/Propstar', desc: 'Generate a property table of component instances.', source: DSG },
    ],
  },
  {
    id: 'colour', title: 'Colour', kicker: 'Foundations',
    intro: 'Generate accessible, perceptually even palettes.',
    items: [
      { name: 'Leonardo', url: 'https://leonardocolor.io', desc: 'Adobe’s contrast-based colour generator for design systems.', source: DSG },
      { name: 'Farbvelo', url: 'https://farbvelo.elastiq.ch', desc: 'Palette generator with inspiration modes.', source: DSG },
      { name: 'Supa Palette', url: 'https://www.supa-palette.com', desc: 'Palette generator, editor and manager for Figma.', source: DSG },
      { name: 'Shaper', url: 'https://hihayk.github.io/shaper/', desc: 'Explore interface styles — radius, density, type — in real time.', source: DSG },
    ],
  },
  {
    id: 'a11y', title: 'Accessibility', kicker: 'Inclusion',
    intro: 'Check contrast, simulate vision deficiencies and build accessible workflows.',
    items: [
      { name: 'Stark', url: 'https://www.getstark.co', desc: 'End-to-end accessibility workflow across design and code.', source: DSG },
      { name: 'Contrast', url: 'https://www.figma.com/community/plugin/748533339900865323/Contrast', meta: 'Figma plugin', desc: 'Check the contrast of selected objects.', source: DSG },
      { name: 'Randoma11y', url: 'https://randoma11y.com', desc: 'Preview random accessible colour combinations.', source: DSG },
      { name: 'Usecontrast', url: 'https://usecontrast.com', desc: 'Contrast checker plugin for Figma.', source: DSG },
      { name: 'Able', url: 'https://www.figma.com/community/plugin/734693888346260052/able-friction-free-accessibility', meta: 'Figma plugin', desc: 'Friction-free accessibility checks.', source: DSG },
      { name: 'ADEE', url: 'https://www.figma.com/community/plugin/931280467863251825/Adee-Comprehensive-Accessibility-Tool', meta: 'Figma plugin', desc: 'Colour-blindness simulation and contrast checking.', source: DSG },
    ],
  },
  {
    id: 'metrics', title: 'Metrics & adoption', kicker: 'Measure',
    intro: 'Prove the value of your system with usage data.',
    items: [
      { name: 'Omlet', url: 'https://omlet.dev', desc: 'Measure component usage by analysing your codebases.', source: DSG },
      { name: 'React Scanner', url: 'https://github.com/moroshko/react-scanner', desc: 'Open-source CLI that extracts component usage stats.', source: DSG },
      { name: 'Design System Report', url: 'https://www.uxpin.com/studio/ebooks/designops-design-system-report/', meta: 'UXPin', desc: 'Industry report on DesignOps and system maturity.', source: DSG },
      { name: 'Design System Metrics', url: 'https://thedesignsystem.guide/design-system-metrics', desc: 'How to choose and track design-system KPIs.', source: DSG },
    ],
  },
  {
    id: 'kits', title: 'Libraries & UI kits', kicker: 'Start fast',
    intro: 'Starter kits and libraries to bootstrap a system in Figma or code.',
    items: [
      { name: 'Practical UI', url: 'https://www.practical-ui.com', desc: 'Figma starter kit with logical, accessible defaults.', source: DSG },
      { name: 'KickstartDS', url: 'https://www.kickstartds.com', desc: 'Open-source design system starter kit.', source: DSG },
      { name: 'Reshaped', url: 'https://reshaped.so', desc: 'Premium React + Figma design system.', source: DSG },
      { name: 'Wanda', url: 'https://design.wonderflow.ai', desc: 'Open-source design system by Wonderflow.', source: DSG },
      { name: 'Flowbite Design System', url: 'https://www.figma.com/community/file/1179442320711977498', desc: 'Free Figma component collection matching Flowbite.', source: DSG },
      { name: 'UIPrep', url: 'https://www.uiprep.com/design-system-ui-kit-for-figma', desc: 'Figma design-system UI kit.', source: DSG },
      { name: 'Detachless', url: 'https://detachless.com/figma-ui-kit', desc: 'Figma UI kit built to avoid detaching.', source: DSG },
      { name: 'Cabana', url: 'https://cabana-for-figma.lemonsqueezy.com', desc: 'Figma design system for building faster.', source: DSG },
      { name: 'Tailwind UI', url: 'https://tailwindcss.com/plus', desc: 'Professionally designed Tailwind components.', source: DSG },
      { name: 'Styled System', url: 'https://styled-system.com', desc: 'Style props for building custom UI components.', source: DSG },
      { name: 'Reach UI', url: 'https://github.com/reach/reach-ui', desc: 'Accessible foundation React components.', source: DSG },
      { name: 'Quasar', url: 'https://quasar.dev/docs', desc: 'MIT-licensed Vue.js framework.', source: DSG },
    ],
  },
  {
    id: 'books', title: 'Books', kicker: 'Read',
    intro: 'The canon — methodology, scaling and practice.',
    items: [
      { name: 'Atomic Design', url: 'https://atomicdesign.bradfrost.com', meta: 'Brad Frost', desc: 'The hierarchical methodology behind modern pattern libraries.', source: DSG },
      { name: 'Design That Scales', url: 'https://designsystem.university/books/design-that-scales', meta: 'Dan Mall', desc: 'Building a sustainable design-system practice.', source: DSG },
      { name: 'Design Systems Handbook', url: 'https://www.designbetter.co/design-systems-handbook', meta: 'Marco Suarez et al.', desc: 'Planning, building and implementing design systems.', source: DSG },
      { name: 'Laying the Foundations', url: 'https://www.goodreads.com/search?q=Laying+the+Foundations+Andrew+Couldwell', meta: 'Andrew Couldwell', desc: 'Systematic design and maintaining a living system.', source: DSG },
      { name: 'A Practical Guide to Design System Components', url: 'https://redesigningdesign.systems/resources.html', meta: 'Ness Grixti', desc: 'Four-part guide to creating and documenting components.', source: DSG },
      { name: 'Continuous Discovery Habits', url: 'https://www.producttalk.org/continuous-discovery-habits/', meta: 'Teresa Torres', desc: 'A structured approach to continuous product discovery.', source: DSG },
    ],
  },
  {
    id: 'podcasts', title: 'Podcasts', kicker: 'Listen',
    intro: 'Conversations with practitioners on scaling, adoption and team models.',
    items: [
      { name: 'Design System Office Hours', url: 'https://podcasts.apple.com/us/podcast/design-system-office-hours/id1605819337', meta: 'Davy Fung & PJ Onori', desc: 'Scaling, adoption and team models from practitioners.', source: DSG },
      { name: 'The Design System Guide Podcast', url: 'https://thedesignsystem.guide/design-system-interviews', meta: 'Romina Kavcic', desc: 'Interviews with design-system experts.', source: DSG },
      { name: 'Design Systems Podcast', url: 'https://www.designsystemspodcast.com', meta: 'Chris Strahl', desc: 'Industry leaders on design and development.', source: DSG },
      { name: 'What the DS?', url: 'https://podcasts.apple.com/us/podcast/what-the-ds/id1668798071', meta: 'Dan Cork & Dan Donald', desc: 'Lighthearted stories from design-system journeys.', source: DSG },
      { name: 'Code & Pixels', url: 'https://codeandpixels.fm', meta: 'Adekunle Oduye & Kelly Harrop', desc: 'Conversations on UX engineering.', source: DSG },
      { name: 'DesignOps Island Discs', url: 'https://podcasts.apple.com/us/podcast/designops-island-discs/id1567001691', meta: 'zeroheight', desc: 'DesignOps conversations with practitioners worldwide.', source: DSG },
    ],
  },
  {
    id: 'video', title: 'Video & workshops', kicker: 'Watch',
    intro: 'Talks, tutorials and live workshops.',
    items: [
      { name: 'The Design System Guide on YouTube', url: 'https://www.youtube.com/@designsystemguide', desc: 'AI, automation and design systems.', source: DSG },
      { name: 'Figma on YouTube', url: 'https://www.youtube.com/@Figma', desc: 'Official Figma channel incl. Config & Schema talks.', source: DSG },
      { name: 'Smashing Workshops', url: 'https://www.smashingmagazine.com/online-workshops/', desc: 'Online workshops on design systems and interface patterns.', source: DSG },
      { name: 'Typography: Ultimate Design System Breakdown', url: 'https://www.youtube.com/watch?v=9w-BwzcuxYM', meta: 'Tim Lee', desc: 'A deep dive into type scales in a design system.', source: DSG },
      { name: 'Tokens Studio Quickstart', url: 'https://www.youtube.com/watch?v=7utmznIOWLU', desc: 'Introductory tutorial for Tokens Studio.', source: DSG },
      { name: 'In the File: multi-product design systems', url: 'https://www.youtube.com/watch?v=tMGtwX-t0no', meta: 'Figma', desc: 'Building one system across multiple products.', source: DSG },
      { name: 'Design Tokens Course', url: 'https://thedesignsystem.guide/design-tokens-course', desc: 'Structured course on design tokens.', source: DSG },
    ],
  },
  {
    id: 'dsc-articles', title: 'designsystems.com essentials', kicker: 'By Figma',
    intro: 'Hand-picked articles from Figma’s design-systems publication.',
    items: [
      { name: 'Six myths holding you back from design systems', url: 'https://designsystems.com/six-myths-holding-you-back-from-embracing-design-systems/', meta: 'Featured', desc: 'Setting the record straight on common objections.', source: DSC },
      { name: 'Space, grids and layouts', url: 'https://designsystems.com/space-grids-and-layouts/', meta: 'Getting started', desc: 'Spacing scales and grid systems explained.', source: DSC },
      { name: 'A complete guide to iconography', url: 'https://designsystems.com/iconography-guide/', meta: 'Getting started', desc: 'Designing and maintaining an icon set.', source: DSC },
      { name: 'Typography guides', url: 'https://designsystems.com/typography-guides/', meta: 'Getting started', desc: 'Type scales, pairing and hierarchy.', source: DSC },
      { name: 'Content strategy in design systems', url: 'https://designsystems.com/guide-to-content-strategy-in-design-systems/', meta: 'Getting started', desc: 'Bringing voice and content into the system.', source: DSC },
      { name: 'How Spotify’s design system goes beyond platforms', url: 'https://designsystems.com/how-spotifys-design-system-goes-beyond-platforms/', meta: 'Design & dev', desc: 'Encore and cross-platform systems thinking.', source: DSC },
      { name: 'The future of design systems is semantic', url: 'https://designsystems.com/the-future-of-design-systems-is-semantic/', meta: 'Design & dev', desc: 'Why semantic tokens and naming matter.', source: DSC },
      { name: 'The future of design systems is accessible', url: 'https://designsystems.com/the-future-of-design-systems-is-accessible/', meta: 'Design & dev', desc: 'Baking accessibility in from the start.', source: DSC },
      { name: 'How Thumbtack structures their design system', url: 'https://designsystems.com/how-thumbtack-structures-their-design-system/', meta: 'Operations', desc: 'Team structure and library architecture.', source: DSC },
      { name: 'Keeping contributions in check', url: 'https://designsystems.com/keeping-design-system-contributions-in-check/', meta: 'Operations', desc: 'A contribution model that scales.', source: DSC },
      { name: 'Defining components collaboratively', url: 'https://designsystems.com/a-collaborative-approach-to-defining-components-and-their-features/', meta: 'Operations', desc: 'Aligning design and engineering on component APIs.', source: DSC },
      { name: 'Schema by Figma talks', url: 'https://designsystems.com/sections/schema/', meta: 'Talks', desc: 'Schema New York, London and Tokyo recordings.', source: DSC },
    ],
  },
  {
    id: 'figma-files', title: 'Open Figma files', kicker: 'Duplicate & study',
    intro: 'Official design-system libraries published to the Figma Community.',
    items: [
      { name: 'Material 3 Design Kit', url: 'https://www.figma.com/community/file/1035203688168086460', meta: 'Google', desc: 'The official M3 library with dynamic colour.', source: DSC },
      { name: 'GitHub Primer', url: 'https://www.figma.com/community/file/854767373644076713', meta: 'GitHub', desc: 'Primer primitives and components.', source: DSC },
      { name: 'Atlassian ADS Foundations', url: 'https://www.figma.com/community/file/1527530559648073327', meta: 'Atlassian', desc: 'Tokens and foundations for Atlassian products.', source: DSC },
      { name: 'Salesforce Lightning', url: 'https://www.figma.com/community/file/854593583696357016', meta: 'Salesforce', desc: 'Lightning Design System UI kit.', source: DSC },
      { name: 'Spotify Backstage', url: 'https://www.figma.com/community/file/850673348101741100', meta: 'Spotify', desc: 'Backstage developer-portal design kit.', source: DSC },
      { name: 'Airtable Base SDK', url: 'https://www.figma.com/community/file/862805330899066752', meta: 'Airtable', desc: 'Components for Airtable extensions.', source: DSC },
      { name: 'Figma Community: design systems', url: 'https://www.figma.com/community/design-systems', meta: 'Browse all', desc: 'Every public design-system file on Figma.', source: DSC },
    ],
  },
]

/* ───────────── 4. Production code foundations ───────────── */
export interface Foundation {
  id: string
  name: string
  url: string
  repo: string
  tagline: string
  desc: string
  bestFor: string
  styling: string
  /** 1–5 relative scores */
  control: number
  speed: number
  a11y: number
}

export const FOUNDATIONS: Foundation[] = [
  { id: 'shadcn', name: 'shadcn/ui', url: 'https://ui.shadcn.com', repo: 'https://github.com/shadcn-ui/ui', tagline: 'Own the code', desc: 'Copies accessible component source into your repo using Tailwind CSS and Radix/Base UI primitives — full control over token mapping and styling, no upstream breaking changes.', bestFor: 'Product teams that want a custom look without building primitives', styling: 'Tailwind + CSS vars', control: 5, speed: 4, a11y: 4 },
  { id: 'radix', name: 'Radix Primitives', url: 'https://www.radix-ui.com/primitives', repo: 'https://github.com/radix-ui/primitives', tagline: 'Unstyled & accessible', desc: 'Unstyled React components that handle focus management, keyboard navigation and ARIA attributes out of the box.', bestFor: 'Building a bespoke visual language from scratch', styling: 'Bring your own', control: 5, speed: 3, a11y: 5 },
  { id: 'base-ui', name: 'Base UI', url: 'https://base-ui.com', repo: 'https://github.com/mui/base-ui', tagline: 'Headless, modern', desc: 'Unstyled headless components from the creators of Radix, Floating UI and Material UI — designed to pair with CSS variables and Tailwind.', bestFor: 'Teams wanting Radix-style primitives with active development', styling: 'Bring your own', control: 5, speed: 3, a11y: 5 },
  { id: 'react-aria', name: 'React Aria', url: 'https://react-spectrum.adobe.com/react-aria/', repo: 'https://github.com/adobe/react-spectrum', tagline: 'Accessibility hooks', desc: 'Headless hooks and components with internationalised date/number pickers and screen-reader-tested mobile touch support.', bestFor: 'Global products with strict a11y and i18n requirements', styling: 'Bring your own', control: 5, speed: 2, a11y: 5 },
  { id: 'mantine', name: 'Mantine', url: 'https://mantine.dev', repo: 'https://github.com/mantinedev/mantine', tagline: 'Batteries included', desc: '100+ pre-styled components and hooks that are easy to theme via CSS variables without building primitives.', bestFor: 'Small teams shipping full apps quickly', styling: 'CSS modules + vars', control: 3, speed: 5, a11y: 4 },
  { id: 'antd', name: 'Ant Design', url: 'https://ant.design', repo: 'https://github.com/ant-design/ant-design', tagline: 'Enterprise CRUD', desc: 'The fastest route to complex internal enterprise tables, forms and admin CRUD panels.', bestFor: 'Internal tools and data-heavy B2B dashboards', styling: 'CSS-in-JS tokens', control: 2, speed: 5, a11y: 3 },
]
