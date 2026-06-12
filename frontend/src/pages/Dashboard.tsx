import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CheckSquare, FlaskConical, Wrench, Bell, Database, Code2, Layers,
  TrendingUp, Cpu, Activity, Map, BookOpen, Flame,
  ArrowRight, Circle, AlertCircle, Clock, CheckCircle2, Wifi, WifiOff,
} from 'lucide-react'
import { fetchHealth } from '../api/client'
import { fetchTasks }  from '../api/tasks'
import { fetchEDA }    from '../api/eda'
import { fetchWIPs }   from '../api/wip'
import { fetchPerformanceSummary } from '../api/performance'
import type { Task, EDARequest, WIPItem, PerformanceSummary } from '../types'
import { MSG } from '../messages'

// ── tiny helpers ───────────────────────────────────────────────
function todayStr() { return new Date().toISOString().slice(0, 10) }

function isPast(date: string | null) { return !!date && date < todayStr() }
function isToday(date: string | null) { return date === todayStr() }

const PRIORITY_DOT: Record<string, string> = {
  high: 'bg-red-500', medium: 'bg-yellow-500', low: 'bg-gray-500',
}
const STATUS_COLOR: Record<string, string> = {
  todo: 'text-gray-400', in_progress: 'text-blue-400', done: 'text-green-400',
}

// ── sub-components ─────────────────────────────────────────────
function StatCard({ icon, label, value, sub, color }: {
  icon: React.ReactNode; label: string; value: string | number; sub?: string; color: string
}) {
  return (
    <div className={`bg-gray-900 border rounded-xl p-4 space-y-2 border-gray-800`}>
      <div className="flex items-center gap-2">
        <span className={color}>{icon}</span>
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-gray-600">{sub}</div>}
    </div>
  )
}

function SectionLink({ to, icon, label, color }: {
  to: string; icon: React.ReactNode; label: string; color: string
}) {
  return (
    <Link to={to}
      className="flex items-center gap-2 px-3 py-2.5 bg-gray-900 border border-gray-800 hover:border-gray-600 rounded-xl transition-colors group">
      <span className={color}>{icon}</span>
      <span className="text-sm text-gray-300 group-hover:text-white transition-colors flex-1">{label}</span>
      <ArrowRight size={12} className="text-gray-700 group-hover:text-gray-400 transition-colors" />
    </Link>
  )
}

function TaskRow({ task }: { task: Task }) {
  const overdue = isPast(task.due_date) && task.status !== 'done'
  return (
    <div className="flex items-start gap-2.5 py-2 border-b border-gray-800 last:border-0">
      <span className={`mt-0.5 w-2 h-2 rounded-full shrink-0 ${PRIORITY_DOT[task.priority]}`} />
      <div className="flex-1 min-w-0">
        <p className={`text-sm truncate ${task.status === 'done' ? 'line-through text-gray-600' : 'text-gray-200'}`}>
          {task.title}
        </p>
        {task.due_date && (
          <p className={`text-xs ${overdue ? 'text-red-400' : 'text-gray-600'}`}>
            {overdue ? '⚠ Overdue · ' : ''}{task.due_date}
          </p>
        )}
      </div>
      <span className={`text-xs shrink-0 ${STATUS_COLOR[task.status]}`}>{task.status.replace('_', ' ')}</span>
    </div>
  )
}

