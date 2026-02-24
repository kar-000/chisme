import { useState, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize from 'rehype-sanitize'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { visit } from 'unist-util-visit'
import { chismeSanitizeSchema } from '../../utils/sanitize'

const SUPPORTED_LANGUAGES = [
  'python', 'javascript', 'typescript', 'json',
  'bash', 'sql', 'yaml', 'html', 'css',
]

/** Remark plugin — flattens heading nodes to paragraph > strong before rehype-sanitize runs. */
function remarkFlattenHeadings() {
  return (tree) => {
    visit(tree, 'heading', (node) => {
      node.type = 'paragraph'
      node.children = [{ type: 'strong', children: node.children }]
    })
  }
}

/** Remark plugin — converts @username tokens to span[data-mention] hast elements. */
function remarkMentions() {
  return (tree) => {
    visit(tree, 'text', (node, index, parent) => {
      if (!parent || !node.value.includes('@')) return
      const parts = node.value.split(/(@\w+)/g)
      if (parts.length === 1) return

      const newNodes = parts
        .filter((p) => p !== '')
        .map((part) => {
          if (/^@\w+$/.test(part)) {
            return {
              type: 'mention',
              children: [{ type: 'text', value: part }],
              data: {
                hName: 'span',
                hProperties: { 'data-mention': part.slice(1) },
              },
            }
          }
          return { type: 'text', value: part }
        })

      parent.children.splice(index, 1, ...newNodes)
    })
  }
}

/** Remark plugin — wraps keyword matches in span[data-keyword] elements. */
function remarkKeywords(keywords) {
  if (!keywords || keywords.length === 0) return () => {}
  const pattern = new RegExp(
    `(${keywords.map((k) => k.keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`,
    'gi',
  )
  return () => (tree) => {
    visit(tree, 'text', (node, index, parent) => {
      if (!parent || !pattern.test(node.value)) return
      pattern.lastIndex = 0
      const parts = node.value.split(pattern)
      if (parts.length === 1) return

      const newNodes = parts
        .filter((p) => p !== '')
        .map((part) => {
          if (pattern.test(part)) {
            pattern.lastIndex = 0
            return {
              type: 'keyword',
              children: [{ type: 'text', value: part }],
              data: {
                hName: 'mark',
                hProperties: { 'data-keyword': part.toLowerCase() },
              },
            }
          }
          pattern.lastIndex = 0
          return { type: 'text', value: part }
        })

      parent.children.splice(index, 1, ...newNodes)
    })
  }
}

function CopyButton({ content }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content)
    } catch {
      // fallback for insecure contexts
      const el = document.createElement('textarea')
      el.value = content
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={copy}
      className="msg-code-copy"
      title="Copy code"
      type="button"
    >
      {copied ? 'copied!' : 'copy'}
    </button>
  )
}

/**
 * Renders message content as constrained Markdown.
 * Supports: bold, italic, strikethrough, inline code, code blocks (with
 * optional syntax highlighting and copy button), blockquotes, and links.
 * @mentions are rendered as interactive buttons.
 * Keyword matches are highlighted if keywords prop is provided.
 */
export function MessageContent({ content, currentUsername, isOwn, onMentionClick, keywords }) {
  const components = useMemo(() => ({
    // Pass through — code component handles block rendering
    pre: ({ children }) => <>{children}</>,

    // Handles both inline code (no className) and fenced code blocks (className=language-*)
    code({ className, children }) {
      const match = /language-(\w+)/.exec(className || '')
      const language = match?.[1]

      if (language !== undefined || (className && className.startsWith('language-'))) {
        const code = String(children).trimEnd()
        const isSupported = SUPPORTED_LANGUAGES.includes(language)
        return (
          <div className="msg-code-block">
            {language && <div className="msg-code-lang">{language}</div>}
            {isSupported ? (
              <SyntaxHighlighter language={language} useInlineStyles={false} PreTag="pre">
                {code}
              </SyntaxHighlighter>
            ) : (
              <pre><code>{code}</code></pre>
            )}
            <CopyButton content={code} />
          </div>
        )
      }

      return <code className="msg-inline-code">{children}</code>
    },

    // Safe links — new tab, noopener
    a({ href, children }) {
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" className="msg-link">
          {children}
        </a>
      )
    },

    // Flatten lists — rendered as styled plain text
    ul: ({ children }) => <span className="msg-flat-list">{children}</span>,
    ol: ({ children }) => <span className="msg-flat-list">{children}</span>,
    li: ({ children }) => <p className="msg-list-item">{children}</p>,

    // Strip horizontal rules
    hr: () => null,

    // @mention spans injected by remarkMentions plugin
    span({ 'data-mention': username, children, ...props }) {
      if (username !== undefined) {
        const isAll = username.toLowerCase() === 'all'
        const isMe = !isAll && username.toLowerCase() === currentUsername?.toLowerCase()
        const highlight = isAll || isMe
        return (
          <button
            type="button"
            onClick={() => !isAll && onMentionClick?.(username)}
            className={`font-bold font-mono transition-colors ${
              highlight
                ? 'text-[var(--crt-orange,#FF8C42)] bg-[rgba(255,140,66,0.15)] px-0.5 rounded hover:bg-[rgba(255,140,66,0.25)]'
                : isOwn
                  ? 'text-[var(--text-own)] hover:underline'
                  : 'text-[var(--text-lt)] hover:underline'
            }`}
          >
            @{username}
          </button>
        )
      }
      return <span {...props}>{children}</span>
    },

    // Keyword highlight marks injected by remarkKeywords plugin
    mark({ 'data-keyword': kw, children, ...props }) {
      if (kw !== undefined) {
        return <mark className="keyword-highlight">{children}</mark>
      }
      return <mark {...props}>{children}</mark>
    },
  }), [currentUsername, isOwn, onMentionClick])

  const remarkPlugins = useMemo(() => [
    remarkFlattenHeadings,
    remarkMentions,
    [remarkGfm, { singleTilde: false }],
    ...(keywords?.length > 0 ? [remarkKeywords(keywords)] : []),
  ], [keywords])

  return (
    <div className="msg-content">
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={[
          [rehypeSanitize, chismeSanitizeSchema],
        ]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
