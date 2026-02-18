function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function isImage(file) {
  return file.type.startsWith('image/')
}

export default function AttachmentPreview({ attachments, onRemove }) {
  if (!attachments.length) return null

  return (
    <div className="flex flex-wrap gap-2 px-4 pt-2">
      {attachments.map((a) => (
        <div
          key={a.tempId}
          className="relative flex flex-col rounded border border-[var(--border)] bg-black/40 overflow-hidden"
          style={{ minWidth: '80px', maxWidth: '120px' }}
          data-testid="attachment-preview"
        >
          {/* Thumbnail or file icon */}
          {isImage(a.file) ? (
            <img
              src={URL.createObjectURL(a.file)}
              alt={a.file.name}
              className="w-full object-cover"
              style={{ height: '72px' }}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-16 text-[var(--text-muted)] px-2">
              <span className="text-xl">📎</span>
              <span className="text-[9px] font-mono truncate w-full text-center mt-1">
                {a.file.name}
              </span>
            </div>
          )}

          {/* Progress bar */}
          {a.progress < 100 && !a.error && (
            <div className="h-0.5 w-full bg-[var(--bg-hover)]">
              <div
                className="h-full bg-[var(--accent-teal)] shadow-glow-sm transition-all duration-200"
                style={{ width: `${a.progress}%` }}
              />
            </div>
          )}

          {/* Error indicator */}
          {a.error && (
            <div className="absolute inset-0 bg-red-900/70 flex items-center justify-center">
              <span className="text-[10px] text-red-300 text-center px-1">{a.error}</span>
            </div>
          )}

          {/* File size */}
          <div className="text-[9px] text-[var(--text-muted)] font-mono px-1 pb-0.5 truncate">
            {formatBytes(a.file.size)}
          </div>

          {/* Remove button */}
          <button
            onClick={() => onRemove(a.tempId)}
            className="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-black/60 text-[var(--text-muted)]
                       hover:text-[var(--text-error)] flex items-center justify-center text-[10px]"
            title="Remove"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
