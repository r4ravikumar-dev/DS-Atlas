'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '@/lib/api/client'
import { qk } from '@/lib/api/keys'
import type { Item, Session, User } from '@/lib/api/types'

export function useMe() {
  return useQuery({
    queryKey: qk.me,
    queryFn: ({ signal }) => api<Item<User>>('/auth/me', { signal }).then((r) => r.data),
    retry: (n, e) => !(e instanceof ApiError && e.status === 401) && n < 2,
    staleTime: 60_000,
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { email: string; password: string }) => api<Item<Session>>('/auth/login', { method: 'POST', body }),
    onSuccess: (r) => {
      qc.clear()
      qc.setQueryData(qk.me, r.data.user)
    },
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>('/auth/logout', { method: 'POST' }),
    onSettled: () => qc.clear(),
  })
}

/** Single-administrator model: the backend only issues sessions to administrators and enforces this on every endpoint. */
export function isAdmin(user: User | undefined) {
  return !!user && user.role === 'admin'
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) => api<Item<User>>('/auth/password', { method: 'POST', body }),
  })
}
