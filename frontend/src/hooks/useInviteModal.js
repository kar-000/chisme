import useUIStore from '../store/uiStore'

export function useInviteModal() {
  const showInviteModal = useUIStore((s) => s.showInviteModal)
  const setShowInviteModal = useUIStore((s) => s.setShowInviteModal)
  return {
    isOpen: showInviteModal,
    open: () => setShowInviteModal(true),
    close: () => setShowInviteModal(false),
  }
}
