/**
 * Dynamic favicon badge utility.
 *
 * Draws a 32×32 canvas favicon using the app icon as the base, with an
 * optional orange badge in the top-right corner showing the unread count.
 *
 * Usage:
 *   setFaviconBadge(0)   // plain icon, no badge
 *   setFaviconBadge(5)   // icon + "5" badge
 *   setFaviconBadge(100) // icon + "!" badge (overflow)
 */

let _link = null
let _iconImage = null

function getFaviconLink() {
  if (!_link) {
    _link = document.querySelector("link[rel~='icon']")
    if (!_link) {
      _link = document.createElement('link')
      _link.rel = 'icon'
      _link.type = 'image/png'
      document.head.appendChild(_link)
    }
  }
  return _link
}

function loadIcon() {
  if (_iconImage) return Promise.resolve(_iconImage)
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => { _iconImage = img; resolve(img) }
    img.onerror = () => resolve(null)
    img.src = '/icons/icon-192.png'
  })
}

function drawFavicon(count, img) {
  const size = 32
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')

  if (img) {
    ctx.drawImage(img, 0, 0, size, size)
  } else {
    // Fallback if image fails to load: dark background + "C" lettermark
    ctx.fillStyle = '#0a0a0f'
    ctx.beginPath()
    ctx.roundRect(0, 0, size, size, 6)
    ctx.fill()
    ctx.fillStyle = '#00ced1'
    ctx.font = 'bold 20px "Courier New", monospace'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('C', size / 2, size / 2 + 1)
  }

  if (count > 0) {
    // Orange badge circle in top-right
    const r = 9
    const bx = size - r + 1
    const by = r - 1

    ctx.fillStyle = '#ff8c42'
    ctx.beginPath()
    ctx.arc(bx, by, r, 0, Math.PI * 2)
    ctx.fill()

    // Count label — "!" when > 99
    const label = count > 99 ? '!' : String(count)
    ctx.fillStyle = '#0a0a0f'
    ctx.font = `bold ${label.length > 1 ? 8 : 10}px "Courier New", monospace`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(label, bx, by)
  }

  return canvas.toDataURL('image/png')
}

export function setFaviconBadge(count) {
  loadIcon().then((img) => {
    getFaviconLink().href = drawFavicon(count, img)
  })
}
