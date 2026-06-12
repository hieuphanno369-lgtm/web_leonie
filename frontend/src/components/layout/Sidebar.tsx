import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  CheckSquare,
  BellRing,
  Code2,
  TrendingUp,
  BrainCircuit,
  Sparkles,
  NotebookPen,
  Workflow,
} from 'lucide-react'
import type { NavCategory } from '../../types'
import HoneyBadgerLogo from './HoneyBadgerLogo'

export const ICON_MAP = {
  LayoutDashboard, CheckSquare, BellRing, Code2,
  TrendingUp, BrainCircuit, NotebookPen, Workflow,
}

const NAV: NavCategory[] = [
  {
    id: 'home', label: 'HOME', color: '#00d4ff',
    items: [
      { path: '/',                 label: 'Dashboard',   iconName: 'LayoutDashboard', color: '#00d4ff' },
    ],
  },
  {
    id: 'work', label: 'WORK', color: '#34d399',
    items: [
      { path: '/work/tasks',       label: 'Task Manager',   iconName: 'CheckSquare',   color: '#34d399' },
      { path: '/work/notes',       label: 'Quick Notes',    iconName: 'NotebookPen',   color: '#34d399' },
      { path: '/work/discord',     label: 'Discord Notify', iconName: 'BellRing',      color: '#34d399' },
    ],
  },
  {
    id: 'analytics', label: 'ANALYTICS', color: '#fbbf24',
    items: [
      { path: '/analytics/kpi',   label: 'KPI Tracker', iconName: 'TrendingUp',   color: '#fbbf24' },
      { path: '/analytics/ml',    label: 'ML Studio',   iconName: 'BrainCircuit', color: '#fbbf24' },
      { path: '/data/automation', label: 'Automation',  iconName: 'Workflow',     color: '#fbbf24' },
    ],
  },
  {
    id: 'data', label: 'SQL SANDBOX', color: '#60a5fa',
    items: [
      { path: '/data/snippets', label: 'Snippet Library', iconName: 'Code2',    color: '#60a5fa' },
    ],
  },
]

export default function Sidebar() {
  return (
    <aside className="fixed top-0 left-0 h-full w-56 bg-secondary border-r border-white/5 z-40 flex flex-col overflow-y-auto">
      {/* Logo */}
      <div className="p-4 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center p-1">
            <HoneyBadgerLogo size={28} />
          </div>
          <div>
            <p className="text-white font-semibold text-sm leading-none">Leonie</p>
            <p className="text-home/50 text-xs mt-0.5 font-mono">Work Hub · v1.0</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3">
        {NAV.map((cat) => (
          <div key={cat.id} className="mb-3">
            <p
              className="px-3 mb-1 text-[10px] font-semibold tracking-widest uppercase"
              style={{ color: cat.color + '80' }}
            >
              {cat.label}
            </p>
            {cat.items.map(({ path, label, iconName, color }) => {
              const Icon = ICON_MAP[iconName as keyof typeof ICON_MAP]
              return (
                <NavLink
                  key={path}
                  to={path}
                  end={path === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all mb-0.5 ${
                      isActive
                        ? 'bg-white/5 text-white border border-white/10'
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      {Icon && (
                        <Icon size={15} style={{ color: isActive ? color : undefined }} />
                      )}
                      <span>{label}</span>
                      {isActive && (
                        <span
                          className="ml-auto w-1.5 h-1.5 rounded-full flex-shrink-0"
                          style={{ background: color, boxShadow: `0 0 6px ${color}` }}
                        />
                      )}
                    </>
                  )}
                </NavLink>
              )
            })}
          </div>
        ))}
      </nav>

      {/* Leonie AI button */}
      <div className="p-3 border-t border-white/5 flex-shrink-0">
        <button
          disabled
          title="Tính năng đang được phát triển"
          className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm
                     bg-gradient-to-r from-learn/10 to-home/10 border border-learn/20
                     text-gray-400 cursor-not-allowed"
        >
          <Sparkles size={15} className="text-learn/70 flex-shrink-0" />
          <div className="text-left flex-1">
            <p className="font-semibold text-xs leading-none text-gray-300">Leonie AI</p>
            <p className="text-[10px] text-gray-600 mt-0.5">Context-aware agent</p>
          </div>
          <span className="text-[9px] font-semibold uppercase tracking-wider text-learn/80
                           bg-learn/10 border border-learn/20 rounded px-1.5 py-0.5">Soon</span>
        </button>
      </div>
    </aside>
  )
}
