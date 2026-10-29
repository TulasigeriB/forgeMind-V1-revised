import { useEffect, useState } from 'react'
import { CircleAlert, CheckCircle2, X } from 'lucide-react'
import type { ToastDetail } from '../utils/toast'

interface Toast extends ToastDetail {
  id: number
}

function ToastViewport() {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    let nextId = 0
    const timers = new Map<number, number>()
    const removeToast = (id: number) => {
      setToasts((current) => current.filter((toast) => toast.id !== id))
      const timer = timers.get(id)
      if (timer !== undefined) window.clearTimeout(timer)
      timers.delete(id)
    }
    const handleToast = (event: Event) => {
      const detail = (event as CustomEvent<ToastDetail>).detail
      const id = ++nextId
      setToasts((current) => [...current, { ...detail, id }])
      timers.set(id, window.setTimeout(() => removeToast(id), 4000))
    }
    const handleDismiss = (event: Event) => {
      removeToast((event as CustomEvent<number>).detail)
    }

    window.addEventListener('forgemind:toast', handleToast)
    window.addEventListener('forgemind:dismiss-toast', handleDismiss)
    return () => {
      window.removeEventListener('forgemind:toast', handleToast)
      window.removeEventListener('forgemind:dismiss-toast', handleDismiss)
      timers.forEach((timer) => window.clearTimeout(timer))
    }
  }, [])

  return (
    <div className="toast-viewport" aria-live="polite" aria-relevant="additions">
      {toasts.map((toast) => {
        const Icon = toast.kind === 'success' ? CheckCircle2 : CircleAlert
        return (
          <div className={`app-toast app-toast-${toast.kind}`} key={toast.id} role={toast.kind === 'error' ? 'alert' : 'status'}>
            <Icon size={17} />
            <span>{toast.message}</span>
            <button type="button" onClick={() => window.dispatchEvent(new CustomEvent<number>('forgemind:dismiss-toast', { detail: toast.id }))} aria-label="Dismiss notification"><X size={15} /></button>
          </div>
        )
      })}
    </div>
  )
}

export default ToastViewport
