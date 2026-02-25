import { useEffect } from 'react'
import useChatStore from '../store/chatStore'
import useDMStore from '../store/dmStore'
import { setFaviconBadge } from '../utils/favicon'

/**
 * Watches the total unread message count across all channels and DMs and:
 *  - Updates the favicon with an orange badge showing the count
 *  - Prepends "(N)" to the document title when there are unread messages
 *
 * Should be called once inside ChatLayout.
 */
export function useFaviconBadge() {
  const unreadCounts = useChatStore((s) => s.unreadCounts)
  const unreadDmCounts = useDMStore((s) => s.unreadDmCounts)

  useEffect(() => {
    const channelTotal = Object.values(unreadCounts).reduce((sum, n) => sum + n, 0)
    const dmTotal = Object.values(unreadDmCounts).reduce((sum, n) => sum + n, 0)
    const total = channelTotal + dmTotal
    setFaviconBadge(total)
    document.title = total > 0 ? `(${total > 99 ? '99+' : total}) chisme` : 'chisme'
  }, [unreadCounts, unreadDmCounts])
}
