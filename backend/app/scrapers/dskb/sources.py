"""Permanent seed-source register (S01–S20) and taxonomy definitions."""
from __future__ import annotations

from typing import Dict, List, Optional

SEEDS: List[Dict[str, str]] = [
    {"source_id": "S01", "name": "Design Systems Surf", "url": "https://designsystems.surf/", "source_type": "directory", "adapter": "surf"},
    {"source_id": "S02", "name": "Adele by UXPin", "url": "https://adele.uxpin.com/", "source_type": "directory", "adapter": "adele"},
    {"source_id": "S03", "name": "Design Systems Repo", "url": "https://designsystemsrepo.com/", "source_type": "directory", "adapter": "dsrepo"},
    {"source_id": "S04", "name": "Storybook Showcase", "url": "https://storybook.js.org/showcase", "source_type": "showcase", "adapter": "storybook"},
    {"source_id": "S05", "name": "Design Systems Directory", "url": "https://designsystems.directory/", "source_type": "directory", "adapter": "dsdir"},
    {"source_id": "S06", "name": "Awesome Design Systems (alexpate)", "url": "https://github.com/alexpate/awesome-design-systems", "source_type": "curated_repository", "adapter": "awesome"},
    {"source_id": "S07", "name": "Awesome Design Systems (klaufel)", "url": "https://github.com/klaufel/awesome-design-systems", "source_type": "curated_repository", "adapter": "awesome"},
    {"source_id": "S08", "name": "Design Systems (saadeghi)", "url": "https://github.com/saadeghi/design-systems", "source_type": "curated_repository", "adapter": "awesome"},
    {"source_id": "S09", "name": "Style Dictionary", "url": "https://github.com/amzn/style-dictionary", "source_type": "tool_repository", "adapter": "style_dictionary"},
    {"source_id": "S10", "name": "Design Tokens Community Group", "url": "https://github.com/design-tokens/community-group", "source_type": "specification_repository", "adapter": "dtcg"},
    {"source_id": "S11", "name": "shadcn/ui", "url": "https://ui.shadcn.com/", "source_type": "component_library", "adapter": "shadcn"},
    {"source_id": "S12", "name": "Radix UI Primitives", "url": "https://www.radix-ui.com/primitives", "source_type": "component_library", "adapter": "radix"},
    {"source_id": "S13", "name": "Base UI", "url": "https://base-ui.com/", "source_type": "component_library", "adapter": "baseui"},
    {"source_id": "S14", "name": "React Aria", "url": "https://react-spectrum.adobe.com/react-aria/", "source_type": "component_library", "adapter": "reactaria"},
    {"source_id": "S15", "name": "Mantine", "url": "https://mantine.dev/", "source_type": "component_library", "adapter": "mantine"},
    {"source_id": "S16", "name": "Ant Design", "url": "https://ant.design/", "source_type": "component_library", "adapter": "antd"},
    {"source_id": "S17", "name": "The Design System Guide: Resources", "url": "https://thedesignsystem.guide/resources", "source_type": "resource_guide", "adapter": "dsguide"},
    {"source_id": "S18", "name": "DesignSystems.com", "url": "https://www.designsystems.com/", "source_type": "publication", "adapter": "dscom"},
    {"source_id": "S19", "name": "Design System Checklist", "url": "https://github.com/ardeshireshghi/design-system-checklist", "source_type": "checklist_repository", "adapter": "checklist"},
    {"source_id": "S20", "name": "Design Systems One", "url": "https://www.designsystems.one/design-systems", "source_type": "directory", "adapter": "dsone"},
]

SEED_BY_ID = {s["source_id"]: s for s in SEEDS}

