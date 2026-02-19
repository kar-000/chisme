import { useState, useEffect } from 'react'

/**
 * Shows a top banner during WebSocket disconnection or after server failover.
 * - reconnecting: orange "Reconnecting…" bar with spinner
 * - failoverDetected (after reconnect): teal "Back online" bar, dismissible after 5s
 */
export default function FailoverBanner({ reconnecting, failoverDetected }) {
  const [dismissable, setDismissable] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  // Reset dismissed state when a new condition appears
  useEffect(() => {
    if (reconnecting || failoverDetected) {
      setDismissed(false)
      setDismissable(false)
      const t = setTimeout(() => setDismissable(true), 5000)
      return () => clearTimeout(t)
    }
  }, [reconnecting, failoverDetected])

  if (dismissed || (!reconnecting && !failoverDetected)) return null

  if (reconnecting) {
    return (
      <div
        className="fixed top-0 inset-x-0 z-50 flex items-center gap-3 px-4 py-2.5
                   bg-[rgba(255,140,66,0.95)] border-b-2 border-[var(--crt-orange)]
                   backdrop-blur-sm animate-[slideDown_0.3s_ease-out]"
        data-testid="failover-banner-reconnecting"
      >
        <span className="text-lg">⚠️</span>
        <div className="flex-1 min-w-0">
          <span className="font-mono font-bold text-sm text-black/90">Reconnecting…</span>
          <span className="ml-2 text-xs text-black/70 font-mono">
            Connection lost. Attempting to reconnect.
          </span>
        </div>
        {/* Spinner */}
        <div
          className="w-5 h-5 rounded-full border-2 border-black/20 border-t-black/80
                     animate-spin flex-shrink-0"
          aria-label="reconnecting"
        />
      </div>
    )
  }

  if (failoverDetected) {
    return (
      <div
        className="fixed top-0 inset-x-0 z-50 flex items-center gap-3 px-4 py-2.5
                   bg-[rgba(0,206,209,0.95)] border-b-2 border-[var(--crt-teal)]
                   backdrop-blur-sm animate-[slideDown_0.3s_ease-out]"
        data-testid="failover-banner-recovered"
      >
        <span className="text-lg">✅</span>
        <div className="flex-1 min-w-0">
          <span className="font-mono font-bold text-sm text-black/90">Back online</span>
          <span className="ml-2 text-xs text-black/70 font-mono">
            Connection restored. A small number of recent messages may have been missed.
          </span>
        </div>
        {dismissable && (
          <button
            onClick={() => setDismissed(true)}
            className="text-black/70 hover:text-black transition-colors flex-shrink-0 text-lg leading-none px-1"
            title="Dismiss"
            data-testid="failover-banner-dismiss"
          >
            ✕
          </button>
        )}
      </div>
    )
  }

  return null
}
