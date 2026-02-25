import api from './api'

export const uploadFile = (file, onProgress, durationSecs) => {
  const fd = new FormData()
  fd.append('file', file)
  if (durationSecs != null) fd.append('duration_secs', String(Math.round(durationSecs)))
  return api.post('/upload', fd, {
    onUploadProgress: (e) => {
      if (e.total) onProgress?.(Math.round((e.loaded / e.total) * 100))
    },
  })
}