TAXONOMY: Dict[str, Dict[str, object]] = {
    "C01": {"name": "Design-System Strategy", "subs": ["vision", "alignment", "scope", "maturity", "adoption", "metrics", "roi", "team", "ownership", "decision-making", "roadmap", "prioritization"]},
    "C02": {"name": "Foundations", "subs": ["color", "typography", "spacing", "layout", "sizing", "responsive", "breakpoints", "radius", "borders", "elevation", "iconography", "illustration", "photography", "motion", "sound-haptics", "density", "z-index", "surfaces", "brand"]},
    "C03": {"name": "Design Tokens", "subs": ["primitive", "semantic", "component", "brand", "theme", "naming", "hierarchy", "aliases", "types", "groups", "validation", "versioning", "deprecation", "formats", "dtcg", "outputs", "sync", "design-tool", "ci", "governance"]},
    "C04": {"name": "Component Architecture", "subs": ["taxonomy", "anatomy", "composition", "slots", "props", "variants", "sizes", "states", "interaction", "controlled", "compound", "primitive", "styled", "recipes", "deprecation", "migration"]},
    "C05": {"name": "Component Catalog", "subs": []},
    "C06": {"name": "Patterns and Product Workflows", "subs": ["auth", "onboarding", "search", "filtering", "crud", "multi-step", "confirmation", "bulk", "dashboard", "errors", "loading", "empty-states"]},
    "C07": {"name": "Accessibility and Inclusive Design", "subs": ["wcag", "keyboard", "focus", "screen-readers", "semantics", "names", "contrast", "motion", "touch", "cognitive", "forms", "localization", "rtl", "testing"]},
    "C08": {"name": "Documentation and Governance", "subs": ["structure", "usage", "dos-donts", "status", "contribution", "rfcs", "ownership", "review", "release", "versioning", "changelog", "migration", "deprecation", "support", "feedback", "adoption"]},
    "C09": {"name": "Engineering and Tooling", "subs": ["frameworks", "typescript", "css", "tailwind", "headless", "storybook", "testing", "build", "publishing", "monorepo", "ci", "codegen", "figma", "docs-generation", "performance", "ssr", "i18n"]},
    "C10": {"name": "Theming and Brand Systems", "subs": ["multi-brand", "inheritance", "semantic-color", "switching", "dark-mode", "high-contrast", "density", "white-label", "runtime"]},
    "C11": {"name": "Cross-Platform Design Systems", "subs": ["web", "ios", "android", "desktop", "react-native", "parity", "portability"]},
    "C12": {"name": "Research and Comparative Analysis", "subs": ["comparison", "strengths", "limitations", "trade-offs", "recommendations"]},
    "C13": {"name": "AI-Ready Design-System Knowledge", "subs": ["machine-readable", "metadata", "retrieval", "ai-context", "mcp", "llms-txt", "provenance"]},
}

