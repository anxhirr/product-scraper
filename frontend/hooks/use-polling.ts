import { useEffect, useRef, useState, useCallback } from "react"

interface UsePollingOptions<T> {
  pollFn: () => Promise<T>
  enabled: boolean
  interval?: number
  onSuccess?: (data: T) => void
  onError?: (error: Error) => void
  shouldStop?: (data: T) => boolean
  maxDuration?: number | null // Maximum polling duration in milliseconds (null/undefined = no timeout)
}

export function usePolling<T>({
  pollFn,
  enabled,
  interval = 5000, // Default 5 seconds
  onSuccess,
  onError,
  shouldStop,
  maxDuration = null, // No timeout by default
}: UsePollingOptions<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)
  const initialTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const startTimeRef = useRef<number | null>(null)
  const mountedRef = useRef(true)
  const isPollingRef = useRef(false) // Track if a poll is currently in progress

  // Use refs to store callbacks so they don't need to be in dependencies
  const pollFnRef = useRef(pollFn)
  const onSuccessRef = useRef(onSuccess)
  const onErrorRef = useRef(onError)
  const shouldStopRef = useRef(shouldStop)
  const enabledRef = useRef(enabled)

  // Update refs when values change
  useEffect(() => {
    pollFnRef.current = pollFn
    onSuccessRef.current = onSuccess
    onErrorRef.current = onError
    shouldStopRef.current = shouldStop
    enabledRef.current = enabled
  }, [pollFn, onSuccess, onError, shouldStop, enabled])

  const stopPolling = useCallback(() => {
    setIsPolling(false)
    isPollingRef.current = false
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
    if (initialTimeoutRef.current) {
      clearTimeout(initialTimeoutRef.current)
      initialTimeoutRef.current = null
    }
    startTimeRef.current = null
  }, [])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      stopPolling()
    }
  }, [stopPolling])

  useEffect(() => {
    // Only restart polling if enabled state actually changed
    if (!enabled) {
      stopPolling()
      return
    }

    // Don't restart if already polling
    if (isPollingRef.current || intervalRef.current) {
      return
    }

    // Start polling
    setIsPolling(true)
    startTimeRef.current = Date.now()

    // Initial poll after 1 second (increased from 500ms)
    initialTimeoutRef.current = setTimeout(() => {
      if (!mountedRef.current || !enabledRef.current || isPollingRef.current) return

      const poll = async () => {
        if (!mountedRef.current || !enabledRef.current || isPollingRef.current) return

        isPollingRef.current = true
        try {
          const result = await pollFnRef.current()
          if (!mountedRef.current) return

          setData(result)
          setError(null)
          onSuccessRef.current?.(result)

          // Check if we should stop polling
          if (shouldStopRef.current?.(result)) {
            stopPolling()
            return
          }
        } catch (err) {
          if (!mountedRef.current) return
          const error = err instanceof Error ? err : new Error("Polling error")
          setError(error)
          onErrorRef.current?.(error)
        } finally {
          isPollingRef.current = false
        }
      }

      poll()
    }, 1000)

    // Set up interval polling
    intervalRef.current = setInterval(() => {
      if (!mountedRef.current || !enabledRef.current) {
        stopPolling()
        return
      }

      // Skip if a poll is already in progress
      if (isPollingRef.current) {
        return
      }

      // Check max duration (only if maxDuration is set)
      if (maxDuration != null && startTimeRef.current && Date.now() - startTimeRef.current > maxDuration) {
        stopPolling()
        setError(new Error("Polling timeout: Maximum duration exceeded"))
        return
      }

      const poll = async () => {
        if (!mountedRef.current || !enabledRef.current || isPollingRef.current) return

        isPollingRef.current = true
        try {
          const result = await pollFnRef.current()
          if (!mountedRef.current) return

          setData(result)
          setError(null)
          onSuccessRef.current?.(result)

          // Check if we should stop polling
          if (shouldStopRef.current?.(result)) {
            stopPolling()
            return
          }
        } catch (err) {
          if (!mountedRef.current) return
          const error = err instanceof Error ? err : new Error("Polling error")
          setError(error)
          onErrorRef.current?.(error)
        } finally {
          isPollingRef.current = false
        }
      }

      poll()
    }, interval)

    // Set up max duration timeout (only if maxDuration is set)
    if (maxDuration != null) {
      timeoutRef.current = setTimeout(() => {
        if (mountedRef.current && enabledRef.current) {
          stopPolling()
          setError(new Error("Polling timeout: Maximum duration exceeded"))
        }
      }, maxDuration)
    }

    return () => {
      stopPolling()
    }
  }, [enabled, interval, maxDuration, stopPolling])

  return {
    data,
    error,
    isPolling,
    startPolling: () => {}, // No-op, polling is controlled by enabled prop
    stopPolling,
  }
}
