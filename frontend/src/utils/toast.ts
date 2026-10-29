export type ToastKind = 'success' | 'error'

interface ToastDetail {
  message: string
  kind: ToastKind
}

export function showToast(message: string, kind: ToastKind = 'success') {
  window.dispatchEvent(new CustomEvent<ToastDetail>('forgemind:toast', {
    detail: { message, kind },
  }))
}

export type { ToastDetail }