# Canonical component families. Aliases map source-native names (lowercased) to a family.
# Source-native names are always preserved on records; the family is an added, documented normalisation.
COMPONENT_FAMILIES: Dict[str, List[str]] = {
    "Button": ["button", "buttons", "action button", "icon button", "action icon", "actionicon", "close button", "closebutton", "unstyled button", "unstyledbutton", "float button", "floatbutton", "toggle button", "togglebutton"],
    "Button group": ["button group", "buttongroup", "toggle group", "togglegroup", "toggle button group", "togglebuttongroup", "segmented control", "segmentedcontrol", "segmented", "action group"],
    "Link": ["link", "links", "anchor"],
    "Text input": ["input", "text input", "textinput", "text field", "textfield", "text fields", "input text", "field", "number field", "numberfield", "number input", "numberinput", "inputnumber", "password input", "passwordinput", "input otp", "pin input", "pininput", "search field", "searchfield"],
    "Textarea": ["textarea", "text area", "text-area"],
    "Select": ["select", "native select", "nativeselect", "dropdown select", "picker"],
    "Combobox": ["combobox", "combo box", "autocomplete", "auto complete", "multiselect", "multi select", "tags input", "tagsinput", "cascader", "tree select", "treeselect", "mentions"],
    "Checkbox": ["checkbox", "checkboxes", "checkbox group", "checkboxgroup"],
    "Radio": ["radio", "radio button", "radio group", "radiogroup", "radio buttons"],
    "Switch": ["switch", "toggle", "toggle switch"],
    "Slider": ["slider", "range slider", "rangeslider", "range"],
    "Date & time picker": ["date picker", "datepicker", "date field", "datefield", "time picker", "timepicker", "time field", "timefield", "date range picker", "daterangepicker", "time input", "dateinput", "date input"],
    "Calendar": ["calendar", "range calendar", "rangecalendar", "month picker"],
    "Form": ["form", "forms", "field set", "fieldset", "form field", "label", "help text", "input wrapper", "inputwrapper"],
    "Card": ["card", "cards", "paper"],
    "Avatar": ["avatar", "avatars", "avatar group"],
    "Badge": ["badge", "badges", "indicator", "status"],
    "Tag": ["tag", "tags", "chip", "chips", "pill", "tag group", "taggroup"],
    "Tooltip": ["tooltip", "tooltips", "hover card", "hovercard", "preview card", "previewcard"],
    "Popover": ["popover", "popovers", "popconfirm", "toggletip"],
    "Menu": ["menu", "menus", "dropdown", "dropdown menu", "dropdownmenu", "context menu", "contextmenu", "menubar", "action list", "actionlist", "action menu"],
    "Dialog": ["dialog", "dialogs", "modal", "alert dialog", "alertdialog", "modals"],
    "Drawer / Sheet": ["drawer", "sheet", "side sheet", "bottom sheet", "sheets", "side panel"],
    "Alert": ["alert", "alerts", "alert banner", "banner", "inline message", "callout", "notice", "message bar"],
    "Toast / Notification": ["toast", "toasts", "notification", "notifications", "snackbar", "sonner"],
    "Tabs": ["tabs", "tab", "tab bar", "segmented tabs"],
    "Accordion": ["accordion", "accordions", "collapse", "collapsible", "disclosure", "disclosure group", "disclosuregroup", "expander", "details"],
    "Breadcrumbs": ["breadcrumbs", "breadcrumb"],
    "Pagination": ["pagination", "paginator"],
    "Navigation": ["navigation", "navigation bar", "navbar", "nav", "navigation menu", "navigationmenu", "app bar", "header", "top navigation", "sidebar", "side navigation", "navigation drawer", "nav link", "navlink", "steps", "stepper", "anchor nav", "tree view"],
    "Table / Data grid": ["table", "tables", "data table", "datatable", "data grid", "datagrid", "grid list", "gridlist"],
    "List": ["list", "lists", "list box", "listbox", "description list", "descriptions"],
    "Tree": ["tree", "tree view", "treeview"],
    "Search": ["search", "search bar", "searchbar", "spotlight", "command", "command palette", "commandpalette", "command menu"],
    "Progress": ["progress", "progress bar", "progressbar", "progress indicator", "progress circle", "ring progress", "ringprogress", "meter", "loader", "spinner", "loading indicator", "spin", "semicircle progress"],
    "Skeleton": ["skeleton", "skeletons", "skeleton loader"],
    "Empty state": ["empty state", "empty", "empty states", "zero state"],
    "Divider": ["divider", "separator", "dividers"],
    "Icon": ["icon", "icons", "theme icon", "themeicon"],
    "Image": ["image", "images", "background image", "backgroundimage", "aspect ratio", "aspectratio"],
    "Typography": ["typography", "text", "title", "heading", "highlight", "mark", "blockquote", "code", "kbd", "code snippet"],
    "Layout primitive": ["box", "flex", "grid", "simple grid", "simplegrid", "stack", "group", "container", "center", "space", "layout", "app shell", "appshell", "masonry", "splitter", "scroll area", "scrollarea"],
    "File upload": ["file upload", "upload", "file input", "fileinput", "drop zone", "dropzone", "file trigger", "filetrigger", "dropzone"],
    "Carousel": ["carousel", "carousels"],
    "Chart": ["chart", "charts", "data visualization", "sparkline"],
    "Color picker": ["color picker", "colorpicker", "color input", "colorinput", "color area", "colorarea", "color slider", "colorslider", "color wheel", "colorwheel", "color swatch", "colorswatch", "color field", "colorfield", "color swatch picker"],
    "Rating": ["rating", "rate"],
    "Timeline": ["timeline"],
    "Toolbar": ["toolbar", "action bar", "actionbar"],
    "Resizable panels": ["resizable", "resizable panels", "split panel", "split view"],
    "Portal / Overlay utility": ["portal", "overlay", "visually hidden", "visuallyhidden", "focus trap", "focustrap", "affix", "back top", "backtop", "transition", "collapse transition"],
}

ALIAS_TO_FAMILY: Dict[str, str] = {}
for fam, aliases in COMPONENT_FAMILIES.items():
    ALIAS_TO_FAMILY[fam.lower()] = fam
    for a in aliases:
        ALIAS_TO_FAMILY.setdefault(a.lower(), fam)

# Library-specific family overrides where a name means different things in different libraries.
LIB_FAMILY_OVERRIDES: Dict[str, Dict[str, Optional[str]]] = {
    "Ant Design": {"Message": "Toast / Notification", "Result": "Alert", "Space": "Layout primitive", "App": None},
    "shadcn/ui": {"Message": None, "Item": None, "Field": "Form"},
    "React Aria": {"Group": None},
}
