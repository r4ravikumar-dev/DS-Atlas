export type Category =
  | 'enterprise'
  | 'saas'
  | 'consumer'
  | 'public'
  | 'platform'
  | 'library'
  | 'industry'

export type Source = 'open' | 'hybrid' | 'closed'

export interface DesignSystem {
  id: string
  name: string
  company: string
  url: string
  repo?: string
  category: Category
  stack: string[]
  source: Source
  figma?: 'official' | 'community'
  /** AI-readiness score from designsystems.one (0–5) where published */
  ai?: number
  /** Short headline for what the system is best at */
  strength: string
  /** Longer context on why to study it */
  why?: string
  /** Part of the hand-curated benchmark list */
  featured?: boolean
}

export const CATEGORIES: Record<Category, { label: string; blurb: string }> = {
  enterprise: { label: 'Enterprise & Data', blurb: 'Cloud consoles, analytics, dense admin UIs' },
  saas: { label: 'SaaS & Dev Tools', blurb: 'B2B products, developer platforms, collaboration' },
  consumer: { label: 'Consumer & Fintech', blurb: 'Marketplaces, payments, mobility, social' },
  public: { label: 'Public Sector', blurb: 'Government, accessibility-first, citizen services' },
  platform: { label: 'OS & Platforms', blurb: 'Operating-system level languages & ecosystems' },
  library: { label: 'Libraries & Frameworks', blurb: 'Install-and-ship component libraries & primitives' },
  industry: { label: 'Industry & Brand', blurb: 'Automotive, travel, retail, media, health, education' },
}

const gh = (path: string) => `https://github.com/${path}`

