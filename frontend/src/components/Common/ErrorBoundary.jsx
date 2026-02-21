import { Component } from 'react'

/**
 * React error boundary — catches render-time errors in child components
 * and shows a friendly recovery UI instead of a blank screen.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary]', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 p-8 font-mono">
          <p className="text-4xl">💀</p>
          <p className="text-[var(--text-primary)] glow-teal text-lg font-bold">
            something went wrong
          </p>
          <p className="text-[var(--text-muted)] text-sm text-center max-w-sm">
            {this.state.error.message}
          </p>
          <button
            onClick={() => this.setState({ error: null })}
            className="px-4 py-2 text-sm border border-[var(--border-glow)]
                       text-[var(--text-primary)] rounded hover:bg-white/5 transition-colors"
          >
            try again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
