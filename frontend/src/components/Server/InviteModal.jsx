import useServerStore from '../../store/serverStore'
import Modal from '../Common/Modal'
import { InviteForm } from './InviteForm'

export function InviteModal({ onClose }) {
  const activeServerId = useServerStore((s) => s.activeServerId)
  const servers = useServerStore((s) => s.servers)
  const server = servers.find((s) => s.id === activeServerId)

  return (
    <Modal title={`Invite People to ${server?.name ?? '…'}`} onClose={onClose}>
      <InviteForm serverId={activeServerId} serverName={server?.name} />
    </Modal>
  )
}