export const SYSTEMS: DesignSystem[] = [
  // ───────────── Enterprise, Cloud & Data-Dense Consoles ─────────────
  {
    id: 'carbon', name: 'Carbon', company: 'IBM', url: 'https://carbondesignsystem.com',
    repo: gh('carbon-design-system/carbon'), category: 'enterprise',
    stack: ['Tokens', 'React', 'Vue', 'Svelte', 'Style Dictionary'], source: 'open', figma: 'official', ai: 4,
    strength: 'Enterprise governance, accessibility & AI',
    why: 'Unmatched WCAG keyboard diagrams, public deprecation rules and Carbon for AI — patterns for LLM interfaces and agentic workflows.',
    featured: true,
  },
  {
    id: 'cloudscape', name: 'Cloudscape', company: 'Amazon Web Services', url: 'https://cloudscape.design',
    repo: gh('cloudscape-design/components'), category: 'enterprise',
    stack: ['Tokens', 'React', 'Style Dictionary'], source: 'open', ai: 1,
    strength: 'Data-dense technical consoles',
    why: 'Built for cloud dashboards: multi-column tables, advanced property filtering, split panels and resource creation wizards.',
    featured: true,
  },
  {
    id: 'spectrum', name: 'Spectrum', company: 'Adobe', url: 'https://spectrum.adobe.com',
    repo: gh('adobe/react-spectrum'), category: 'enterprise',
    stack: ['React', 'Web Components', 'Style Dictionary'], source: 'open', figma: 'official', ai: 2,
    strength: 'Headless accessibility & token architecture',
    why: 'Home of React Aria plus a multi-platform JSON token schema (adobe/spectrum-tokens) with a public token visualizer.',
    featured: true,
  },
  {
    id: 'fluent', name: 'Fluent 2', company: 'Microsoft', url: 'https://fluent2.microsoft.design',
    repo: gh('microsoft/fluentui'), category: 'enterprise',
    stack: ['Tokens', 'React', 'Web Components', 'Cross-platform'], source: 'open', figma: 'official',
    strength: 'Cross-platform enterprise ecosystems',
    why: 'Shows how to map raw base values to semantic tokens across Web, Windows and mobile productivity apps.',
    featured: true,
  },
  {
    id: 'eui', name: 'EUI', company: 'Elastic', url: 'https://eui.elastic.co',
    repo: gh('elastic/eui'), category: 'enterprise', stack: ['React'], source: 'open',
    strength: 'Observability & analytics',
    why: 'Built for Kibana — the reference for log viewers, time-series charts and complex query bars.',
    featured: true,
  },
  {
    id: 'blueprint', name: 'Blueprint', company: 'Palantir', url: 'https://blueprintjs.com',
    repo: gh('palantir/blueprint'), category: 'enterprise', stack: ['React'], source: 'open',
    strength: 'High-density desktop web apps',
    why: 'Optimised for data-heavy interfaces requiring compact tables, trees and multi-pane layouts.',
    featured: true,
  },
  {
    id: 'workday-canvas', name: 'Canvas', company: 'Workday', url: 'https://canvas.workday.com',
    repo: gh('Workday/canvas-kit'), category: 'enterprise',
    stack: ['Tokens', 'React', 'Style Dictionary'], source: 'open', figma: 'official', ai: 1,
    strength: 'Enterprise HR & finance workflows',
    why: 'Strong docs on compound components, token migration and accessibility testing.',
    featured: true,
  },
  {
    id: 'druids', name: 'DRUIDS', company: 'Datadog', url: 'https://druids.datadoghq.com',
    category: 'enterprise', stack: ['React'], source: 'closed',
    strength: 'Monitoring & developer dashboards',
    why: 'High-density status indicators, keyboard shortcuts and dark-mode data visualisation.',
    featured: true,
  },
  {
    id: 'lightning', name: 'Lightning Design System', company: 'Salesforce', url: 'https://www.lightningdesignsystem.com',
    repo: gh('salesforce-ux/design-system'), category: 'enterprise',
    stack: ['Tokens', 'Web Components', 'React', 'Style Dictionary'], source: 'open', figma: 'official', ai: 1,
    strength: 'Pioneer of design tokens for CRM-scale products',
  },
  { id: 'sap-fiori', name: 'SAP Fiori', company: 'SAP', url: 'https://www.sap.com/design-system', repo: gh('SAP/ui5-webcomponents'), category: 'enterprise', stack: ['Web Components', 'React'], source: 'open', figma: 'official', strength: 'ERP-grade business applications' },
  { id: 'patternfly', name: 'PatternFly', company: 'Red Hat', url: 'https://www.patternfly.org', repo: gh('patternfly/patternfly-react'), category: 'enterprise', stack: ['Tokens', 'React', 'Angular', 'CSS-only'], source: 'open', figma: 'official', ai: 0, strength: 'Open-source enterprise & hybrid-cloud consoles' },
  { id: 'splunk-ui', name: 'Splunk UI', company: 'Splunk', url: 'https://splunkui.splunk.com', repo: gh('splunk/react-ui'), category: 'enterprise', stack: ['React'], source: 'open', strength: 'Security analytics & dashboards' },
  { id: 'momentum', name: 'Momentum', company: 'Cisco / Webex', url: 'https://momentum.design', repo: gh('momentum-design/momentum-design'), category: 'enterprise', stack: ['Web Components', 'React', 'Angular'], source: 'open', strength: 'Real-time collaboration & meetings' },
  { id: 'horizon', name: 'Horizon', company: 'ServiceNow', url: 'https://horizon.servicenow.com/foundations/all', category: 'enterprise', stack: ['Web Components', 'React'], source: 'closed', figma: 'official', strength: 'IT service workflows' },
  { id: 'redwood', name: 'Redwood', company: 'Oracle', url: 'https://docs.oracle.com/en/cloud/saas/readiness/redwood-adoption/', category: 'enterprise', stack: ['Web Components'], source: 'hybrid', strength: 'Enterprise SaaS suite modernisation' },
  { id: 'siemens-ix', name: 'Siemens iX', company: 'Siemens', url: 'https://ix.siemens.io', repo: gh('siemens/ix'), category: 'enterprise', stack: ['Web Components', 'React', 'Angular'], source: 'open', strength: 'Industrial & IoT applications' },
  { id: 'salt', name: 'Salt', company: 'J.P. Morgan', url: 'https://www.saltdesignsystem.com', repo: gh('jpmorganchase/salt-ds'), category: 'enterprise', stack: ['React'], source: 'open', strength: 'Financial-services trading & data UIs' },
  { id: 'grommet', name: 'Grommet', company: 'Hewlett Packard Enterprise', url: 'https://v2.grommet.io', repo: gh('grommet/grommet'), category: 'enterprise', stack: ['React'], source: 'open', strength: 'Accessible, themeable enterprise React' },
  { id: 'leafygreen', name: 'LeafyGreen UI', company: 'MongoDB', url: 'https://www.mongodb.design', repo: gh('mongodb/leafygreen-ui'), category: 'enterprise', stack: ['Tokens', 'React'], source: 'open', figma: 'official', ai: 0, strength: 'Database tooling & cloud console' },

  // ───────────── B2B SaaS, Developer Tools & Healthcare ─────────────
  {
    id: 'polaris', name: 'Polaris', company: 'Shopify', url: 'https://polaris.shopify.com',
    repo: gh('Shopify/polaris'), category: 'saas',
    stack: ['Tokens', 'React', 'Style Dictionary'], source: 'open', figma: 'official', ai: 1,
    strength: 'Usage rules & microcopy',
    why: 'The benchmark for B2B SaaS docs — when to use a pattern, when not to, what to use instead, and exact voice-and-tone rules.',
    featured: true,
  },
  {
    id: 'primer', name: 'Primer', company: 'GitHub', url: 'https://primer.style',
    repo: gh('primer/react'), category: 'saas',
    stack: ['Tokens', 'React', 'Web Components', 'CSS-only', 'Style Dictionary'], source: 'open', figma: 'official', ai: 3,
    strength: 'Design token taxonomy',
    why: 'primer/primitives structures base, functional and component tokens for light, dark and high-contrast modes.',
    featured: true,
  },
  {
    id: 'pajamas', name: 'Pajamas', company: 'GitLab', url: 'https://design.gitlab.com',
    repo: 'https://gitlab.com/gitlab-org/gitlab-services/design.gitlab.com', category: 'saas',
    stack: ['Tokens', 'Vue'], source: 'open', figma: 'official', ai: 1,
    strength: 'Lifecycle transparency',
    why: 'Documents the maturity status of every component and links directly to user-research findings.',
    featured: true,
  },
  {
    id: 'paste', name: 'Paste', company: 'Twilio', url: 'https://paste.twilio.design',
    repo: gh('twilio-labs/paste'), category: 'saas',
    stack: ['Tokens', 'React'], source: 'open', figma: 'official', ai: 0,
    strength: 'Composable token packages',
    why: 'Accessible, token-driven and deliberately restrictive — strict layout primitives instead of arbitrary CSS overrides.',
    featured: true,
  },
  {
    id: 'geist', name: 'Geist', company: 'Vercel', url: 'https://vercel.com/geist/introduction',
    repo: gh('vercel/geist-font'), category: 'saas',
    stack: ['Tokens', 'React'], source: 'hybrid', ai: 0,
    strength: 'Developer tooling aesthetics',
    why: 'Minimalist, high-precision monochrome grids, keyboard-first navigation and custom typography.',
    featured: true,
  },
  {
    id: 'vibe', name: 'Vibe', company: 'monday.com', url: 'https://vibe.monday.com',
    repo: gh('mondaycom/vibe'), category: 'saas', stack: ['React'], source: 'open',
    strength: 'Collaborative work OS',
    why: 'Clean React architecture focused on interactive tables, status badges and consumer-grade B2B polish.',
    featured: true,
  },
  {
    id: 'atlassian', name: 'Atlassian Design System', company: 'Atlassian', url: 'https://atlassian.design',
    repo: 'https://bitbucket.org/atlassian/atlaskit-mk-2', category: 'saas',
    stack: ['Tokens', 'React', 'Style Dictionary'], source: 'open', figma: 'official', ai: 2,
    strength: 'Multi-product SaaS suites',
    why: 'Navigation patterns, onboarding spotlights and unifying distinct products under one brand.',
    featured: true,
  },
  {
    id: 'nord', name: 'Nord', company: 'Nordhealth', url: 'https://nordhealth.design',
    category: 'saas', stack: ['Web Components', 'Vue', 'React', 'W3C Tokens'], source: 'open', figma: 'official',
    strength: 'Healthcare & clinical SaaS',
    why: 'One of the cleanest examples of Web Components, W3C design tokens and medical-grade UI clarity.',
    featured: true,
  },
  { id: 'garden', name: 'Garden', company: 'Zendesk', url: 'https://garden.zendesk.com', repo: gh('zendeskgarden/react-components'), category: 'saas', stack: ['React', 'Style Dictionary'], source: 'open', strength: 'Customer-support tooling' },
  { id: 'evergreen', name: 'Evergreen', company: 'Segment', url: 'https://evergreen.segment.com', repo: gh('segmentio/evergreen'), category: 'saas', stack: ['React'], source: 'open', strength: 'Flexible React UI for data products' },
  { id: 'ring-ui', name: 'Ring UI', company: 'JetBrains', url: 'https://jetbrains.github.io/ring-ui/', repo: gh('JetBrains/ring-ui'), category: 'saas', stack: ['React'], source: 'open', strength: 'Developer-tool web interfaces' },
  { id: 'helios', name: 'Helios', company: 'HashiCorp', url: 'https://helios.hashicorp.design', repo: gh('hashicorp/design-system'), category: 'saas', stack: ['Tokens', 'Web Components', 'Style Dictionary'], source: 'open', figma: 'official', ai: 1, strength: 'Infrastructure tooling & cloud products' },
  { id: 'linear', name: 'Linear', company: 'Linear', url: 'https://linear.app', category: 'saas', stack: ['Tokens', 'React'], source: 'closed', ai: 0, strength: 'Speed-obsessed, keyboard-first product craft' },
  { id: 'lexicon', name: 'Lexicon', company: 'Liferay', url: 'https://design.liferay.com/lexicon', repo: gh('liferay/clay'), category: 'saas', stack: ['React', 'CSS-only'], source: 'open', strength: 'Digital-experience platforms' },
  { id: 'stacks', name: 'Stacks', company: 'Stack Overflow', url: 'https://stackoverflow.design', repo: gh('StackExchange/Stacks'), category: 'saas', stack: ['CSS-only'], source: 'open', strength: 'Atomic CSS for community products' },
  { id: 'seeds', name: 'Seeds', company: 'Sprout Social', url: 'https://seeds.sproutsocial.com', category: 'saas', stack: ['React'], source: 'hybrid', figma: 'official', strength: 'Social-media management & content voice' },
  { id: 'odyssey', name: 'Odyssey', company: 'Okta', url: 'https://odyssey-storybook.okta.design', repo: gh('okta/odyssey'), category: 'saas', stack: ['React'], source: 'open', figma: 'official', strength: 'Identity & security flows' },
  { id: 'hubspot-canvas', name: 'Canvas', company: 'HubSpot', url: 'https://canvas.hubspot.com', category: 'saas', stack: ['React'], source: 'hybrid', figma: 'official', strength: 'Marketing & CRM platform' },
  { id: 'kumo', name: 'Kumo', company: 'Cloudflare', url: 'https://kumo-ui.com', category: 'saas', stack: ['React', 'Tailwind'], source: 'open', figma: 'official', strength: 'Network & edge-platform dashboards' },
  { id: 'dropbox', name: 'Dropbox Design', company: 'Dropbox', url: 'https://dropbox.design', category: 'saas', stack: ['Tokens', 'React'], source: 'closed', ai: 0, strength: 'Brand-led product expression' },
  { id: 'asana', name: 'Asana Design', company: 'Asana', url: 'https://asana.design', category: 'saas', stack: ['React'], source: 'closed', strength: 'Work-management product design' },
  { id: 'mailchimp', name: 'Mailchimp Design', company: 'Mailchimp', url: 'https://mailchimp.com/design/', category: 'saas', stack: ['Tokens', 'React'], source: 'hybrid', ai: 0, strength: 'Voice & tone and expressive brand' },
  { id: 'wordpress', name: 'WordPress Components', company: 'WordPress / Automattic', url: 'https://developer.wordpress.org/block-editor/reference-guides/components/', repo: gh('WordPress/gutenberg'), category: 'saas', stack: ['React'], source: 'open', strength: 'Block-editor extensibility' },
  { id: 'smarthr', name: 'SmartHR Design System', company: 'SmartHR', url: 'https://smarthr.design', repo: gh('kufu/smarthr-ui'), category: 'saas', stack: ['React'], source: 'open', strength: 'HR SaaS with deep accessibility writing' },
  { id: 'shoreline', name: 'Shoreline', company: 'VTEX', url: 'https://shoreline.vtex.com', repo: gh('vtex/shoreline'), category: 'saas', stack: ['React'], source: 'open', strength: 'Commerce admin experiences' },
  { id: 'vtex-styleguide', name: 'VTEX Styleguide', company: 'VTEX', url: 'https://styleguide.vtex.com', repo: gh('vtex/styleguide'), category: 'saas', stack: ['React'], source: 'open', strength: 'Legacy commerce admin components' },
  { id: 'backstage', name: 'Backstage', company: 'Spotify', url: 'https://backstage.io', repo: gh('backstage/backstage'), category: 'saas', stack: ['React'], source: 'open', figma: 'official', strength: 'Developer portals (featured on designsystems.com)' },

  // ───────────── OS Platforms ─────────────
  {
    id: 'material', name: 'Material 3', company: 'Google', url: 'https://m3.material.io',
    repo: gh('material-components'), category: 'platform',
    stack: ['React', 'Web Components', 'Cross-platform', 'W3C Tokens'], source: 'open', figma: 'official', ai: 0,
    strength: 'Dynamic theming & cross-platform scale',
    why: 'The reference for algorithmic colour generation, elevation tokens and responsive motion.',
    featured: true,
  },
  {
    id: 'apple-hig', name: 'Human Interface Guidelines', company: 'Apple',
    url: 'https://developer.apple.com/design/human-interface-guidelines', repo: 'https://developer.apple.com/design/resources/',
    category: 'platform', stack: ['Cross-platform'], source: 'closed', figma: 'official', ai: 0,
    strength: 'Native spatial, mobile & desktop ergonomics',
    why: 'Essential reference for system-defined semantic colours, typography scales and platform conventions.',
    featured: true,
  },
  { id: 'acorn', name: 'Acorn', company: 'Mozilla / Firefox', url: 'https://acorn.firefox.com', category: 'platform', stack: [], source: 'hybrid', figma: 'official', strength: 'Browser chrome & product UI' },
  { id: 'wonder-blocks', name: 'Wonder Blocks', company: 'Khan Academy', url: 'https://khan.github.io/wonder-blocks/', repo: gh('Khan/wonder-blocks'), category: 'industry', stack: ['React'], source: 'open', strength: 'Education & learning products' },

  // ───────────── Consumer & Fintech ─────────────
  {
    id: 'blade', name: 'Blade', company: 'Razorpay', url: 'https://blade.razorpay.com',
    repo: gh('razorpay/blade'), category: 'consumer', stack: ['React', 'React Native', 'Tokens'], source: 'open',
    strength: 'Cross-platform React + React Native fintech',
    why: 'Built for multi-brand white-labelling, payment flows and banking dashboards.',
    featured: true,
  },
  {
    id: 'baseweb', name: 'Base Web', company: 'Uber', url: 'https://baseweb.design',
    repo: gh('uber/baseweb'), category: 'consumer', stack: ['React'], source: 'open',
    strength: 'High-contrast consumer & logistics UI',
    why: 'Dense mobile/web interfaces, map overlays and complex theming overrides.',
    featured: true,
  },
  {
    id: 'gestalt', name: 'Gestalt', company: 'Pinterest', url: 'https://gestalt.pinterest.systems',
    repo: gh('pinterest/gestalt'), category: 'consumer', stack: ['Tokens', 'React'], source: 'open', figma: 'official', ai: 0,
    strength: 'Consumer visual discovery',
    why: 'Media grids, RTL internationalisation and automated ESLint rules that enforce adoption.',
    featured: true,
  },
  {
    id: 'wise', name: 'Wise Design', company: 'Wise', url: 'https://wise.design',
    category: 'consumer', stack: ['React'], source: 'hybrid',
    strength: 'Fintech trust & global localisation',
    why: 'Expressive brand personality combined with strict financial clarity and multi-currency rules.',
    featured: true,
  },
  { id: 'stripe', name: 'Stripe Apps UI', company: 'Stripe', url: 'https://docs.stripe.com/stripe-apps/components', category: 'consumer', stack: ['Tokens', 'React'], source: 'closed', ai: 1, strength: 'Payments UI extension toolkit' },
  { id: 'square', name: 'Square Design', company: 'Square', url: 'https://design.squareup.com', category: 'consumer', stack: ['Tokens', 'React'], source: 'hybrid', ai: 0, strength: 'Point-of-sale & seller tools' },
  { id: 'visa', name: 'Visa Design System', company: 'Visa', url: 'https://design.visa.com', category: 'consumer', stack: ['Web Components'], source: 'open', strength: 'Payments brand at global scale' },
  { id: 'hsbc', name: 'HSBC Design', company: 'HSBC', url: 'https://create.hsbc', category: 'consumer', stack: [], source: 'closed', strength: 'Retail banking brand & product' },
  { id: 'airbnb', name: 'Airbnb Design', company: 'Airbnb', url: 'https://medium.com/airbnb-design', category: 'consumer', stack: ['Tokens', 'React'], source: 'hybrid', ai: 0, strength: 'Influential writing on systems thinking' },
  { id: 'duolingo', name: 'Duolingo Design', company: 'Duolingo', url: 'https://design.duolingo.com', category: 'consumer', stack: ['React'], source: 'closed', strength: 'Playful illustration & character systems' },
  { id: 'ebay', name: 'eBay Playbook', company: 'eBay', url: 'https://playbook.ebay.com/design-system', category: 'consumer', stack: ['Tokens', 'CSS-only'], source: 'hybrid', ai: 0, strength: 'Marketplace patterns & Skin CSS' },
  { id: 'alibaba', name: 'Alibaba Design', company: 'Alibaba', url: 'https://www.aliued.com', category: 'consumer', stack: ['React'], source: 'hybrid', strength: 'E-commerce at massive scale' },
  { id: 'fusion', name: 'Fusion Design', company: 'Alibaba', url: 'https://fusion.design', repo: gh('alibaba-fusion/next'), category: 'consumer', stack: ['React'], source: 'open', strength: 'Configurable middle-platform UI' },
  { id: 'rakuten', name: 'Rakuten Design', company: 'Rakuten', url: 'https://www.rakuten.design', category: 'consumer', stack: [], source: 'hybrid', strength: 'Multi-service ecosystem brand' },
  { id: 'line', name: 'LINE Design System', company: 'LINE', url: 'https://designsystem.line.me', category: 'consumer', stack: [], source: 'closed', strength: 'Messaging super-app' },
  { id: 'semi', name: 'Semi Design', company: 'ByteDance', url: 'https://semi.design', repo: gh('DouyinFE/semi-design'), category: 'consumer', stack: ['React'], source: 'open', strength: 'Design-to-code theming at ByteDance scale' },
  { id: 'tdesign', name: 'TDesign', company: 'Tencent', url: 'https://tdesign.tencent.com', repo: gh('Tencent/tdesign'), category: 'consumer', stack: ['Tokens', 'React', 'Vue'], source: 'open', strength: 'Multi-framework enterprise kit from Tencent' },
  { id: 'vant', name: 'Vant', company: 'Youzan', url: 'https://vant-ui.github.io/vant/', repo: gh('youzan/vant'), category: 'consumer', stack: ['Vue'], source: 'open', strength: 'Lightweight mobile commerce UI' },
  { id: 'spindle', name: 'Spindle', company: 'CyberAgent', url: 'https://spindle.ameba.design', category: 'consumer', stack: ['Tokens'], source: 'hybrid', strength: 'Media & blogging platform (Ameba)' },
  { id: 'mistica', name: 'Mística', company: 'Telefónica', url: 'https://brandfactory.telefonica.com/mistica', repo: gh('Telefonica/mistica-web'), category: 'consumer', stack: ['React', 'Cross-platform', 'Tokens Studio'], source: 'open', strength: 'Multi-brand telco white-labelling' },
  { id: 'scale', name: 'Scale', company: 'Deutsche Telekom', url: 'https://telekom.github.io/scale/', repo: gh('telekom/scale'), category: 'consumer', stack: ['Tokens', 'Web Components', 'React', 'Vue', 'Style Dictionary'], source: 'open', strength: 'Framework-agnostic telco components' },

  // ───────────── Industry & Brand ─────────────
  { id: 'audi', name: 'Audi UI', company: 'Audi', url: 'https://www.audi.com/ci/', category: 'industry', stack: ['Tokens', 'Web Components', 'Style Dictionary'], source: 'open', ai: 0, strength: 'Automotive brand & digital CI' },
  { id: 'porsche', name: 'Porsche Design System', company: 'Porsche', url: 'https://designsystem.porsche.com', repo: gh('porsche-design-system/porsche-design-system'), category: 'industry', stack: ['Web Components', 'React', 'Angular'], source: 'open', figma: 'official', strength: 'Premium automotive web' },
  { id: 'backpack', name: 'Backpack', company: 'Skyscanner', url: 'https://www.skyscanner.design', repo: gh('Skyscanner/backpack'), category: 'industry', stack: ['Tokens', 'React', 'Cross-platform'], source: 'open', figma: 'official', ai: 2, strength: 'Travel search across web, iOS & Android' },
  { id: 'orbit', name: 'Orbit', company: 'Kiwi.com', url: 'https://kiwicom.github.io/orbit/', repo: gh('kiwicom/orbit'), category: 'industry', stack: ['React'], source: 'open', figma: 'official', strength: 'Travel booking flows' },
  { id: 'priceline', name: 'Priceline One', company: 'Priceline', url: 'https://priceline.github.io/design-system/', repo: gh('priceline/design-system'), category: 'industry', stack: ['React'], source: 'open', strength: 'Travel deals & checkout' },
  { id: 'lyne', name: 'Lyne', company: 'SBB (Swiss Federal Railways)', url: 'https://digital.sbb.ch', repo: gh('sbb-design-systems/lyne-components'), category: 'industry', stack: ['Web Components', 'React'], source: 'open', strength: 'Public transport & ticketing' },
  { id: 'db-ux', name: 'DB UX Design System', company: 'Deutsche Bahn', url: 'https://design-system.deutschebahn.com', repo: gh('db-ux-design-system/core-web'), category: 'industry', stack: ['React', 'Angular', 'Vue'], source: 'open', strength: 'Rail mobility at national scale' },
  { id: 'cedar', name: 'Cedar', company: 'REI', url: 'https://cedar.rei.com', repo: gh('rei/rei-cedar'), category: 'industry', stack: ['Vue'], source: 'open', strength: 'Outdoor retail e-commerce' },
  { id: 'vitamin', name: 'Vitamin', company: 'Decathlon', url: 'https://www.decathlon.design', repo: gh('Decathlon/vitamin-web'), category: 'industry', stack: ['React', 'Vue', 'Svelte', 'Style Dictionary'], source: 'open', strength: 'Sports retail across frameworks' },
  { id: 'skapa', name: 'Skapa', company: 'IKEA', url: 'https://android.skapa.ikea.net', category: 'industry', stack: ['React', 'Cross-platform'], source: 'hybrid', strength: 'Home-furnishing retail' },
  { id: 'bbc-gel', name: 'GEL', company: 'BBC', url: 'https://bbc.github.io/gel/', repo: gh('bbc/gel'), category: 'industry', stack: ['Tokens', 'CSS-only'], source: 'open', ai: 0, strength: 'Accessible media & broadcasting' },
  { id: 'wapo', name: 'WPDS', company: 'The Washington Post', url: 'https://build.washingtonpost.com', category: 'industry', stack: ['React'], source: 'closed', strength: 'News publishing at speed' },
  { id: 'instructure', name: 'Instructure UI', company: 'Instructure (Canvas LMS)', url: 'https://instructure.design', repo: gh('instructure/instructure-ui'), category: 'industry', stack: ['React'], source: 'open', strength: 'Accessible learning-management UI' },
  { id: 'braid', name: 'Braid', company: 'SEEK', url: 'https://seek-oss.github.io/braid-design-system/', repo: gh('seek-oss/braid-design-system'), category: 'industry', stack: ['React'], source: 'open', strength: 'Themeable jobs-marketplace UI' },
  { id: 'nhs', name: 'NHS Design System', company: 'National Health Service', url: 'https://service-manual.nhs.uk/design-system', repo: gh('nhsuk/nhsuk-frontend'), category: 'public', stack: ['Tokens', 'CSS-only'], source: 'open', figma: 'official', ai: 1, strength: 'Health-service clarity backed by research' },
  { id: 'hopkins', name: 'Johns Hopkins Design Standards', company: 'Johns Hopkins Medicine', url: 'https://brand.hopkinsmedicine.org/brand/design-standards', category: 'industry', stack: [], source: 'hybrid', strength: 'Healthcare brand standards' },
  { id: 'yale', name: 'Yale Identity', company: 'Yale University', url: 'https://yaleidentity.yale.edu', category: 'industry', stack: [], source: 'hybrid', strength: 'Higher-education identity' },
  { id: 'berkeley', name: 'Berkeley Brand', company: 'UC Berkeley', url: 'https://brand.berkeley.edu', category: 'industry', stack: [], source: 'hybrid', strength: 'Higher-education identity' },
  { id: 'columbia', name: 'Columbia Design System', company: 'Columbia University', url: 'https://usability.cuit.columbia.edu/content/columbia-design-system', category: 'industry', stack: [], source: 'hybrid', strength: 'University web usability' },

  // ───────────── Public Sector & Radical Accessibility ─────────────
  {
    id: 'govuk', name: 'GOV.UK Design System', company: 'UK Government', url: 'https://design-system.service.gov.uk',
    repo: gh('alphagov/govuk-frontend'), category: 'public',
    stack: ['Tokens', 'CSS-only', 'Framework-agnostic'], source: 'open', figma: 'official', ai: 0,
    strength: 'Form usability & radical clarity',
    why: 'Every pattern is backed by public usability testing — the gold standard for accessible forms and error states.',
    featured: true,
  },
  {
    id: 'uswds', name: 'U.S. Web Design System', company: 'U.S. Government', url: 'https://designsystem.digital.gov',
    repo: gh('uswds/uswds'), category: 'public',
    stack: ['Tokens', 'CSS-only'], source: 'open', figma: 'official', ai: 0,
    strength: 'Section 508 compliance & public utility',
    why: 'Bulletproof accessibility, progressive enhancement and utility-driven tokens.',
    featured: true,
  },
  { id: 'canada-ca', name: 'Canada.ca Design System', company: 'Government of Canada', url: 'https://design.canada.ca', category: 'public', stack: ['CSS-only', 'Web Components'], source: 'open', strength: 'Bilingual federal web presence' },
  { id: 'gcds', name: 'GC Design System', company: 'Canadian Digital Service', url: 'https://design-system.canada.ca', repo: gh('cds-snc/gcds-components'), category: 'public', stack: ['Web Components'], source: 'open', strength: 'Bilingual web components for services' },
  { id: 'au-gold', name: 'GOLD Design System', company: 'Australian Government', url: 'https://gold.designsystemau.org', category: 'public', stack: ['CSS-only', 'Framework-agnostic'], source: 'open', strength: 'Community-maintained government kit' },
  { id: 'sgds', name: 'Singapore Government Design System', company: 'Singapore Government', url: 'https://www.designsystem.tech.gov.sg', category: 'public', stack: ['CSS-only'], source: 'open', strength: 'Smart-nation digital services' },
  { id: 'ec', name: 'Europa Component Library', company: 'European Commission', url: 'https://ec.europa.eu/component-library/ec/', category: 'public', stack: ['CSS-only'], source: 'open', strength: 'Multilingual EU institutions' },
  { id: 'bank-canada', name: 'Bank of Canada Design', company: 'Bank of Canada', url: 'https://design.bankofcanada.ca', category: 'public', stack: [], source: 'closed', strength: 'Central-bank communication' },
  { id: 'hds', name: 'Helsinki Design System', company: 'City of Helsinki', url: 'https://hds.hel.fi', repo: gh('City-of-Helsinki/helsinki-design-system'), category: 'public', stack: ['Web Components', 'React'], source: 'open', strength: 'City services with exemplary a11y docs' },
  { id: 'ontario', name: 'Ontario Design System', company: 'Government of Ontario', url: 'https://designsystem.ontario.ca', repo: gh('ongov/ontario-design-system'), category: 'public', stack: ['CSS-only'], source: 'open', strength: 'Provincial digital services' },
  { id: 'designsystemet', name: 'Designsystemet', company: 'Digdir (Norway)', url: 'https://designsystemet.no/en/', repo: gh('digdir/designsystemet'), category: 'public', stack: ['Tokens', 'CSS-only', 'Web Components', 'React', 'Tokens Studio'], source: 'open', figma: 'official', strength: 'Shared tokens for a whole nation' },
  { id: 'dkfds', name: 'DKFDS', company: 'Danish Government', url: 'https://designsystem.dk', category: 'public', stack: ['Tokens', 'CSS-only', 'Framework-agnostic'], source: 'open', strength: 'Danish public self-service' },
  { id: 'nl-ds', name: 'NL Design System', company: 'Dutch Ministry of the Interior', url: 'https://nldesignsystem.nl', category: 'public', stack: ['Tokens', 'Web Components', 'CSS-only', 'Style Dictionary'], source: 'open', strength: 'Multi-organisation themeable commons' },
  { id: 'nz-gov', name: 'NZ Government Design System', company: 'Dept. of Internal Affairs, NZ', url: 'https://design-system-alpha.digital.govt.nz', category: 'public', stack: ['Tokens', 'React', 'Vue', 'CSS-only'], source: 'open', strength: 'Emerging national standard (alpha)' },
  { id: 'poncho', name: 'Poncho', company: 'Government of Argentina', url: 'https://argob.github.io/poncho/', repo: gh('argob/poncho'), category: 'public', stack: ['Tokens'], source: 'open', strength: 'Latin-American government web' },
  { id: 'dads', name: 'Digital Agency Design System', company: 'Government of Japan', url: 'https://design.digital.go.jp/dads/', category: 'public', stack: [], source: 'open', strength: 'Japanese public-sector accessibility' },
  { id: 'nys', name: 'New York State Design System', company: 'New York State ITS', url: 'https://designsystem.ny.gov', category: 'public', stack: ['Web Components'], source: 'open', strength: 'State-level digital services' },

  // ───────────── Libraries, Frameworks & Primitives ─────────────
  { id: 'shadcn', name: 'shadcn/ui', company: 'shadcn', url: 'https://ui.shadcn.com', repo: gh('shadcn-ui/ui'), category: 'library', stack: ['React', 'Tailwind', 'W3C Tokens'], source: 'open', figma: 'community', ai: 3, strength: 'Copy-paste components you own', featured: true, why: 'Copies accessible source into your repo on Tailwind + Radix/Base UI — 100% control over token mapping.' },
  { id: 'radix', name: 'Radix Primitives', company: 'WorkOS', url: 'https://www.radix-ui.com/primitives', repo: gh('radix-ui/primitives'), category: 'library', stack: ['React'], source: 'open', figma: 'community', ai: 0, strength: 'Unstyled accessible primitives', featured: true, why: 'Focus management, keyboard navigation and ARIA handled out of the box.' },
  { id: 'base-ui', name: 'Base UI', company: 'MUI', url: 'https://base-ui.com', repo: gh('mui/base-ui'), category: 'library', stack: ['React'], source: 'open', strength: 'Headless components for CSS vars & Tailwind', featured: true, why: 'From the creators of Radix, Floating UI and Material UI.' },
  { id: 'react-aria', name: 'React Aria', company: 'Adobe', url: 'https://react-spectrum.adobe.com/react-aria/', repo: gh('adobe/react-spectrum'), category: 'library', stack: ['React'], source: 'open', strength: 'Headless a11y hooks with i18n', featured: true, why: 'Internationalised date/number pickers and screen-reader tested touch support.' },
  { id: 'mantine', name: 'Mantine', company: 'Mantine', url: 'https://mantine.dev', repo: gh('mantinedev/mantine'), category: 'library', stack: ['React'], source: 'open', figma: 'community', ai: 2, strength: '100+ themeable components & hooks', featured: true },
  { id: 'antd', name: 'Ant Design', company: 'Ant Group', url: 'https://ant.design', repo: gh('ant-design/ant-design'), category: 'library', stack: ['React', 'Vue'], source: 'open', figma: 'community', ai: 2, strength: 'Enterprise admin CRUD, fast', featured: true },
  { id: 'mui', name: 'Material UI', company: 'MUI', url: 'https://mui.com', repo: gh('mui/material-ui'), category: 'library', stack: ['React'], source: 'open', figma: 'official', ai: 2, strength: 'Most-used Material implementation for React' },
  { id: 'chakra', name: 'Chakra UI', company: 'Chakra UI', url: 'https://chakra-ui.com', repo: gh('chakra-ui/chakra-ui'), category: 'library', stack: ['React'], source: 'open', figma: 'official', ai: 2, strength: 'Style-props ergonomics & theming' },
  { id: 'heroui', name: 'HeroUI', company: 'HeroUI', url: 'https://heroui.com', repo: gh('heroui-inc/heroui'), category: 'library', stack: ['React', 'Tailwind'], source: 'open', strength: 'Beautiful Tailwind React components' },
  { id: 'radianui', name: 'RadianUI', company: 'Radian', url: 'https://radianui.com', category: 'library', stack: ['React', 'Tailwind'], source: 'open', figma: 'official', strength: 'Tailwind kit with matching Figma' },
  { id: 'ariakit', name: 'Ariakit', company: 'Ariakit', url: 'https://ariakit.org', repo: gh('ariakit/ariakit'), category: 'library', stack: ['React'], source: 'open', strength: 'Low-level accessible primitives' },
  { id: 'tailwind-plus', name: 'Tailwind Plus', company: 'Tailwind Labs', url: 'https://tailwindcss.com/plus', category: 'library', stack: ['Tokens', 'React', 'Vue', 'Tailwind'], source: 'closed', figma: 'official', ai: 0, strength: 'Premium Tailwind templates & UI blocks' },
  { id: 'bootstrap', name: 'Bootstrap', company: 'Bootstrap Team', url: 'https://getbootstrap.com', repo: gh('twbs/bootstrap'), category: 'library', stack: ['CSS-only', 'Framework-agnostic'], source: 'open', strength: 'The original responsive CSS framework' },
  { id: 'bulma', name: 'Bulma', company: 'Bulma Team', url: 'https://bulma.io', repo: gh('jgthms/bulma'), category: 'library', stack: ['CSS-only'], source: 'open', strength: 'Flexbox-first CSS framework' },
  { id: 'foundation', name: 'Foundation', company: 'ZURB', url: 'https://get.foundation', repo: gh('foundation/foundation-sites'), category: 'library', stack: ['CSS-only'], source: 'open', strength: 'Responsive front-end framework' },
  { id: 'semantic-ui', name: 'Semantic UI', company: 'Semantic UI', url: 'https://semantic-ui.com', repo: gh('Semantic-Org/Semantic-UI'), category: 'library', stack: ['CSS-only'], source: 'open', strength: 'Human-friendly HTML class naming' },
  { id: 'vuetify', name: 'Vuetify', company: 'Vuetify Team', url: 'https://vuetifyjs.com', repo: gh('vuetifyjs/vuetify'), category: 'library', stack: ['Vue'], source: 'open', strength: 'Material components for Vue' },
  { id: 'element-plus', name: 'Element Plus', company: 'Element Plus', url: 'https://element-plus.org', repo: gh('element-plus/element-plus'), category: 'library', stack: ['Vue'], source: 'open', strength: 'Vue 3 desktop admin components' },
  { id: 'naive-ui', name: 'Naive UI', company: 'TuSimple', url: 'https://www.naiveui.com', repo: gh('tusen-ai/naive-ui'), category: 'library', stack: ['Vue'], source: 'open', strength: 'Typed, themeable Vue 3 library' },
]

export const ALL_STACKS = Array.from(new Set(SYSTEMS.flatMap((s) => s.stack))).sort()
