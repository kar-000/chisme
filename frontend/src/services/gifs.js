import api from './api'

export const searchGifs = (q = '', limit = 20) =>
  api.get('/gifs/search', { params: { q, limit } })

export const attachGif = (gif) =>
  api.post('/gifs/attach', {
    tenor_id: gif.id,
    url: gif.url,
    title: gif.title,
    width: gif.width,
    height: gif.height,
  })
