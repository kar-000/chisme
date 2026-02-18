import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Modal from './Modal'

describe('Modal', () => {
  it('renders the title', () => {
    render(<Modal title="Confirm" onClose={vi.fn()}><p>Body</p></Modal>)
    expect(screen.getByText('Confirm')).toBeInTheDocument()
  })

  it('renders children', () => {
    render(<Modal title="X" onClose={vi.fn()}><p>Modal content</p></Modal>)
    expect(screen.getByText('Modal content')).toBeInTheDocument()
  })

  it('renders footer when provided', () => {
    render(
      <Modal title="X" onClose={vi.fn()} footer={<button>OK</button>}>
        body
      </Modal>
    )
    expect(screen.getByRole('button', { name: 'OK' })).toBeInTheDocument()
  })

  it('calls onClose when × button is clicked', async () => {
    const onClose = vi.fn()
    render(<Modal title="X" onClose={onClose}>body</Modal>)
    await userEvent.click(screen.getByRole('button', { name: '×' }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('calls onClose when Escape key is pressed', () => {
    const onClose = vi.fn()
    render(<Modal title="X" onClose={onClose}>body</Modal>)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('calls onClose when backdrop is clicked', async () => {
    const onClose = vi.fn()
    const { container } = render(<Modal title="X" onClose={onClose}>body</Modal>)
    // The outermost fixed div is the backdrop
    const backdrop = container.firstChild
    fireEvent.click(backdrop, { target: backdrop })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('does not show × button when onClose is not provided', () => {
    render(<Modal title="X">body</Modal>)
    expect(screen.queryByRole('button', { name: '×' })).toBeNull()
  })
})
