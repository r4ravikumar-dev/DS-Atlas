/** Site navigation, shared by the header (client) and footer (server). */
export const PRIMARY_NAV = [
  { href: '/systems', label: 'Design systems', match: ['/systems'] },
  { href: '/components', label: 'Components', match: ['/components'] },
  { href: '/tokens', label: 'Tokens', match: ['/tokens'] },
  { href: '/patterns', label: 'Patterns', match: ['/patterns'] },
  { href: '/playground', label: 'Playgrounds', match: ['/playground'] },
  { href: '/compare', label: 'Compare', match: ['/compare'] },
]
export const RESOURCES_NAV = [
  { href: '/storybook', label: 'Storybook showcases', hint: 'Public Storybooks, stories and extracted variants' },
  { href: '/about', label: 'Methodology', hint: 'Where the data comes from and how it is kept current' },
  { href: '/attribution', label: 'Attribution & IP', hint: 'Who owns the names, logos and assets shown here' },
]