function WipBar({ item }: { item: WIPItem }) {
  const pct = item.progress
  const color = pct >= 80 ? 'bg-green-500' : pct >= 40 ? 'bg-blue-500' : 'bg-yellow-500'
  return (
    <div className="space-y-1 py-2 border-b border-gray-800 last:border-0">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-300 truncate flex-1">{item.task_title}</p>
        <span className="text-xs text-gray-500 ml-2">{pct}%</span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function CalendarStrip({ calendar }: { calendar: { date: string; status: string }[] }) {
  const last14 = calendar.slice(-14)
  return (
    <div className="flex gap-1 flex-wrap">
      {last14.map(d => (
        <div key={d.date} title={d.date}
          className={`w-4 h-4 rounded-sm ${
            d.status === 'hit'     ? 'bg-green-500' :
            d.status === 'partial' ? 'bg-yellow-500' : 'bg-gray-800'
          }`} />
      ))}
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────
export default function Dashboard() {
  const [tasks,  setTasks]  = useState<Task[]>([])
  const [edas,   setEdas]   = useState<EDARequest[]>([])
  const [wips,   setWips]   = useState<WIPItem[]>([])
  const [perf,   setPerf]   = useState<PerformanceSummary | null>(null)
  const [online, setOnline] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([
      fetchHealth().then(() => setOnline(true)).catch(() => setOnline(false)),
      fetchTasks().then(setTasks).catch(() => {}),
      fetchEDA().then(setEdas).catch(() => {}),
      fetchWIPs().then(setWips).catch(() => {}),
      fetchPerformanceSummary().then(setPerf).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  // derived
  const overdueTasks   = tasks.filter(t => isPast(t.due_date) && t.status !== 'done')
  const todayTasks     = tasks.filter(t => isToday(t.due_date) && t.status !== 'done')
  const inProgressTasks = tasks.filter(t => t.status === 'in_progress')
  const edaInProgress  = edas.filter(e => e.status === 'in_progress')
  const edaTodo        = edas.filter(e => e.status === 'todo')

  const priorityTasks = [
    ...overdueTasks,
    ...todayTasks,
    ...inProgressTasks.filter(t => !isToday(t.due_date) && !isPast(t.due_date)),
  ].filter((t, i, arr) => arr.findIndex(x => x.id === t.id) === i).slice(0, 6)

  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Chào buổi sáng'
    if (h < 18) return 'Chào buổi chiều'
    return 'Chào buổi tối'
  }

  const today = new Date().toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <div className="p-6 space-y-6 bg-gray-950 min-h-full">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{greeting()}, Leonie 👋</h1>
          <p className="text-gray-400 text-sm mt-1 capitalize">{today}</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          {online === null ? (
            <span className="text-gray-600 flex items-center gap-1"><Circle size={8} /> Connecting…</span>
          ) : online ? (
            <span className="text-green-400 flex items-center gap-1"><Wifi size={12} /> API online</span>
          ) : (
            <span className="text-red-400 flex items-center gap-1"><WifiOff size={12} /> API offline</span>
          )}
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={<AlertCircle size={16} />} label="Overdue tasks" color="text-red-400"
          value={overdueTasks.length}
          sub={overdueTasks.length > 0 ? 'cần xử lý ngay' : 'Không có'} />
        <StatCard icon={<Clock size={16} />} label="Due today" color="text-yellow-400"
          value={todayTasks.length}
          sub={`${inProgressTasks.length} in-progress`} />
        <StatCard icon={<Flame size={16} />} label="Perf streak" color="text-orange-400"
          value={perf ? `${perf.streak}d` : '—'}
          sub={perf ? `${perf.tasks_done} tasks done` : MSG.loading} />
        <StatCard icon={<Wrench size={16} />} label="WIP avg" color="text-blue-400"
          value={perf ? `${Math.round(perf.wip_avg_progress)}%` : '—'}
          sub={`${wips.length} items active`} />
      </div>

      {/* Main 2-col */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Tasks priority list */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
              <CheckSquare size={14} className="text-blue-400" /> Priority Tasks
            </h2>
            <Link to="/work/tasks" className="text-xs text-gray-600 hover:text-blue-400 flex items-center gap-1">
              All <ArrowRight size={10} />
            </Link>
          </div>
          {loading ? (
            <p className="text-xs text-gray-600 py-4">{MSG.loading}</p>
          ) : priorityTasks.length === 0 ? (
            <div className="flex items-center gap-2 py-4 text-green-400 text-sm">
              <CheckCircle2 size={16} /> Không có task urgent hôm nay 🎉
            </div>
          ) : (
            <div>{priorityTasks.map(t => <TaskRow key={t.id} task={t} />)}</div>
          )}
        </div>

        {/* WIP progress */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
              <Wrench size={14} className="text-yellow-400" /> Work In Progress
            </h2>
            <Link to="/work/wip" className="text-xs text-gray-600 hover:text-blue-400 flex items-center gap-1">
              All <ArrowRight size={10} />
            </Link>
          </div>
          {loading ? (
            <p className="text-xs text-gray-600 py-4">{MSG.loading}</p>
          ) : wips.length === 0 ? (
            <p className="text-xs text-gray-600 py-4">{MSG.emptyWipList}</p>
          ) : (
            <div>{wips.slice(0, 5).map(w => <WipBar key={w.id} item={w} />)}</div>
          )}
        </div>
      </div>

      {/* 3-col row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* Performance calendar */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
              <Activity size={14} className="text-orange-400" /> Performance
            </h2>
            <Link to="/analytics/perf" className="text-xs text-gray-600 hover:text-blue-400 flex items-center gap-1">
              Detail <ArrowRight size={10} />
            </Link>
          </div>
          {perf ? (
            <>
              <div className="flex items-center gap-3">
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-400">{perf.streak}</div>
                  <div className="text-xs text-gray-600">day streak</div>
                </div>
                <div className="flex-1 space-y-1 text-xs text-gray-500">
                  <div className="flex justify-between"><span>Tasks done</span><span className="text-gray-300">{perf.tasks_done}</span></div>
                  <div className="flex justify-between"><span>EDA done</span><span className="text-gray-300">{perf.eda_done}</span></div>
                  <div className="flex justify-between"><span>KPI logs</span><span className="text-gray-300">{perf.kpi_logs}</span></div>
                </div>
              </div>
              {perf.calendar.length > 0 && <CalendarStrip calendar={perf.calendar} />}
            </>
          ) : (
            <p className="text-xs text-gray-600">{MSG.loading}</p>
          )}
        </div>

        {/* Learning — đang phát triển */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-4">
          <h2 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
            <Map size={14} className="text-purple-400" /> Learning
          </h2>

          <div
            title="Tính năng đang được phát triển"
            className="flex flex-col items-center justify-center text-center gap-2 py-6 rounded-lg
                       bg-gradient-to-r from-learn/10 to-home/10 border border-learn/20
                       text-gray-400 cursor-not-allowed select-none"
          >
            <BookOpen size={20} className="text-learn/70" />
            <p className="text-sm font-semibold text-gray-300">Sắp ra mắt</p>
            <p className="text-[11px] text-gray-600 px-2">
              Lộ trình kỹ năng &amp; quiz hằng ngày đang được phát triển.
            </p>
            <span className="text-[9px] font-semibold uppercase tracking-wider text-learn/80
                             bg-learn/10 border border-learn/20 rounded px-1.5 py-0.5">Soon</span>
          </div>
        </div>

        {/* EDA requests */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
              <FlaskConical size={14} className="text-green-400" /> EDA Requests
            </h2>
            <Link to="/work/eda" className="text-xs text-gray-600 hover:text-blue-400 flex items-center gap-1">
              All <ArrowRight size={10} />
            </Link>
          </div>
          <div className="flex gap-4 text-center">
            <div className="flex-1 bg-gray-800 rounded-lg py-2">
              <div className="text-lg font-bold text-blue-400">{edaInProgress.length}</div>
              <div className="text-[10px] text-gray-600">in-progress</div>
            </div>
            <div className="flex-1 bg-gray-800 rounded-lg py-2">
              <div className="text-lg font-bold text-gray-300">{edaTodo.length}</div>
              <div className="text-[10px] text-gray-600">todo</div>
            </div>
          </div>
          {edaInProgress.slice(0, 3).map(e => (
            <div key={e.id} className="text-xs text-gray-400 truncate border-l-2 border-blue-600 pl-2">
              {e.title}
              <span className="text-gray-600 ml-1">· {e.requester}</span>
            </div>
          ))}
          {edaInProgress.length === 0 && edaTodo.length === 0 && (
            <p className="text-xs text-gray-600">{MSG.emptyEdaRequests}</p>
          )}
        </div>
      </div>

      {/* Quick nav */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest">Quick Access</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          <div className="space-y-2">
            <p className="text-[10px] text-gray-700 uppercase tracking-widest pl-1">Work</p>
            <SectionLink to="/work/tasks"   icon={<CheckSquare size={13} />}  label="Task Manager"   color="text-blue-400" />
            <SectionLink to="/work/eda"     icon={<FlaskConical size={13} />} label="EDA Tracker"    color="text-green-400" />
            <SectionLink to="/work/wip"     icon={<Wrench size={13} />}       label="WIP Builder"    color="text-yellow-400" />
            <SectionLink to="/work/discord" icon={<Bell size={13} />}         label="Discord Notify" color="text-indigo-400" />
          </div>
          <div className="space-y-2">
            <p className="text-[10px] text-gray-700 uppercase tracking-widest pl-1">Data</p>
            <SectionLink to="/data/sql"      icon={<Database size={13} />}  label="SQL Sandbox"      color="text-cyan-400" />
            <SectionLink to="/data/snippets" icon={<Code2 size={13} />}     label="Snippet Library"  color="text-purple-400" />
            <SectionLink to="/data/fabric"   icon={<Layers size={13} />}    label="Fabric Views"     color="text-blue-400" />
          </div>
          <div className="space-y-2">
            <p className="text-[10px] text-gray-700 uppercase tracking-widest pl-1">Analytics</p>
            <SectionLink to="/analytics/kpi"  icon={<TrendingUp size={13} />} label="KPI Tracker" color="text-green-400" />
            <SectionLink to="/analytics/ml"   icon={<Cpu size={13} />}        label="ML Studio"   color="text-pink-400" />
            <SectionLink to="/analytics/perf" icon={<Activity size={13} />}   label="Performance" color="text-orange-400" />
          </div>
        </div>
      </div>

    </div>
  )
}
