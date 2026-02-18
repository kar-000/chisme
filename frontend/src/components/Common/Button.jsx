export default function Button({ children, variant = 'primary', className = '', ...props }) {
  const base = 'px-4 py-2 font-mono font-bold text-sm uppercase tracking-wide rounded transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed'
  const variants = {
    primary: 'bg-gradient-to-r from-crt-teal to-crt-teal-lt text-crt-bg shadow-glow hover:shadow-glow-lg hover:-translate-y-px active:translate-y-0',
    secondary: 'bg-transparent border border-[var(--border)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)] hover:border-[var(--border-glow)]',
    ghost: 'bg-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)]',
    danger: 'bg-transparent border border-[var(--text-error)] text-[var(--text-error)] hover:bg-red-900/20',
  }
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  )
}
