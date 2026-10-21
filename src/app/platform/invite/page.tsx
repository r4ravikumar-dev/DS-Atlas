'use client'

import { Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { CheckCircle2, ShieldAlert } from 'lucide-react'
import { ApiError } from '@/lib/api/client'
import {
  useAcceptInvitation,
  useSendInvitationCode,
  useValidateInvitation,
} from '@/features/invitations/api'
import { Button, Field, fmtDate, Skeleton, Tag } from '@/components/ui'
import s from '@/components/platform/page.module.scss'

function InviteFlow() {
  const router = useRouter()
  const validate = useValidateInvitation()
  const sendCode = useSendInvitationCode()
  const accept = useAcceptInvitation()

  const [token, setToken] = useState<string | null>(null)
  const [initChecked, setInitChecked] = useState(false)
  const [codeSent, setCodeSent] = useState(false)
  const [code, setCode] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [formErr, setFormErr] = useState<string | null>(null)

  useEffect(() => {
    // Read token from fragment #token=... or fallback ?token=...
    let tok: string | null = null
    if (typeof window !== 'undefined') {
      const hash = window.location.hash.replace(/^#/, '')
      const hashParams = new URLSearchParams(hash)
      tok = hashParams.get('token')
      if (!tok) {
        const queryParams = new URLSearchParams(window.location.search)
        tok = queryParams.get('token')
      }
    }
    setToken(tok)
    setInitChecked(true)

    if (tok) {
      validate.mutate({ token: tok })
    }
  }, [])

  if (!initChecked) {
    return (
      <div className={s.loginCard}>
        <Skeleton h={220} />
      </div>
    )
  }

  if (!token) {
    return (
      <div className={s.loginCard}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--coral)' }}>
          <ShieldAlert size={28} />
          <h1 style={{ margin: 0, fontSize: '1.25rem' }}>Missing Invitation Token</h1>
        </div>
        <p className={s.muted} style={{ marginTop: 12 }}>
          An invitation token is required in the link fragment. Please check the invitation link sent to your email.
        </p>
        <Link href="/platform/login">
          <Button variant="primary" style={{ width: '100%', marginTop: 16 }}>Return to Sign In</Button>
        </Link>
      </div>
    )
  }

  if (validate.isPending) {
    return (
      <div className={s.loginCard}>
        <h1>Validating invitation…</h1>
        <p className={s.muted}>Verifying cryptographic signature and expiration status.</p>
        <div style={{ marginTop: 16 }}><Skeleton h={100} /></div>
      </div>
    )
  }

  if (validate.error) {
    const msg = validate.error instanceof ApiError ? validate.error.message : 'Invalid or expired invitation.'
    return (
      <div className={s.loginCard}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--coral)' }}>
          <ShieldAlert size={28} />
          <h1 style={{ margin: 0, fontSize: '1.25rem' }}>Invitation Unavailable</h1>
        </div>
        <p style={{ marginTop: 12, color: 'var(--fg)' }}>{msg}</p>
        <p className={s.muted} style={{ fontSize: '0.84rem' }}>
          This invitation may have already been accepted, revoked, or expired. Contact your platform administrator for a new invitation.
        </p>
        <Link href="/platform/login">
          <Button variant="ghost" style={{ width: '100%', marginTop: 16 }}>Return to Sign In</Button>
        </Link>
      </div>
    )
  }

  const inv = validate.data?.data
  if (!inv) return null

  const handleSendCode = () => {
    setFormErr(null)
    sendCode.mutate({ token }, {
      onSuccess: () => {
        setCodeSent(true)
      },
    })
  }

  const handleAccept = (e: React.FormEvent) => {
    e.preventDefault()
    setFormErr(null)

    if (code.trim().length !== 6) {
      setFormErr('Verification code must be exactly 6 digits.')
      return
    }
    if (password.length < 12) {
      setFormErr('Password must be at least 12 characters long.')
      return
    }
    if (password !== confirmPassword) {
      setFormErr('Passwords do not match.')
      return
    }

    accept.mutate(
      {
        token,
        code: code.trim(),
        name: fullName.trim() || 'Invited User',
        password,
      },
      {
        onSuccess: () => {
          router.replace('/platform')
        },
      }
    )
  }

  const effectiveCodeSent = codeSent || inv.email_delivery

  return (
    <div className={s.loginCard}>
      <div>
        <div className={s.row} style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ margin: 0 }}>Accept Invitation</h1>
          <Tag tone="accent">{inv.role}</Tag>
        </div>
        <p className={s.muted} style={{ marginTop: 6, fontSize: '0.88rem' }}>
          Design Systems Research Platform private access for <strong>{inv.email_hint}</strong>.
        </p>
      </div>

      <div style={{ background: 'var(--surface-hover)', borderRadius: 6, padding: '10px 14px', fontSize: '0.82rem', display: 'grid', gap: 4 }}>
        <div className={s.row} style={{ justifyContent: 'space-between' }}>
          <span className={s.muted}>Authorized Email:</span>
          <strong>{inv.email_hint}</strong>
        </div>
        <div className={s.row} style={{ justifyContent: 'space-between' }}>
          <span className={s.muted}>Expires:</span>
          <span>{fmtDate(inv.expires_at)}</span>
        </div>
      </div>

      {!effectiveCodeSent ? (
        <div style={{ display: 'grid', gap: 14, marginTop: 8 }}>
          <p style={{ fontSize: '0.86rem' }}>
            To verify email ownership, we will send a 6-digit one-time verification code to <strong>{inv.email_hint}</strong>.
          </p>
          {sendCode.error && (
            <p role="alert" style={{ color: 'var(--coral)', fontSize: '0.84rem' }}>
              {sendCode.error instanceof ApiError ? sendCode.error.message : 'Failed to send code.'}
            </p>
          )}
          <Button
            type="button"
            variant="primary"
            loading={sendCode.isPending}
            onClick={handleSendCode}
          >
            Send Verification Code
          </Button>
        </div>
      ) : (
        <form onSubmit={handleAccept} style={{ display: 'grid', gap: 12, marginTop: 6 }} noValidate>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--mint)', fontSize: '0.84rem' }}>
            <CheckCircle2 size={16} />
            <span>Verification code sent to {inv.email_hint}</span>
          </div>

          <Field label="6-Digit Verification Code" hint="Check your inbox or development outbox. Code expires in 10 minutes.">
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="123456"
              style={{ fontFamily: 'var(--font-mono)', letterSpacing: '0.2em', fontSize: '1.1rem' }}
              required
            />
          </Field>

          <Field label="Full Name">
            <input
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Jane Doe"
            />
          </Field>

          <Field label="Create Password" hint="At least 12 characters.">
            <input
              type="password"
              autoComplete="new-password"
              minLength={12}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </Field>

          <Field label="Confirm Password">
            <input
              type="password"
              autoComplete="new-password"
              minLength={12}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </Field>

          {formErr && (
            <p role="alert" style={{ color: 'var(--coral)', fontSize: '0.84rem' }}>
              {formErr}
            </p>
          )}

          {accept.error && (
            <p role="alert" style={{ color: 'var(--coral)', fontSize: '0.84rem' }}>
              {accept.error instanceof ApiError ? accept.error.message : 'Acceptance failed.'}
            </p>
          )}

          <div className={s.row} style={{ justifyContent: 'space-between', alignItems: 'center', marginTop: 6 }}>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              loading={sendCode.isPending}
              onClick={handleSendCode}
            >
              Resend Code
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={accept.isPending}
            >
              Complete Registration
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}

export default function InvitePage() {
  return (
    <Suspense fallback={<div className={s.loginCard}><Skeleton h={220} /></div>}>
      <InviteFlow />
    </Suspense>
  )
}
