import { redirect } from 'next/navigation'

// The application is a private admin workspace; there is no public landing page.
export default function Root() {
  redirect('/platform')
}
