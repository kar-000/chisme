export default function Input({ label, error, className = '', ...props }) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-xs text-[var(--text-muted)] uppercase tracking-wider">
          {label}
        </label>
      )}
      <input
        className={`
          w-full bg-black/40 border border-[var(--border)] rounded
          text-[var(--text-primary)] font-mono text-sm px-3 py-2
          placeholder:text-[var(--text-muted)]
          focus:outline-none focus:border-[var(--border-glow)]
          focus:shadow-[0_0_12px_rgba(0,206,209,0.3)]
          transition-all duration-200
          ${error ? 'border-[var(--text-error)]' : ''}
          ${className}
        `}
        {...props}
      />
      {error && (
        <p className="text-xs text-[var(--text-error)]">&gt; {error}</p>
      )}
    </div>
  )
}
