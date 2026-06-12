import { useEffect, useRef } from 'react'
import { EditorView, keymap, highlightActiveLine, lineNumbers } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { sql, StandardSQL } from '@codemirror/lang-sql'
import { oneDark } from '@codemirror/theme-one-dark'
import {
  defaultKeymap, indentWithTab, history, historyKeymap,
} from '@codemirror/commands'
import {
  autocompletion, completionKeymap, closeBracketsKeymap,
} from '@codemirror/autocomplete'
import { indentOnInput, bracketMatching, foldKeymap } from '@codemirror/language'
import { searchKeymap } from '@codemirror/search'

// VINA BREW table + column names for autocomplete
const VINA_BREW_SCHEMA: Record<string, string[]> = {
  dim_date:          ['date_key','date','year','month','quarter','month_name','day_of_week','is_weekend','is_holiday','season'],
  dim_product:       ['product_id','product_name','brand','category','sub_category','sku_code','volume_ml','gross_price','net_price','cost','is_active'],
  dim_channel:       ['channel_id','channel_name','channel_type','commission_rate'],
  dim_store:         ['store_id','store_name','region','province','channel_id','tier','is_active'],
  fact_sales:        ['sale_id','date_key','product_id','store_id','channel_id','gross_amount','discount_amount','net_amount','quantity','trade_spend','target_amount'],
  fact_transactions: ['txn_id','date_key','product_id','store_id','scan_count','brew_points_earned','brew_points_redeemed','basket_size','is_new_buyer','app_channel'],
}

// Custom dark theme matching the app palette
const appTheme = EditorView.theme({
  '&': {
    backgroundColor: '#0d1117',
    color: '#c9d1d9',
    height: '100%',
    fontSize: '13px',
    fontFamily: "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
  },
  '.cm-content': { caretColor: '#58a6ff', padding: '12px 0' },
  '.cm-line': { padding: '0 16px' },
  '.cm-cursor': { borderLeftColor: '#58a6ff' },
  '.cm-activeLine': { backgroundColor: '#ffffff08' },
  '.cm-gutters': { backgroundColor: '#0d1117', borderRight: '1px solid #ffffff0d', color: '#484f58' },
  '.cm-activeLineGutter': { backgroundColor: '#ffffff08' },
  '.cm-selectionBackground, ::selection': { backgroundColor: '#264f7840 !important' },
  '.cm-tooltip': { backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '6px' },
  '.cm-tooltip-autocomplete > ul > li': { padding: '2px 8px', fontSize: '12px' },
  '.cm-tooltip-autocomplete > ul > li[aria-selected]': { backgroundColor: '#1f6feb', color: '#fff' },
}, { dark: true })

interface Props {
  value: string
  onChange: (v: string) => void
  onRun: () => void
}

export default function SqlEditor({ value, onChange, onRun }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewRef      = useRef<EditorView | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const runCmd = keymap.of([
      { key: 'Shift-Enter', run: () => { onRun(); return true } },
      { key: 'Ctrl-Enter',  run: () => { onRun(); return true } },
    ])

    const state = EditorState.create({
      doc: value,
      extensions: [
        lineNumbers(),
        history(),
        highlightActiveLine(),
        indentOnInput(),
        bracketMatching(),
        autocompletion(),
        sql({
          dialect: StandardSQL,
          schema: VINA_BREW_SCHEMA,
          upperCaseKeywords: true,
        }),
        oneDark,
        appTheme,
        keymap.of([
          ...defaultKeymap,
          ...historyKeymap,
          ...completionKeymap,
          ...closeBracketsKeymap,
          ...foldKeymap,
          ...searchKeymap,
          indentWithTab,
        ]),
        runCmd,
        EditorView.updateListener.of(update => {
          if (update.docChanged) onChange(update.state.doc.toString())
        }),
        EditorView.lineWrapping,
      ],
    })

    const view = new EditorView({ state, parent: containerRef.current })
    viewRef.current = view

    return () => { view.destroy(); viewRef.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Sync external value changes (e.g. inject from exercises)
  useEffect(() => {
    const view = viewRef.current
    if (!view) return
    const current = view.state.doc.toString()
    if (current !== value) {
      view.dispatch({
        changes: { from: 0, to: current.length, insert: value },
      })
    }
  }, [value])

  return <div ref={containerRef} className="h-full overflow-hidden" />
}
