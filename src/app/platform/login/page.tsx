'use client'

import { Suspense, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { ApiError } from '@/lib/api/client'
import { useLogin } from '@/features/auth/api'
import { Button, Field } from '@/components/ui'
import s from '@/components/platform/page.module.scss'

const EMAIL = /^\S+@\S+\.\S+$/

function LoginForm() {
  const router = useRouter()
  const next = useSearchParams().get('next')
  const login = useLogin()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [touched, setTouched] = useState(false)
  const emailErr = touched && !EMAIL.test(email) ? 'Enter a valid email address.' : undefined
  const pwErr = touched && !password ? 'Password is required.' : undefined
  // Only allow same-app relative redirects (prevents open redirects).
  const safeNext = next && next.startsWith('/platform') && !next.startsWith('//') ? next : '/platform'

  return (
    <form
      className={s.loginCard}
      onSubmit={(e) => {
        e.preventDefault()
        setTouched(true)
        if (!EMAIL.test(email) || !password) return
        login.mutate({ email, password }, { onSuccess: () => router.replace(safeNext) })
      }}
      noValidate
    >
      <div>
        <h1>Sign in</h1>
        <p>Design Systems Research Platform. Accounts are created by an administrator.</p>
      </div>
      <Field label="Email" error={emailErr}>
        <input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
      </Field>
      <Field label="Password" error={pwErr}>
        <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      </Field>
      {login.error && (
        <p role="alert" style={{ color: 'var(--coral)' }}>
          {login.error instanceof ApiError ? login.error.message : 'Sign-in failed.'}
        </p>
      )}
      <Button type="submit" variant="primary" loading={login.isPending}>
        Sign in
      </Button>
    </form>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  )
}
