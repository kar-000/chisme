import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AttachmentPreview from './AttachmentPreview'

beforeAll(() => {
  vi.stubGlobal('URL', { createObjectURL: () => 'blob:fake' })
})

afterAll(() => {
  vi.unstubAllGlobals()
})

const makeFile = (name, type, size = 1024) => {
  const f = new File(['x'.repeat(size)], name, { type })
  return f
}

const makeImageAttachment = (overrides = {}) => ({
  tempId: 'tmp-1',
  file: makeFile('photo.png', 'image/png'),
  progress: 100,
  error: null,
  id: 1,
  url: '/uploads/photo.png',
  ...overrides,
})

const makeFileAttachment = (overrides = {}) => ({
  tempId: 'tmp-2',
  file: makeFile('report.pdf', 'application/pdf', 2048),
  progress: 100,
  error: null,
  id: 2,
  url: '/uploads/report.pdf',
  ...overrides,
})

describe('AttachmentPreview', () => {
  it('renders nothing when attachments array is empty', () => {
    const { container } = render(<AttachmentPreview attachments={[]} onRemove={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders an image thumbnail for image files', () => {
    render(<AttachmentPreview attachments={[makeImageAttachment()]} onRemove={vi.fn()} />)
    expect(screen.getByRole('img')).toBeInTheDocument()
  })

  it('renders a file icon and name for non-image files', () => {
    render(<AttachmentPreview attachments={[makeFileAttachment()]} onRemove={vi.fn()} />)
    expect(screen.getByText('report.pdf')).toBeInTheDocument()
    expect(screen.getByText('📎')).toBeInTheDocument()
  })

  it('shows a progress bar when progress < 100', () => {
    const a = makeImageAttachment({ progress: 50 })
    render(<AttachmentPreview attachments={[a]} onRemove={vi.fn()} />)
    // Progress bar container is present
    const bar = document.querySelector('[style*="width: 50%"]')
    expect(bar).not.toBeNull()
  })

  it('does not show progress bar when progress is 100', () => {
    render(<AttachmentPreview attachments={[makeImageAttachment()]} onRemove={vi.fn()} />)
    const bar = document.querySelector('[style*="width: 100%"]')
    expect(bar).toBeNull()
  })

  it('shows error overlay when error is set', () => {
    const a = makeImageAttachment({ error: 'File too large', progress: 0 })
    render(<AttachmentPreview attachments={[a]} onRemove={vi.fn()} />)
    expect(screen.getByText('File too large')).toBeInTheDocument()
  })

  it('calls onRemove with tempId when remove button is clicked', () => {
    const onRemove = vi.fn()
    render(<AttachmentPreview attachments={[makeImageAttachment()]} onRemove={onRemove} />)
    fireEvent.click(screen.getByTitle('Remove'))
    expect(onRemove).toHaveBeenCalledWith('tmp-1')
  })

  it('renders multiple attachments', () => {
    const attachments = [makeImageAttachment(), makeFileAttachment()]
    render(<AttachmentPreview attachments={attachments} onRemove={vi.fn()} />)
    expect(screen.getAllByTestId('attachment-preview')).toHaveLength(2)
  })
})
