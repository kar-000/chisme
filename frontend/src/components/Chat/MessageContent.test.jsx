import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import { MessageContent } from './MessageContent'

// react-syntax-highlighter is heavy — mock it for tests
vi.mock('react-syntax-highlighter', () => ({
  Prism: ({ children, language }) => (
    <pre data-testid="syntax-highlighter" data-language={language}>
      <code>{children}</code>
    </pre>
  ),
}))

describe('MessageContent', () => {
  it('renders plain text unchanged', () => {
    render(<MessageContent content="just a normal message" />)
    expect(screen.getByText('just a normal message')).toBeInTheDocument()
  })

  it('renders bold text', () => {
    render(<MessageContent content="**hello**" />)
    expect(screen.getByText('hello').tagName).toBe('STRONG')
  })

  it('renders italic text', () => {
    render(<MessageContent content="*world*" />)
    expect(screen.getByText('world').tagName).toBe('EM')
  })

  it('renders strikethrough', () => {
    render(<MessageContent content="~~deleted~~" />)
    expect(document.querySelector('del')).toBeInTheDocument()
    expect(screen.getByText('deleted')).toBeInTheDocument()
  })

  it('renders inline code', () => {
    render(<MessageContent content="`npm install`" />)
    const el = screen.getByText('npm install')
    expect(el.tagName).toBe('CODE')
    expect(el.className).toContain('msg-inline-code')
  })

  it('renders code block with language label', () => {
    render(<MessageContent content={"```python\nprint('hi')\n```"} />)
    expect(screen.getByText('python')).toBeInTheDocument()
    expect(screen.getByTestId('syntax-highlighter')).toBeInTheDocument()
    expect(screen.getByTestId('syntax-highlighter').dataset.language).toBe('python')
  })

  it('renders code block without language as plain pre/code', () => {
    render(<MessageContent content={"```\nsome code\n```"} />)
    expect(screen.getByText('some code')).toBeInTheDocument()
    // No syntax highlighter for unknown language
    expect(screen.queryByTestId('syntax-highlighter')).toBeNull()
  })

  it('renders copy button inside code block', () => {
    render(<MessageContent content={"```js\nconsole.log(1)\n```"} />)
    expect(screen.getByTitle('Copy code')).toBeInTheDocument()
  })

  it('renders blockquote with correct element', () => {
    render(<MessageContent content="> quoted text" />)
    expect(document.querySelector('blockquote')).toBeInTheDocument()
    expect(screen.getByText('quoted text')).toBeInTheDocument()
  })

  it('renders headings as bold paragraphs, not heading elements', () => {
    render(<MessageContent content="# Big Title" />)
    expect(document.querySelector('h1')).toBeNull()
    const strong = document.querySelector('strong')
    expect(strong).toBeInTheDocument()
    expect(strong.textContent).toBe('Big Title')
  })

  it('opens links in new tab with noopener', () => {
    render(<MessageContent content="https://example.com" />)
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link).toHaveClass('msg-link')
  })

  it('does not render javascript: href links', () => {
    render(<MessageContent content="[click](javascript:alert(1))" />)
    const link = screen.queryByRole('link')
    expect(link).toBeNull()
  })

  it('strips raw HTML script tags', () => {
    render(<MessageContent content={'hello <script>alert("xss")</script> world'} />)
    expect(document.querySelector('script')).toBeNull()
    expect(screen.getByText(/hello/)).toBeInTheDocument()
  })

  it('renders @mention as a button', () => {
    render(<MessageContent content="hey @alice check this out" currentUsername="bob" />)
    const btn = screen.getByRole('button', { name: /@alice/ })
    expect(btn).toBeInTheDocument()
  })

  it('highlights @mention matching current user', () => {
    render(<MessageContent content="hello @bob" currentUsername="bob" />)
    const btn = screen.getByRole('button', { name: /@bob/ })
    expect(btn.className).toContain('crt-orange')
  })

  it('calls onMentionClick when a mention is clicked', () => {
    const onMentionClick = vi.fn()
    render(
      <MessageContent
        content="ping @carol"
        currentUsername="alice"
        onMentionClick={onMentionClick}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /@carol/ }))
    expect(onMentionClick).toHaveBeenCalledWith('carol')
  })

  it('does not call onMentionClick for @all', () => {
    const onMentionClick = vi.fn()
    render(
      <MessageContent
        content="hey @all"
        currentUsername="alice"
        onMentionClick={onMentionClick}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /@all/ }))
    expect(onMentionClick).not.toHaveBeenCalled()
  })

  it('renders lists flattened, not as ul/li elements', () => {
    render(<MessageContent content={"- item one\n- item two"} />)
    // ul/li are intercepted and flattened
    expect(document.querySelector('ul')).toBeNull()
    expect(screen.getByText('item one')).toBeInTheDocument()
    expect(screen.getByText('item two')).toBeInTheDocument()
  })
})
