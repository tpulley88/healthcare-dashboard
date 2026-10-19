import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  failed: boolean
}

/**
 * Catches an error while showing a page, so one broken page doesn't blank the whole app.
 *
 * The header and sidebar stay usable. App gives this a new key on each navigation,
 * so moving to another page tries again.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: unknown) {
    // Only the kind of error: the page may have been showing patient data.
    console.error('Page failed to render:', error instanceof Error ? error.name : typeof error)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <section className="notice notice-error" role="alert">
        <p>This page couldn’t be shown. Reload to try again, or choose another page.</p>
        <button type="button" className="button" onClick={() => window.location.reload()}>
          Reload
        </button>
      </section>
    )
  }
}
