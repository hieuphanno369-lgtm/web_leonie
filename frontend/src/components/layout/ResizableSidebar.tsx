import { useState, useRef, useCallback, useEffect } from 'react'

type AccentColor = 'analytics' | 'work' | 'data' | 'home' | 'learn'

// Full literal class strings per color — Tailwind JIT can't see dynamically
// built names like `bg-${color}/40`, so we map them out explicitly.
const HANDLE_HOVER: Record<AccentColor, string> = {
  analytics: 'hover:bg-analytics/40 active:bg-analytics/60',
  work:      'hover:bg-work/40 active:bg-work/60',
  data:      'hover:bg-data/40 active:bg-data/60',
  home:      'hover:bg-home/40 active:bg-home/60',
  learn:     'hover:bg-learn/40 active:bg-learn/60',
}

interface Options {
  initial: number
  min?: number
  max?: number
  storageKey?: string
}

/**
 * Drag-to-resize sidebar width, mirroring the SQL Sandbox pattern. Width is
 * clamped to [min, max] and (optionally) persisted to localStorage so the
 * user's chosen width survives navigation + reload.
 */
export function useResizableSidebar({ initial, min = 200, max = 560, storageKey }: Options) {
  const [width, setWidth] = useState<number>(() => {
    if (storageKey && typeof localStorage !== 'undefined') {
      const saved = Number(localStorage.getItem(storageKey))
      if (Number.isFinite(saved) && saved >= min && saved <= max) return saved
    }
    return initial
  })
  const isDragging = useRef(false)

  const onDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    isDragging.current = true
    const startX = e.clientX
    const startW = width
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    const onMove = (mv: MouseEvent) => {
      if (!isDragging.current) return
      setWidth(Math.min(max, Math.max(min, startW + mv.clientX - startX)))
    }
    const onUp = () => {
      isDragging.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [width, min, max])

  useEffect(() => {
    if (storageKey) localStorage.setItem(storageKey, String(width))
  }, [storageKey, width])

  return { width, onDragStart }
}

interface HandleProps {
  onDragStart: (e: React.MouseEvent) => void
  color?: AccentColor
}

/** Thin draggable divider placed immediately after a resizable sidebar. */
export function ResizeHandle({ onDragStart, color = 'analytics' }: HandleProps) {
  return (
    <div
      onMouseDown={onDragStart}
      role="separator"
      aria-orientation="vertical"
      title="Kéo để đổi độ rộng"
      className={`w-1 flex-shrink-0 cursor-col-resize transition-colors ${HANDLE_HOVER[color]}`}
    />
  )
}
