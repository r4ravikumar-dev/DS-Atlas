# Design-System Comparative Analysis

_Generated 2026-10-21T09:52:33+00:00 from the canonical dataset (`design_systems_master.jsonl`). Every number below is computed from extracted records._

**Legend.** Values are **verified source facts** unless marked. `—` = *not documented in the inspected material*; **NI** = *not inspected*; **NA** = *not applicable*. Paragraphs labelled _Interpretation_ are analytical conclusions, not source statements.

## 1. Component libraries (S11–S16)

| Library | Type | Version inspected | Components | With API tables | Props documented | With keyboard tables | With a11y sections | With anatomy | Tokens extracted | Token delivery |
|---|---|---|---|---|---|---|---|---|---|---|
| [shadcn/ui](https://ui.shadcn.com/) | component_recipes (copy-in source) | 4.22.1 | 65 | 23 | 166 | 0 | 16 | 1 | 116 | CSS custom property |
| [Radix Primitives](https://www.radix-ui.com/primitives) | headless_primitives | 1.8.1 | 35 | 34 | 656 | 22 | 29 | 35 | 0 | NA (unstyled) |
| [Base UI](https://base-ui.com/) | headless_primitives | 1.9.0 | 37 | 37 | 1582 | 0 | 17 | 37 | 0 | NA (unstyled) |
| [React Aria](https://react-spectrum.adobe.com/react-aria/) | headless_components_and_hooks | 1.22.1 | 60 | 58 | 12052 | 0 | 10 | 0 | 0 | NA (unstyled) |
| [Mantine](https://mantine.dev/) | styled_component_library | 9.7.3 | 180 | 172 | 5391 | 2 | 69 | 0 | 482 | CSS custom property |
| [Ant Design](https://ant.design/) | styled_enterprise_design_system | 6.6.7 | 72 | 72 | 2219 | 0 | 13 | 0 | 820 | antd token-meta.json (published package) |

_Interpretation:_ Radix, Base UI and React Aria are **headless** — they ship behaviour, state and accessibility without visual styles, so a token count of zero is *not applicable* rather than a gap. shadcn/ui is a **recipe layer** (copied source on top of Radix or Base UI) whose tokens are CSS custom properties; Mantine and Ant Design are **styled systems** with their own token models (CSS variables vs. a seed/map/alias token algorithm). API and keyboard-table counts reflect how each project *documents* behaviour, not whether the behaviour exists (e.g. React Aria documents keyboard behaviour mostly in prose).

## 2. Component family coverage

Families are a documented normalisation (`sources.py: COMPONENT_FAMILIES`); source-native names are shown in each cell.

| Family | shadcn/ui | Radix Primitives | Base UI | React Aria | Mantine | Ant Design |
|---|---|---|---|---|---|---|
| Accordion | Accordion, Collapsible | Accordion, Collapsible | Accordion, Collapsible | Disclosure, DisclosureGroup | Accordion, Collapse | Collapse |
| Button group | Button Group, Toggle Group | Toggle Group | Toggle Group | ToggleButtonGroup | SegmentedControl | Segmented |
| Checkbox | Checkbox | Checkbox | Checkbox, Checkbox Group | Checkbox, CheckboxGroup | Checkbox | Checkbox |
| Dialog | Alert Dialog, Dialog | Alert Dialog, Dialog | Alert Dialog, Dialog | Modal | Dialog, Modal | Modal |
| Divider | Separator | Separator | Separator | Separator | Divider | Divider |
| Form | Field, Form, Label | Form, Label | Fieldset, Form | Form | Fieldset | Form |
| Menu | Context Menu, Dropdown Menu, Menubar | Context Menu, Dropdown Menu, Menubar | Context Menu, Menu, Menubar | Menu | Menu, Menubar | Dropdown, Menu |
| Popover | Popover | Popover | Popover | Popover | Popover | Popconfirm, Popover |
| Progress | Progress, Spinner | Progress | Meter, Progress | Meter, ProgressBar | Loader, Progress, RingProgress | Progress, Spin |
| Radio | Radio Group | Radio Group | Radio Group | RadioGroup | Radio | Radio |
| Select | Native Select, Select | Select | Select | Select | NativeSelect, Select | Select |
| Slider | Slider | Slider | Slider | Slider | RangeSlider, Slider | Slider |
| Switch | Switch, Toggle | Switch, Toggle | Switch, Toggle | Switch | Switch, Toggle | Switch |
| Tabs | Tabs | Tabs | Tabs | Tabs | Tabs | Tabs |
| Toast / Notification | Sonner, Toast | Toast | Toast | Toast | Notification | Message, Notification |
| Tooltip | Hover Card, Tooltip | Hover Card, Tooltip | Preview Card, Tooltip | Tooltip | HoverCard, Tooltip | Tooltip |
| Avatar | Avatar | Avatar | Avatar | — | Avatar | Avatar |
| Button | Button | — | Button | Button, ToggleButton | ActionIcon, Button, CloseButton, UnstyledButton | Button, FloatButton |
| Combobox | Combobox | — | Autocomplete, Combobox | Autocomplete, ComboBox | Autocomplete, Cascader, Combobox, MultiSelect | AutoComplete, Cascader, Mentions, TreeSelect |
| Drawer / Sheet | Drawer, Sheet | — | Drawer | Sheet | Drawer | Drawer |
| Layout primitive | Scroll Area | Scroll Area | Scroll Area | — | AppShell, Box, Center, Container | Flex, Grid, Layout, Masonry |
| Navigation | Navigation Menu, Sidebar | Navigation Menu | Navigation Menu | — | NavLink, Stepper | Steps |
| Text input | Input, Input OTP | — | Field, Input, Number Field | NumberField, SearchField, TextField | Input, NumberInput, PasswordInput, PinInput | Input, InputNumber |
| Breadcrumbs | Breadcrumb | — | — | Breadcrumbs | Breadcrumbs | Breadcrumb |
| Calendar | Calendar | — | — | Calendar, RangeCalendar | Calendar, MonthPicker | Calendar |
| Image | Aspect Ratio | Aspect Ratio | — | — | AspectRatio, BackgroundImage, Image | Image |
| Portal / Overlay utility | — | Portal, Visually Hidden | — | VisuallyHidden | Affix, FocusTrap, Overlay, Portal | Affix |
| Table / Data grid | Table | — | — | GridList, Table | Table | Table |
| Toolbar | — | Toolbar | Toolbar | Toolbar | ActionBar, Toolbar | — |
| Alert | Alert | — | — | — | Alert | Alert, Result |
| Badge | Badge | — | — | — | Badge, Indicator | Badge |
| Card | Card | — | — | — | Card, Paper | Card |
| Carousel | Carousel | — | — | — | Carousel | Carousel |
| Color picker | — | — | — | ColorArea, ColorField, ColorPicker, ColorSlider | ColorInput, ColorPicker, ColorSwatch | ColorPicker |
| Date & time picker | — | — | — | DateField, DatePicker, DateRangePicker, TimeField | DateInput, DatePicker, TimeInput, TimePicker | DatePicker, TimePicker |
| Empty state | Empty | — | — | — | EmptyState | Empty |
| File upload | — | — | — | DropZone, FileTrigger | Dropzone, FileInput | Upload |
| Link | — | — | — | Link | Anchor | Anchor |
| List | — | — | — | ListBox | List | Descriptions, List |
| Pagination | Pagination | — | — | — | Pagination | Pagination |
| Skeleton | Skeleton | — | — | — | Skeleton | Skeleton |
| Tag | — | — | — | TagGroup | Chip, Pill | Tag |
| Tree | — | — | — | Tree | Tree | Tree |
| Typography | Kbd | — | — | — | Blockquote, Code, Highlight, Kbd | Typography |
| Chart | Chart | — | — | — | Sparkline | — |
| Icon | — | — | — | — | ThemeIcon | Icon |
| Rating | — | — | — | — | Rating | Rate |
| Search | Command | — | — | — | Spotlight | — |
| Textarea | Textarea | — | — | — | Textarea | — |
| Timeline | — | — | — | — | Timeline | Timeline |
| Resizable panels | Resizable | — | — | — | — | — |

## 3. API patterns: controlled state & change handlers

Extracted from documented props. Shows how each library names the *controlled value* and its *change callback* for the same component family.

### Dialog

| Library | Components | State props | Change handlers |
|---|---|---|---|
| shadcn/ui | Alert Dialog, Dialog | — | — |
| Radix Primitives | Alert Dialog, Dialog | `defaultOpen`, `open` | `onOpenChange` |
| Base UI | Alert Dialog, Dialog | `defaultOpen`, `isOpen`, `open` | `onOpenChange`, `onOpenChangeComplete` |
| React Aria | Modal | `defaultOpen`, `isOpen` | `onOpenChange` |
| Mantine | Dialog, Modal | `opened` | `onClose` |
| Ant Design | Modal | `open` | `onCancel`, `onClose`, `onOk` |

### Tabs

| Library | Components | State props | Change handlers |
|---|---|---|---|
| shadcn/ui | Tabs | — | — |
| Radix Primitives | Tabs | `defaultValue`, `value` | `onValueChange` |
| Base UI | Tabs | `defaultValue`, `value` | `onValueChange` |
| React Aria | Tabs | `defaultSelectedKey`, `selectedKey` | `onSelectionChange` |
| Mantine | Tabs | `defaultValue`, `value` | `onChange` |
| Ant Design | Tabs | `activeKey`, `defaultActiveKey` | `onChange` |

### Checkbox

| Library | Components | State props | Change handlers |
|---|---|---|---|
| shadcn/ui | Checkbox | — | — |
| Radix Primitives | Checkbox | `checked`, `defaultChecked`, `value` | `onCheckedChange` |
| Base UI | Checkbox, Checkbox Group | `checked`, `defaultChecked`, `defaultValue`, `value` | `onCheckedChange`, `onValueChange` |
| React Aria | Checkbox, CheckboxGroup | `defaultSelected`, `defaultValue`, `isSelected`, `value` | `onChange` |
| Mantine | Checkbox | `checked`, `defaultChecked`, `value` | `onChange` |
| Ant Design | Checkbox | `checked`, `defaultChecked`, `defaultValue`, `value` | `onChange` |

### Select

| Library | Components | State props | Change handlers |
|---|---|---|---|
| shadcn/ui | Native Select, Select | `value` | — |
| Radix Primitives | Select | `defaultOpen`, `defaultValue`, `open`, `value` | `onOpenChange`, `onValueChange` |
| Base UI | Select | `defaultOpen`, `defaultValue`, `open`, `value` | `onOpenChange`, `onOpenChangeComplete`, `onValueChange` |
| React Aria | Select | `defaultChecked`, `defaultOpen`, `defaultValue`, `isOpen`, `value` | `onChange`, `onOpenChange`, `onSelect` |
| Mantine | NativeSelect, Select | `defaultValue`, `value` | `onChange`, `onSearchChange` |
| Ant Design | Select | `defaultOpen`, `defaultValue`, `open`, `value` | `onChange`, `onOpenChange`, `onSelect` |

### Switch

| Library | Components | State props | Change handlers |
|---|---|---|---|
| shadcn/ui | Switch, Toggle | — | — |
| Radix Primitives | Switch, Toggle | `checked`, `defaultChecked`, `defaultPressed`, `pressed`, `value` | `onCheckedChange`, `onPressedChange` |
| Base UI | Switch, Toggle | `checked`, `defaultChecked`, `defaultPressed`, `pressed`, `value` | `onCheckedChange`, `onPressedChange` |
| React Aria | Switch | `defaultSelected`, `isSelected`, `value` | `onChange` |
| Mantine | Switch, Toggle | — | `onActiveChange` |
| Ant Design | Switch | `checked`, `defaultChecked`, `defaultValue`, `value` | `onChange` |

### Accordion

| Library | Components | State props | Change handlers |
|---|---|---|---|
| shadcn/ui | Accordion, Collapsible | — | — |
| Radix Primitives | Accordion, Collapsible | `defaultOpen`, `defaultValue`, `open`, `value` | `onOpenChange`, `onValueChange` |
| Base UI | Accordion, Collapsible | `defaultOpen`, `defaultValue`, `open`, `value` | `onOpenChange`, `onValueChange` |
| React Aria | Disclosure, DisclosureGroup | `defaultExpanded`, `defaultExpandedKeys`, `expandedKeys` | `onExpandedChange` |
| Mantine | Accordion, Collapse | `defaultValue`, `expanded`, `value` | `onChange` |
| Ant Design | Collapse | `activeKey`, `defaultActiveKey` | `onChange` |

### Slider

| Library | Components | State props | Change handlers |
|---|---|---|---|
| shadcn/ui | Slider | — | — |
| Radix Primitives | Slider | `defaultValue`, `value` | `onValueChange` |
| Base UI | Slider | `defaultValue`, `value` | `onValueChange` |
| React Aria | Slider | `defaultValue`, `value` | `onChange` |
| Mantine | RangeSlider, Slider | `defaultValue`, `value` | `onChange` |
| Ant Design | Slider | `defaultValue`, `open`, `value` | `onChange` |

### Combobox

| Library | Components | State props | Change handlers |
|---|---|---|---|
| shadcn/ui | Combobox | — | — |
| Radix Primitives | — | — | — |
| Base UI | Autocomplete, Combobox | `defaultOpen`, `defaultValue`, `open`, `value` | `onInputValueChange`, `onOpenChange`, `onOpenChangeComplete`, `onValueChange` |
| React Aria | Autocomplete, ComboBox | `defaultChecked`, `defaultValue`, `value` | `onChange`, `onInputChange`, `onOpenChange`, `onSelect` |
| Mantine | Autocomplete, Cascader, Combobox, MultiSelect, TagsInput, TreeSelect | `defaultValue`, `selected`, `value` | `onChange`, `onClose`, `onExpandedChange`, `onSearchChange` |
| Ant Design | AutoComplete, Cascader, Mentions, TreeSelect | `defaultOpen`, `defaultValue`, `open`, `value` | `onChange`, `onOpenChange`, `onSelect` |

_Interpretation:_ Within each library, controlled/uncontrolled pairs are consistent (`value`/`defaultValue` + a change callback), but conventions differ across libraries. Dialog, from the extracted props — shadcn/ui: props not documented on the component page; Radix Primitives: `defaultOpen`, `open`, `onOpenChange`; Base UI: `defaultOpen`, `isOpen`, `open`, `onOpenChange`, `onOpenChangeComplete`; React Aria: `defaultOpen`, `isOpen`, `onOpenChange`; Mantine: `opened`, `onClose`; Ant Design: `open`, `onCancel`, `onClose`, `onOk`. React Aria prefixes booleans with `is…` and uses key-based selection; Ant Design uses `activeKey` for tabs/collapse. shadcn/ui component pages rarely carry prop tables because props pass through to the underlying Radix/Base UI primitive. React Aria's API tables include inherited DOM/ARIA props, which inflates its prop count. A design system wrapping several libraries should pick one convention and adapt at the boundary.

## 4. Design-system registry coverage across directories

| Independent sources listing the system | Systems |
|---|---|
| 1 | 374 |
| 2 | 69 |
| 3 | 35 |
| 4 | 13 |
| 5 | 7 |
| 6 | 3 |
| 7 | 8 |
| 8 | 1 |

Most widely referenced systems (by number of seed sources whose records resolved to the same entity):

| System | Organization | Sources | Docs | Repository | Verification |
|---|---|---|---|---|---|
| Carbon | IBM | S01, S02, S03, S04, S06, S07, S08, S20 | https://www.carbondesignsystem.com/ | https://github.com/ibm/carbon-components | partially_verified |
| Ant Design | Ant Group | S01, S02, S03, S06, S08, S16, S20 | https://ant.design/ | https://github.com/ant-design/ant-design/ | verified |
| Atlassian Design System | Atlassian | S01, S02, S03, S06, S07, S08, S20 | https://atlassian.design/ | https://bitbucket.org/atlassian/atlassian-frontend-mirror/ | partially_verified |
| Canvas | Workday | S01, S02, S03, S04, S06, S08, S20 | https://canvas.workday.com/ | https://github.com/Workday/canvas-kit | partially_verified |
| Fluent UI | Microsoft | S01, S02, S03, S04, S06, S08, S20 | https://fluent2.microsoft.design/ | https://github.com/microsoft/fluentui | partially_verified |
| LeafyGreen UI | MongoDB | S01, S02, S03, S04, S06, S08, S20 | https://www.mongodb.design/ | https://github.com/mongodb/leafygreen-ui | partially_verified |
| Pajamas | GitLab | S01, S02, S03, S06, S07, S08, S20 | https://design.gitlab.com/ | https://gitlab.com/gitlab-org/design.gitlab.com | partially_verified |
| Polaris | Shopify | S01, S02, S03, S06, S07, S08, S20 | https://polaris.shopify.com/ | https://github.com/Shopify/polaris | partially_verified |
| Primer | GitHub | S01, S02, S04, S06, S07, S08, S20 | https://primer.style/ | https://github.com/primer/ | partially_verified |
| Lightning Design System | Salesforce | S01, S02, S03, S06, S08, S20 | https://www.lightningdesignsystem.com/ | https://github.com/salesforce-ux/design-system | partially_verified |
| Material 3 | Google | S01, S03, S06, S07, S08, S20 | https://m3.material.io/ | https://github.com/material-components/material-components | partially_verified |
| U.S. Web Design System | U.S. Government | S01, S02, S03, S06, S08, S20 | https://designsystem.digital.gov/ | https://github.com/uswds/uswds | partially_verified |
| Apple Human Interface Guidelines | Apple | S01, S03, S06, S08, S20 | https://developer.apple.com/design/human-interface-guidelines/ | — | partially_verified |
| Cedar | Rei | S01, S02, S03, S06, S08 | https://cedar.rei.com/ | https://github.com/rei/rei-cedar | partially_verified |
| Duet | LocalTapiola | S01, S02, S03, S06, S08 | https://www.duetds.com/ | https://github.com/duetds | partially_verified |
| Garden | Zendesk | S01, S02, S03, S06, S08 | https://garden.zendesk.com/ | https://github.com/zendeskgarden | partially_verified |
| GOV.UK Design System | UK Government | S01, S02, S03, S06, S20 | https://design-system.service.gov.uk/ | https://github.com/alphagov/govuk-design-system | partially_verified |
| Paste | Twilio | S01, S02, S06, S08, S20 | https://paste.twilio.design/ | https://github.com/twilio-labs/paste | partially_verified |
| Spectrum | Adobe | S01, S03, S06, S08, S20 | https://spectrum.adobe.com/ | https://github.com/adobe/react-spectrum | partially_verified |
| Audi UI | Audi | S02, S03, S08, S20 | https://www.audi.com/ci/ | https://github.com/audi/audi-ui | partially_verified |
| Cloudscape | Amazon Web Services | S01, S06, S08, S20 | https://cloudscape.design/ | https://github.com/cloudscape-design/components | partially_verified |
| Design System | BBC | S01, S02, S03, S06 | https://www.bbc.co.uk/gel | https://github.com/bbc/gel | partially_verified |
| Design System | Elastic | S01, S03, S06, S08 | https://elastic.github.io/eui/#/ | https://github.com/elastic/eui | partially_verified |
| Design System | Pluralsight | S01, S02, S03, S06 | https://design-system.pluralsight.com/ | https://github.com/pluralsight/design-system | partially_verified |
| Evergreen | Segment | S01, S03, S06, S08 | https://evergreen.segment.com/ | https://github.com/segmentio/evergreen | partially_verified |
| Geist | Vercel | S01, S06, S08, S20 | https://vercel.com/geist | https://github.com/vercel/geist-font | partially_verified |
| Orbit | Kiwicom | S01, S03, S04, S08 | https://orbit.kiwi/ | https://github.com/kiwicom/orbit | partially_verified |
| PatternFly | Red Hat | S01, S02, S03, S20 | https://www.patternfly.org/ | https://github.com/patternfly | partially_verified |
| Protocol | Mozilla | S01, S02, S03, S06 | https://protocol.mozilla.org/ | https://github.com/mozilla/protocol | partially_verified |
| Radix Primitives | WorkOS | S01, S06, S12, S20 | https://www.radix-ui.com/primitives | https://github.com/radix-ui | verified |

## 5. Documentation-attribute prevalence (Adele audit, S02)

Share of Adele rows reporting a non-empty, non-'no' value. These are Adele's claims, not re-verified.

| Attribute | Rows with value | 'yes' or specific value | % of rows |
|---|---|---|---|
| components | 103 | 100 | 97% |
| typescript | 103 | 21 | 20% |
| web components | 103 | 9 | 9% |
| tests | 103 | 58 | 56% |
| design tokens | 103 | 29 | 28% |
| storybook | 103 | 25 | 24% |
| accessibility guidelines | 103 | 39 | 38% |
| voice & tone | 103 | 36 | 35% |
| design principles | 103 | 43 | 42% |
| UI kit | 103 | 45 | 44% |
| code documentation | 103 | 78 | 76% |

## 6. AI-readiness signals (DesignSystems.one Agent-Ready Index, S20, CC BY 4.0)

| Signal | yes | partial | no / other |
|---|---|---|---|
| MCP server | 12 | 0 | 25 |
| llms.txt | 10 | 0 | 27 |
| DTCG tokens | 6 | 0 | 31 |
| Component registry | 1 | 0 | 36 |
| Figma Code Connect | 3 | 0 | 34 |

## 7. Limitations of this comparison

- Library facts come from official documentation at the versions listed; behaviour that is implemented but undocumented is reported as `—`.
- Directory-derived system attributes are third-party claims and are not independently verified unless the system is one of S11–S16.
- No numerical ranking is produced: the evidence does not support a weighting that is valid across product contexts.
