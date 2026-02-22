import { create } from 'zustand'

const useUIStore = create((set) => ({
  showInviteModal: false,
  setShowInviteModal: (val) => set({ showInviteModal: val }),
}))

export default useUIStore
