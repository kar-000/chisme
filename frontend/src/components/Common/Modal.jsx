import { useEffect } from 'react'

export default function Modal({ title, children, onClose, footer }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose?.()}
    >
      <div
        className="bg-[var(--bg-primary)] border-2 border-[var(--border-glow)] rounded-lg
                   w-full max-w-md shadow-glow-lg animate-[modalIn_0.2s_ease-out]"
        style={{ animation: 'modalIn 0.2s ease-out' }}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
          <h2 className="text-lg font-medium text-[var(--text-primary)] glow-teal">{title}</h2>
          {onClose && (
            <button
              onClick={onClose}
              className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xl leading-none"
            >
              ×
            </button>
          )}
        </div>
        <div className="px-6 py-6">{children}</div>
        {footer && (
          <div className="px-6 py-4 border-t border-[var(--border)] flex gap-3 justify-end">
            {footer}
          </div>
        )}
      </div>
      <style>{`@keyframes modalIn { from { opacity:0; transform:translateY(-16px) } to { opacity:1; transform:translateY(0) } }`}</style>
    </div>
  )
}
