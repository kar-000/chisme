import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import GifPicker from './GifPicker'

vi.mock('../../services/gifs', () => ({
  searchGifs: vi.fn(),
}))

import { searchGifs } from '../../services/gifs'

const mockGifs = [
  { id: '1', url: 'https://tenor.com/1.gif', preview_url: 'https://tenor.com/1-nano.gif', title: 'funny cat', width: 200, height: 150 },
  { id: '2', url: 'https://tenor.com/2.gif', preview_url: 'https://tenor.com/2-nano.gif', title: 'cute dog', width: 200, height: 150 },
]

beforeEach(() => {
  vi.clearAllMocks()
  searchGifs.mockResolvedValue({ data: mockGifs })
})

describe('GifPicker', () => {
  it('renders the search input', async () => {
    render(<GifPicker onSelect={vi.fn()} onClose={vi.fn()} />)
    expect(screen.getByTestId('gif-search-input')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    // searchGifs never resolves in this test (pending promise)
    searchGifs.mockReturnValue(new Promise(() => {}))
    render(<GifPicker onSelect={vi.fn()} onClose={vi.fn()} />)
    expect(screen.getByTestId('gif-loading')).toBeInTheDocument()
  })

  it('loads featured GIFs on mount', async () => {
    render(<GifPicker onSelect={vi.fn()} onClose={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getAllByTestId('gif-item')).toHaveLength(2)
    })
    expect(searchGifs).toHaveBeenCalledWith('')
  })

  it('shows "No results" when search returns empty array', async () => {
    searchGifs.mockResolvedValue({ data: [] })
    render(<GifPicker onSelect={vi.fn()} onClose={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByTestId('gif-empty')).toBeInTheDocument()
    })
  })

  it('calls searchGifs with query after typing', async () => {
    vi.useFakeTimers()
    render(<GifPicker onSelect={vi.fn()} onClose={vi.fn()} />)

    // Wait for initial load
    await act(async () => { vi.runAllTimersAsync() })
    searchGifs.mockClear()

    const input = screen.getByTestId('gif-search-input')
    fireEvent.change(input, { target: { value: 'dog' } })

    // Advance past debounce
    act(() => vi.advanceTimersByTime(350))
    await waitFor(() => {
      expect(searchGifs).toHaveBeenCalledWith('dog')
    })

    vi.useRealTimers()
  })

  it('calls onSelect and onClose when a GIF item is clicked', async () => {
    const onSelect = vi.fn()
    const onClose = vi.fn()
    render(<GifPicker onSelect={onSelect} onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getAllByTestId('gif-item')).toHaveLength(2)
    })

    await userEvent.click(screen.getAllByTestId('gif-item')[0])
    expect(onSelect).toHaveBeenCalledWith(mockGifs[0])
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when Escape is pressed', async () => {
    const onClose = vi.fn()
    render(<GifPicker onSelect={vi.fn()} onClose={onClose} />)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when clicking outside the picker', async () => {
    const onClose = vi.fn()
    const { container } = render(
      <div>
        <GifPicker onSelect={vi.fn()} onClose={onClose} />
        <button data-testid="outside">Outside</button>
      </div>
    )
    fireEvent.mouseDown(screen.getByTestId('outside'))
    expect(onClose).toHaveBeenCalled()
  })

  it('does not call onClose when clicking inside the picker', async () => {
    const onClose = vi.fn()
    render(<GifPicker onSelect={vi.fn()} onClose={onClose} />)
    fireEvent.mouseDown(screen.getByTestId('gif-picker'))
    expect(onClose).not.toHaveBeenCalled()
  })
})
