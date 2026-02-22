/**
 * Shimmering skeleton placeholder shown while messages are loading.
 * Renders a fixed number of fake message rows.
 */
function SkeletonRow({ wide }) {
  return (
    <div className="flex gap-3 px-3 py-2 animate-pulse">
      {/* Avatar blob */}
      <div className="w-8 h-8 rounded bg-[var(--border)] flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0 flex flex-col gap-1.5 pt-1">
        {/* Username + timestamp */}
        <div className="flex gap-2 items-baseline">
          <div className="h-2.5 w-20 rounded bg-[var(--border)]" />
          <div className="h-2 w-10 rounded bg-[var(--border)] opacity-50" />
        </div>
        {/* Message line(s) */}
        <div className={`h-2.5 rounded bg-[var(--border)] ${wide ? 'w-3/4' : 'w-1/2'}`} />
        {wide && <div className="h-2.5 w-2/5 rounded bg-[var(--border)]" />}
      </div>
    </div>
  )
}

export default function MessageSkeleton({ count = 8 }) {
  const rows = Array.from({ length: count }, (_, i) => ({ id: i, wide: i % 3 !== 2 }))
  return (
    <div className="flex flex-col gap-0.5 py-4">
      {rows.map(({ id, wide }) => (
        <SkeletonRow key={id} wide={wide} />
      ))}
    </div>
  )
}
