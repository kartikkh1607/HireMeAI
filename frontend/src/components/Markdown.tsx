// =============================================================================
// Markdown.tsx - assistant ke jawab (markdown text) ko safely render karna.
//
// SECURITY - teen layers:
//  1. dangerouslySetInnerHTML KABHI nahi. react-markdown text ko parse karke
//     React elements banata hai, HTML string nahi -> browser kuch "execute"
//     nahi karta.
//  2. Raw HTML (jaise <img src=x onerror=alert(1)>) react-markdown by default
//     plain TEXT bana deta hai (humne rehype-raw jaan-boojh ke NAHI lagaya).
//     LLM ka output "untrusted input" maano - resume me kuch bhi ho sakta hai.
//  3. Links: sirf http/https. "javascript:..." wale links sirf text ban jaate.
//     rel="noopener noreferrer" -> nayi tab humare page ko window.opener se
//     control nahi kar sakti, aur referrer leak nahi hota.
// Images bhi band - markdown image se tracking pixel load ho sakta hai.
// =============================================================================
import { memo } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { safeHttpUrl } from '../lib/profile'

const components: Components = {
  // "node" prop DOM tak nahi jaana chahiye, isliye alag nikaal diya
  a({ node: _node, href, children, ...rest }) {
    const safe = safeHttpUrl(href)
    if (!safe) return <span>{children}</span>
    return (
      <a {...rest} href={safe} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    )
  },
  // Image ki jagah sirf uska alt text
  img({ alt }) {
    return alt ? <span>{alt}</span> : null
  },
}

const remarkPlugins = [remarkGfm] // tables, ~~strike~~, autolinks

interface MarkdownProps {
  content: string
  streaming?: boolean
}

// memo -> content same ho to dobara parse nahi (streaming me purane messages
// har chunk pe re-render na hon)
export const Markdown = memo(function Markdown({ content, streaming }: MarkdownProps) {
  return (
    <div className={`md${streaming ? ' is-streaming' : ''}`}>
      <ReactMarkdown remarkPlugins={remarkPlugins} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  )
})
