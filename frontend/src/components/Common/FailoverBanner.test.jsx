import { describe, it, expect, vi } from 'vitest'
import { render, screen, act, fireEvent } from '@testing-library/react'
import FailoverBanner from './FailoverBanner'

describe('FailoverBanner', () => {
  it('renders nothing when idle', () => {
    render(<FailoverBanner reconnecting={false} failoverDetected={false} />)
    expect(screen.queryByTestId('failover-banner-reconnecting')).toBeNull()
    expect(screen.queryByTestId('failover-banner-recovered')).toBeNull()
  })

  it('shows reconnecting banner when reconnecting=true', () => {
    render(<FailoverBanner reconnecting={true} failoverDetected={false} />)
    expect(screen.getByTestId('failover-banner-reconnecting')).toBeInTheDocument()
    expect(screen.getByText(/Reconnecting/i)).toBeInTheDocument()
  })

  it('shows recovered banner when failoverDetected=true and not reconnecting', () => {
    render(<FailoverBanner reconnecting={false} failoverDetected={true} />)
    expect(screen.getByTestId('failover-banner-recovered')).toBeInTheDocument()
    expect(screen.getByText(/Back online/i)).toBeInTheDocument()
  })

  it('does not show dismiss button immediately', () => {
    render(<FailoverBanner reconnecting={false} failoverDetected={true} />)
    expect(screen.queryByTestId('failover-banner-dismiss')).toBeNull()
  })

  it('shows dismiss button after 5 seconds and clicking hides banner', async () => {
    vi.useFakeTimers()
    render(<FailoverBanner reconnecting={false} failoverDetected={true} />)
    expect(screen.queryByTestId('failover-banner-dismiss')).toBeNull()

    act(() => vi.advanceTimersByTime(5001))
    expect(screen.getByTestId('failover-banner-dismiss')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('failover-banner-dismiss'))
    expect(screen.queryByTestId('failover-banner-recovered')).toBeNull()

    vi.useRealTimers()
  })
})
