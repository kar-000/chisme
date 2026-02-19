import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DMList from './DMList'
import useDMStore from '../../store/dmStore'

vi.mock('../../store/dmStore', () => ({ default: vi.fn() }))

const mockOnSelect = vi.fn()

const baseDMs = [
  { id: 1, other_user: { id: 2, username: 'alice' }, last_message_at: null },
  { id: 2, other_user: { id: 3, username: 'bob' }, last_message_at: null },
]

beforeEach(() => {
  vi.clearAllMocks()
  useDMStore.mockReturnValue({ dms: baseDMs, activeDmId: null })
})

describe('DMList', () => {
  it('renders a list item for each DM', () => {
    render(<DMList onSelect={mockOnSelect} />)
    expect(screen.getByText(/alice/)).toBeInTheDocument()
    expect(screen.getByText(/bob/)).toBeInTheDocument()
  })

  it('renders empty state when no DMs', () => {
    useDMStore.mockReturnValue({ dms: [], activeDmId: null })
    render(<DMList onSelect={mockOnSelect} />)
    expect(screen.getByText(/no direct messages/i)).toBeInTheDocument()
  })

  it('calls onSelect with dm id when clicked', async () => {
    render(<DMList onSelect={mockOnSelect} />)
    await userEvent.click(screen.getByTestId('dm-item-1'))
    expect(mockOnSelect).toHaveBeenCalledWith(1)
  })

  it('applies active styling to the active DM', () => {
    useDMStore.mockReturnValue({ dms: baseDMs, activeDmId: 1 })
    render(<DMList onSelect={mockOnSelect} />)
    const activeBtn = screen.getByTestId('dm-item-1')
    expect(activeBtn.className).toMatch(/bg-\[var\(--bg-active\)\]/)
  })

  it('does not apply active styling to inactive DMs', () => {
    useDMStore.mockReturnValue({ dms: baseDMs, activeDmId: 1 })
    render(<DMList onSelect={mockOnSelect} />)
    const inactiveBtn = screen.getByTestId('dm-item-2')
    expect(inactiveBtn.className).not.toMatch(/bg-\[var\(--bg-active\)\]/)
  })
})
