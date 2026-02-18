import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Input from './Input'

describe('Input', () => {
  it('renders an input element', () => {
    render(<Input />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('renders the label when provided', () => {
    render(<Input label="Username" />)
    expect(screen.getByText('Username')).toBeInTheDocument()
  })

  it('renders without a label when omitted', () => {
    const { container } = render(<Input placeholder="enter text" />)
    expect(container.querySelector('label')).toBeNull()
  })

  it('shows an error message when error prop is set', () => {
    render(<Input error="Field is required" />)
    expect(screen.getByText(/field is required/i)).toBeInTheDocument()
  })

  it('does not show error element when no error', () => {
    const { container } = render(<Input />)
    expect(container.querySelector('p')).toBeNull()
  })

  it('passes placeholder through to the input', () => {
    render(<Input placeholder="your_handle" />)
    expect(screen.getByPlaceholderText('your_handle')).toBeInTheDocument()
  })

  it('calls onChange when user types', async () => {
    const onChange = vi.fn()
    render(<Input onChange={onChange} />)
    await userEvent.type(screen.getByRole('textbox'), 'hello')
    expect(onChange).toHaveBeenCalled()
  })

  it('renders password input when type="password"', () => {
    const { container } = render(<Input type="password" />)
    expect(container.querySelector('input[type="password"]')).toBeInTheDocument()
  })
})
