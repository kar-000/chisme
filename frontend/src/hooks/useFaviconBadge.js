import { useEffect } from 'react'
import useChatStore from '../store/chatStore'
import { setFaviconBadge } from '../utils/favicon'

/**
 * Watches the total unread message count across all channels and:
 *  - Updates the favicon with an orange badge showing the count
 *  - Prepends "(N)" to the document title when there are unread messages
 *
 * Should be called once inside ChatLayout.
 */
export function useFaviconBadge() {
  const unreadCounts = useChatStore((s) => s.unreadCounts)

  useEffect(() => {
    const total = Object.values(unreadCounts).reduce((sum, n) => sum + n, 0)
    setFaviconBadge(total)
    document.title = total > 0 ? `(${total > 99 ? '99+' : total}) chisme` : 'chisme'
  }, [unreadCounts])
}
