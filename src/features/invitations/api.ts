'use client'

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, type Query } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type {
  Invitation,
  InvitationAcceptRequest,
  InvitationCreate,
  InvitationSendCodeRequest,
  InvitationValidateOut,
  InvitationValidateRequest,
  Item,
  Page,
  Session,
} from '@/lib/api/types'

export function useInvitations(q?: Query) {
  return useQuery({
    queryKey: qk.invitations(q),
    queryFn: ({ signal }) => api<Page<Invitation>>('/admin/invitations', { query: q, signal }),
    placeholderData: keepPreviousData,
  })
}

export function useCreateInvitation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: InvitationCreate) => api<Item<Invitation>>('/admin/invitations', { method: 'POST', body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invitations'] })
      qc.invalidateQueries({ queryKey: qk.admin('audit') })
    },
  })
}

export function useResendInvitation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api<Item<Invitation>>(`/admin/invitations/${id}/resend`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invitations'] })
    },
  })
}

export function useRevokeInvitation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api<Item<Invitation>>(`/admin/invitations/${id}/revoke`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invitations'] })
    },
  })
}

export function useValidateInvitation() {
  return useMutation({
    mutationFn: (body: InvitationValidateRequest) =>
      api<Item<InvitationValidateOut>>('/auth/invitations/validate', { method: 'POST', body }),
  })
}

export function useSendInvitationCode() {
  return useMutation({
    mutationFn: (body: InvitationSendCodeRequest) =>
      api<Item<{ sent_to: string; expires_in_seconds: number }>>('/auth/invitations/send-code', { method: 'POST', body }),
  })
}

export function useAcceptInvitation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: InvitationAcceptRequest) =>
      api<Item<Session>>('/auth/invitations/accept', { method: 'POST', body }),
    onSuccess: (res) => {
      qc.setQueryData(qk.me, res.data.user)
    },
  })
}
