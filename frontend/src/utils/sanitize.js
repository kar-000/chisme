/**
 * rehype-sanitize schema for rendered message content.
 * Explicit allowlist — everything not listed is stripped.
 */
export const chismeSanitizeSchema = {
  tagNames: [
    'p', 'br',
    'strong', 'em', 'del', 's',
    'code', 'pre',
    'blockquote',
    'a',
    'span',  // used for @mention rendering
    'mark',  // used for keyword highlight rendering
    'ul', 'ol', 'li',
  ],
  attributes: {
    a: ['href', 'target', 'rel'],
    code: ['className'],          // language-* class for syntax highlighting
    span: ['data-mention'],       // @mention identity
    mark: ['data-keyword'],       // keyword highlight identity
  },
  protocols: {
    href: ['http', 'https'],      // blocks javascript: and data: URIs
  },
  strip: ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input'],
}
