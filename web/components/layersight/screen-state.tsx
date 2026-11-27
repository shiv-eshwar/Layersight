import type { ReactNode } from "react"

export type ScreenStateName = "loading" | "empty" | "error" | "ready"

type ScreenStateProps = {
  state: ScreenStateName
  emptyTitle?: string
  emptyBody?: string
  errorDetail?: string
  onRetry?: () => void
  children?: ReactNode
}

export function ScreenState({
  state,
  emptyTitle = "Nothing here yet",
  emptyBody = "Upload emails (.eml, .txt, or .zip) to classify them and open this screen.",
  errorDetail = "This screen could not load.",
  onRetry,
  children,
}: ScreenStateProps) {
  if (state === "loading") {
    return <div data-testid="screen-loading">Loading this screen.</div>
  }
  if (state === "empty") {
    return (
      <div data-testid="screen-empty">
        <p>{emptyTitle}</p>
        <p>{emptyBody}</p>
      </div>
    )
  }
  if (state === "error") {
    return (
      <div data-testid="screen-error">
        <p>{errorDetail}</p>
        <button type="button" data-testid="retry" onClick={onRetry}>
          Retry
        </button>
      </div>
    )
  }
  return <div data-testid="screen-ready">{children}</div>
}
