import { useState, useEffect, useCallback } from 'react'
import { Send, Settings, Zap, Check } from 'lucide-react'
import type { DiscordSettings } from '../../types'
import { fetchDiscordSettings, saveDiscordSettings, sendDiscordMessage, checkDiscordRules } from '../../api/discord'
import { MSG } from '../../messages'

type Tab = 'manual' | 'rules' | 'settings'

const PREFIX_OPTIONS = [
  { value: '',        label: '(no prefix)' },
  { value: '✅ ',    label: '✅ Done' },
  { value: '⚠️ ',   label: '⚠️ Alert' },
  { value: '📊 ',   label: '📊 Report' },
  { value: '🔔 ',   label: '🔔 Reminder' },
]

export default function DiscordNotify() {
  const [tab,          setTab]          = useState<Tab>('manual')
  const [settings,     setSettings]     = useState<DiscordSettings | null>(null)
  const [webhookInput, setWebhookInput] = useState('')
  const [message,      setMessage]      = useState('')
  const [prefix,       setPrefix]       = useState('')
  const [status,       setStatus]       = useState('')   // inline feedback
  const [error,        setError]        = useState('')
  const [saving,       setSaving]       = useState(false)

  const load = useCallback(async () => {
    try {
      const s = await fetchDiscordSettings()
      setSettings(s)
      setWebhookInput(s.webhook_url ?? '')
    } catch { setError(MSG.apiUnreachable) }
  }, [])

  useEffect(() => { load() }, [load])

  // Auto-check when visiting Rules tab and webhook is set
  useEffect(() => {
    if (tab === 'rules' && settings?.webhook_url) {
      checkDiscordRules().catch(() => {/* silent — webhook might be invalid */})
    }
  }, [tab, settings?.webhook_url])

  async function handleSend() {
    if (!message.trim()) { setError(MSG.messageEmpty); return }
    if (!settings?.webhook_url) { setError(MSG.setWebhookFirst); return }
    setError(''); setSaving(true)
    try {
      await sendDiscordMessage(prefix + message.trim())
      setStatus(MSG.sent)
      setMessage('')
      setTimeout(() => setStatus(''), 3000)
    } catch { setError(MSG.sendWebhookFailed) }
    finally { setSaving(false) }
  }

  async function handleSaveSettings() {
    setSaving(true); setError('')
    try {
      const updated = await saveDiscordSettings({ ...settings, webhook_url: webhookInput || null })
      setSettings(updated)
      setStatus(MSG.saved)
      setTimeout(() => setStatus(''), 3000)
    } catch { setError(MSG.saveSettingsFailed) }
    finally { setSaving(false) }
  }

  async function handleTest() {
    if (!webhookInput) { setError(MSG.enterWebhookFirst); return }
    setSaving(true); setError('')
    try {
      // Save first, then send test
      const updated = await saveDiscordSettings({ webhook_url: webhookInput })
      setSettings(updated)
      await sendDiscordMessage('🔔 Leonie webhook test — OK')
      setStatus(MSG.testSent)
      setTimeout(() => setStatus(''), 3000)
    } catch { setError(MSG.testWebhookFailed) }
    finally { setSaving(false) }
  }

  async function handleToggleRule(rule: 'rule_overdue' | 'rule_done' | 'rule_summary') {
    if (!settings) return
    const prev = settings
    const updated = { ...settings, [rule]: !settings[rule] }
    setSettings(updated)
    try {
      const saved = await saveDiscordSettings(updated)
      setSettings(saved)
    } catch {
      setSettings(prev)  // rollback on failure
      setError(MSG.saveRuleFailed)
    }
  }

  const tabCls = (t: Tab) =>
    `flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-all ${
      tab === t
        ? 'border-work text-work'
        : 'border-transparent text-gray-500 hover:text-gray-300'
    }`

  const fmtDate = (iso: string | null) => {
    if (!iso) return 'Never'
    return new Date(iso).toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })
  }

  return (
    <div className="flex-1 p-5 overflow-y-auto max-w-xl">
      <h1 className="text-base font-semibold text-white mb-4">Discord Notify</h1>

      {!settings?.webhook_url && tab !== 'settings' && (
        <div className="bg-warning/5 border border-warning/20 text-warning text-xs px-3 py-2 rounded-lg mb-4">
          Chưa đặt Webhook URL — vào tab <button className="underline" onClick={() => setTab('settings')}>Settings</button> trước.
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-white/5 mb-5">
        <button className={tabCls('manual')}  onClick={() => { setError(''); setStatus(''); setTab('manual') }}>
          <Send size={12} /> Manual
        </button>
        <button className={tabCls('rules')}   onClick={() => { setError(''); setStatus(''); setTab('rules') }}>
          <Zap size={12} /> Auto Rules
        </button>
        <button className={tabCls('settings')} onClick={() => { setError(''); setStatus(''); setTab('settings') }}>
          <Settings size={12} /> Settings
        </button>
      </div>

      {error  && <p className="text-danger text-xs mb-3">{error}</p>}
      {status && <p className="text-work text-xs mb-3">{status}</p>}

      {/* Manual Tab */}
      {tab === 'manual' && (
        <div>
          <div className="mb-3">
            <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Prefix</label>
            <select className="input-base" value={prefix} onChange={e => setPrefix(e.target.value)}>
              {PREFIX_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="mb-4">
            <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Message</label>
            <textarea
              className="input-base resize-none"
              rows={5}
              placeholder={MSG.placeholderMessage}
              value={message}
              onChange={e => setMessage(e.target.value)}
            />
          </div>
          {message && (
            <div className="bg-secondary border border-white/5 rounded-lg px-3 py-2 mb-4">
              <p className="text-[10px] text-gray-600 mb-1">Preview</p>
              <p className="text-xs text-gray-300 whitespace-pre-wrap">{prefix}{message}</p>
            </div>
          )}
          <button
            onClick={handleSend}
            disabled={saving}
            className="btn-primary w-full flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <Send size={13} /> {saving ? 'Sending...' : 'Send to Discord'}
          </button>
        </div>
      )}

      {/* Rules Tab */}
      {tab === 'rules' && settings && (
        <div>
          <p className="text-xs text-gray-500 mb-4">
            Last checked: <span className="text-gray-400">{fmtDate(settings.last_checked)}</span>
          </p>

          {[
            { key: 'rule_overdue' as const, label: 'Task overdue',     desc: 'Send a summary of tasks past their due date' },
            { key: 'rule_done'    as const, label: 'Status to Done',    desc: 'Notify when a task transitions to Done' },
            { key: 'rule_summary' as const, label: 'Daily summary',     desc: 'Daily summary (requires app to be open)' },
          ].map(({ key, label, desc }) => (
            <div
              key={key}
              className="flex items-center justify-between gap-4 py-3 border-b border-white/5"
            >
              <div>
                <p className="text-sm text-white">{label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
              </div>
              <button
                onClick={() => handleToggleRule(key)}
                className={`w-10 h-5 rounded-full transition-all flex-shrink-0 relative ${
                  settings[key] ? 'bg-work' : 'bg-white/10'
                }`}
              >
                <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-all ${
                  settings[key] ? 'left-5' : 'left-0.5'
                }`} />
              </button>
            </div>
          ))}

          <button
            onClick={() => {
              if (!settings.webhook_url) { setError(MSG.setWebhookFirst); return }
              checkDiscordRules()
                .then(r => setStatus(MSG.checkDone(r.sent)))
                .catch(() => setError(MSG.checkFailed))
            }}
            className="btn-ghost w-full mt-4 flex items-center justify-center gap-1.5 text-xs"
          >
            <Check size={12} /> Run check now
          </button>
        </div>
      )}

      {/* Settings Tab */}
      {tab === 'settings' && (
        <div>
          <div className="mb-4">
            <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">
              Discord Webhook URL
            </label>
            <input
              className="input-base font-mono text-xs"
              placeholder="https://discord.com/api/webhooks/..."
              value={webhookInput}
              onChange={e => setWebhookInput(e.target.value)}
            />
            <p className="text-[11px] text-gray-600 mt-1.5">
              Server Settings &gt; Integrations &gt; Webhooks &gt; Copy URL
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSaveSettings}
              disabled={saving}
              className="btn-primary flex-1 flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Check size={13} /> {saving ? 'Saving...' : 'Save'}
            </button>
            <button
              onClick={handleTest}
              disabled={saving}
              className="btn-ghost flex-1 flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Send size={13} /> Test
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
