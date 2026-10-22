import { permanentRedirect } from 'next/navigation'

/** Guidelines and patterns are one library now, organised by design system and cross-system research. */
export default function GuidelinesIndex() {
  permanentRedirect('/patterns')
}
