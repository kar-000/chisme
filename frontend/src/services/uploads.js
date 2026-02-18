import api from './api'

export const uploadFile = (file, onProgress) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/upload', fd, {
    onUploadProgress: (e) => {
      if (e.total) onProgress?.(Math.round((e.loaded / e.total) * 100))
    },
  })
}
