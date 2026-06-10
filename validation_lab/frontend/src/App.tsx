import React, { useState, useCallback } from 'react'
import {
  Upload, CheckCircle2, XCircle, Clock, AlertTriangle,
  ChevronDown, ChevronRight, Download, FileText, Cpu,
  BarChart3, GitCompare
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { cn } from '@/lib/utils'

// ── Types ─────────────────────────────────────────────────────────────────────
type Stage = {
  name: string
  status: 'SUCCESS' | 'ERROR' | 'PENDING'
  time_ms: number
  result: string
  error?: string
  extra_data?: Record<string, unknown>
}

type Transaction = {
  date: string
  narration: string
  debit: string | number | null
  credit: string | number | null
  balance: string | number | null
}

type PipelineResult = {
  success: boolean
  stages: Stage[]
  final_transactions: Transaction[]
  error?: string
}

// ── Ground Truth CSV parser ────────────────────────────────────────────────────
function parseCsv(text: string): Transaction[] {
  const lines = text.split('\n').filter(l => l.trim())
  if (lines.length < 2) return []
  return lines.slice(1).map(l => {
    const vals = l.split(',')
    return {
      date:      (vals[0] ?? '').trim(),
      narration: (vals[1] ?? '').trim(),
      debit:     (vals[2] ?? '').trim() || null,
      credit:    (vals[3] ?? '').trim() || null,
      balance:   (vals[4] ?? '').trim() || null,
    }
  }).filter(t => t.date)
}

// ── Ground Truth diff engine ───────────────────────────────────────────────────
function diffTransactions(extracted: Transaction[], gt: Transaction[]) {
  const matched   = new Set<number>()
  const missing:  Transaction[] = []
  const extra:    Transaction[] = []

  for (const t of gt) {
    const idx = extracted.findIndex((e, i) =>
      !matched.has(i) && e.date === t.date && String(e.credit) === String(t.credit) && String(e.debit) === String(t.debit)
    )
    if (idx === -1) missing.push(t)
    else matched.add(idx)
  }

  extracted.forEach((e, i) => { if (!matched.has(i)) extra.push(e) })

  const accuracy = gt.length === 0 ? 0 : Math.round(((gt.length - missing.length) / gt.length) * 1000) / 10

  return { missing, extra, accuracy }
}

// ── Stage icon ─────────────────────────────────────────────────────────────────
function StageIcon({ status }: { status: Stage['status'] }) {
  if (status === 'SUCCESS') return <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
  if (status === 'ERROR')   return <XCircle      className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
  return                           <Clock        className="w-4 h-4 text-gray-400 shrink-0 mt-0.5 animate-spin" />
}

// ── Upload zone ────────────────────────────────────────────────────────────────
function UploadZone({
  id, label, accept, onFile, fileName, hint
}: {
  id: string; label: string; accept: string
  onFile: (f: File) => void; fileName?: string; hint?: string
}) {
  const [drag, setDrag] = useState(false)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDrag(false)
    const f = e.dataTransfer.files?.[0]
    if (f) onFile(f)
  }, [onFile])

  return (
    <label
      htmlFor={id}
      onDragOver={e => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed",
        "cursor-pointer transition-all p-6 text-center",
        drag
          ? "border-indigo-400 bg-indigo-50"
          : fileName
            ? "border-emerald-300 bg-emerald-50"
            : "border-gray-200 bg-gray-50 hover:border-indigo-300 hover:bg-indigo-50/40"
      )}
    >
      <input id={id} type="file" accept={accept} className="hidden" onChange={e => { const f = e.target.files?.[0]; if (f) onFile(f) }} />
      {fileName ? (
        <>
          <CheckCircle2 className="w-8 h-8 text-emerald-500" />
          <span className="text-sm font-medium text-emerald-700">{fileName}</span>
        </>
      ) : (
        <>
          <Upload className="w-8 h-8 text-gray-400" />
          <span className="text-sm font-semibold text-gray-700">{label}</span>
          {hint && <span className="text-xs text-gray-400">{hint}</span>}
        </>
      )}
    </label>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [loading,        setLoading]       = useState(false)
  const [result,         setResult]        = useState<PipelineResult | null>(null)
  const [gtTxns,         setGtTxns]        = useState<Transaction[]>([])
  const [gtFileName,     setGtFileName]    = useState<string>('')
  const [pdfFileName,    setPdfFileName]   = useState<string>('')
  const [debugOpen,      setDebugOpen]     = useState(false)
  const [searchQ,        setSearchQ]       = useState('')

  // Process PDF via backend
  const processPdf = async (file: File) => {
    setPdfFileName(file.name)
    setLoading(true)
    setResult(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res  = await fetch('/api/process', { method: 'POST', body: fd })
      const data = await res.json() as PipelineResult
      setResult(data)
    } catch (e) {
      setResult({ success: false, stages: [], final_transactions: [], error: String(e) })
    } finally {
      setLoading(false)
    }
  }

  const loadGt = (file: File) => {
    setGtFileName(file.name)
    const reader = new FileReader()
    reader.onload = e => setGtTxns(parseCsv(e.target?.result as string))
    reader.readAsText(file)
  }

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(result?.final_transactions ?? [], null, 2)], { type: 'application/json' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a'); a.href = url; a.download = 'transactions.json'; a.click()
    URL.revokeObjectURL(url)
  }

  // Helpers
  const stages      = result?.final_transactions ? result.stages : []
  const txns        = result?.final_transactions ?? []
  const detection   = stages.find(s => s.name === 'PDF Classification')
  const bankStage   = stages.find(s => s.name === 'Bank Detection')
  const bankJson    = bankStage?.extra_data?.identity_json as Record<string, unknown> | undefined
  const pdfType     = detection?.result ?? 'Unknown'
  const isScanned   = pdfType === 'scanned'
  const ocrStage    = stages.find(s => s.name === 'OCR Engine')
  const adapterStage = stages.find(s => s.name === 'OCR Adapter')
  const parserInput = (
    stages.find(s => s.name === 'PDF Text Extraction')?.extra_data?.full_text
    ?? adapterStage?.extra_data?.full_text
    ?? ''
  ) as string
  const llmRaw      = stages.find(s => s.name === 'Transaction Extraction (LLM)')?.extra_data?.raw_response as string | undefined
  const diff        = gtTxns.length > 0 && txns.length > 0 ? diffTransactions(txns, gtTxns) : null

  const filteredTxns = txns.filter(t =>
    searchQ === '' ||
    t.narration?.toLowerCase().includes(searchQ.toLowerCase()) ||
    t.date?.toLowerCase().includes(searchQ.toLowerCase())
  )

  const totalDebits  = txns.reduce((s, t) => s + (parseFloat(String(t.debit  || 0)) || 0), 0)
  const totalCredits = txns.reduce((s, t) => s + (parseFloat(String(t.credit || 0)) || 0), 0)

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      {/* ── HEADER ──────────────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
              <Cpu className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900 leading-tight">Bank Statement Parser</h1>
              <p className="text-xs text-gray-400">Validation Lab · OCR + Parser Integration Tester</p>
            </div>
          </div>
          {result && (
            <div className="flex items-center gap-3">
              <span className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
                isScanned ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"
              )}>
                <span className={cn("w-1.5 h-1.5 rounded-full", isScanned ? "bg-amber-500" : "bg-emerald-500")} />
                {isScanned ? '🟡 Scanned PDF → OCR → Parser' : '🟢 Digital PDF → Parser'}
              </span>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* ── UPLOAD ROW ──────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <UploadZone
            id="pdf-upload"
            label="Upload Bank Statement PDF"
            accept=".pdf"
            onFile={processPdf}
            fileName={loading ? `Processing ${pdfFileName}…` : pdfFileName}
            hint="Drag & drop or click — digital and scanned both supported"
          />
          <UploadZone
            id="gt-upload"
            label="Upload Ground Truth CSV"
            accept=".csv"
            onFile={loadGt}
            fileName={gtFileName}
            hint="Columns: date, narration, debit, credit, balance"
          />
        </div>

        {/* ── LOADING ─────────────────────────────────────────────────────── */}
        {loading && (
          <div className="flex items-center justify-center gap-3 rounded-xl bg-indigo-50 border border-indigo-200 p-8">
            <Clock className="w-5 h-5 text-indigo-500 animate-spin" />
            <span className="text-sm font-medium text-indigo-700">Running pipeline stages…</span>
          </div>
        )}

        {/* ── ERROR BANNER ─────────────────────────────────────────────────── */}
        {result && !result.success && result.error && (
          <div className="flex items-start gap-3 rounded-xl bg-red-50 border border-red-200 p-4">
            <XCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-red-700">Pipeline Error</p>
              <p className="text-xs text-red-600 mt-1 font-mono">{result.error}</p>
            </div>
          </div>
        )}

        {result && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* ── LEFT: PIPELINE INSPECTOR + DEBUG ───────────────────────── */}
            <div className="space-y-4">
              {/* Processing Summary */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-indigo-500" />
                    Processing Summary
                  </CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-3">
                  {[
                    { label: 'File', value: pdfFileName, span: true },
                    { label: 'Transactions', value: txns.length },
                    { label: 'Total Time', value: `${stages.reduce((s, st) => s + st.time_ms, 0)}ms` },
                    { label: 'PDF Type', value: pdfType },
                    { label: 'Bank', value: (bankJson?.institution_name as string) || '—' },
                    { label: 'Family', value: (bankJson?.document_family as string) || '—' },
                  ].map(({ label, value, span }) => (
                    <div key={label} className={cn("rounded-lg bg-gray-50 border border-gray-100 p-3", span && "col-span-2")}>
                      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
                      <p className="text-sm font-semibold text-gray-900 truncate">{String(value)}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Pipeline Inspector */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-indigo-500" />
                    Pipeline Inspector
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {stages.map((stage, idx) => (
                    <div key={idx} className={cn(
                      "flex items-start gap-3 p-3 rounded-lg border text-sm",
                      stage.status === 'SUCCESS' ? "border-emerald-100 bg-emerald-50/50" : "border-red-100 bg-red-50/50"
                    )}>
                      <StageIcon status={stage.status} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium text-gray-900 text-xs truncate">{stage.name}</span>
                          <span className="text-[10px] text-gray-400 shrink-0 flex items-center gap-0.5">
                            <Clock className="w-2.5 h-2.5" />{stage.time_ms}ms
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-500 mt-0.5 truncate">{stage.result}</p>
                        {stage.error && <p className="text-[10px] text-red-600 mt-0.5 font-mono truncate">{stage.error}</p>}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Debug Panel */}
              <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
                <button
                  onClick={() => setDebugOpen(o => !o)}
                  className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  <span className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    Debug Panel
                  </span>
                  {debugOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </button>
                {debugOpen && (
                  <div className="px-4 pb-4 space-y-1.5 text-xs border-t border-gray-100">
                    {[
                      ['PDF Type',        pdfType],
                      ['OCR Lines',       ocrStage ? String((ocrStage.extra_data?.ocr_tree as Record<string, unknown>)?.lines_preview ? ((ocrStage.extra_data!.ocr_tree as {lines_preview: unknown[]}).lines_preview.length) : '—') : 'N/A (Digital)'],
                      ['Text Length',     parserInput ? `${parserInput.length} chars` : '—'],
                      ['Bank Confidence', bankJson?.confidence_score != null ? `${Math.round(Number(bankJson.confidence_score) * 100)}%` : 'N/A'],
                      ['Parser Status',   stages.find(s => s.name === 'Transaction Extraction (LLM)')?.status ?? '—'],
                      ['Validation',      stages.find(s => s.name === 'Normalization')?.status ?? '—'],
                      ['Errors',          stages.filter(s => s.status === 'ERROR').map(s => s.name).join(', ') || 'None'],
                    ].map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-2 py-1.5 border-b border-gray-50 last:border-0">
                        <span className="text-gray-400">{k}</span>
                        <span className="font-medium text-gray-700 text-right max-w-[180px] truncate">{v}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* ── RIGHT: MAIN TABS ────────────────────────────────────────── */}
            <div className="lg:col-span-2 space-y-4">
              <Tabs defaultValue="transactions">
                <TabsList>
                  <TabsTrigger value="transactions">
                    Transactions&nbsp;<span className="ml-1 rounded-full bg-indigo-100 text-indigo-700 px-1.5 py-0.5 text-[10px] font-bold">{txns.length}</span>
                  </TabsTrigger>
                  <TabsTrigger value="ground-truth" disabled={gtTxns.length === 0}>
                    Ground Truth {diff && <span className="ml-1 text-[10px] font-bold">{diff.accuracy}%</span>}
                  </TabsTrigger>
                  <TabsTrigger value="parser-input">Parser Input</TabsTrigger>
                  <TabsTrigger value="llm-raw">LLM Raw</TabsTrigger>
                  <TabsTrigger value="bank-json">Bank Detection</TabsTrigger>
                </TabsList>

                {/* TRANSACTIONS */}
                <TabsContent value="transactions">
                  <Card>
                    <CardHeader className="pb-0">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3 flex-1">
                          <input
                            type="text"
                            placeholder="Search narration or date…"
                            value={searchQ}
                            onChange={e => setSearchQ(e.target.value)}
                            className="flex-1 max-w-xs rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          />
                          <span className="text-xs text-gray-400">{filteredTxns.length} of {txns.length}</span>
                        </div>
                        <button
                          onClick={exportJson}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
                        >
                          <Download className="w-3.5 h-3.5" />Export JSON
                        </button>
                      </div>
                      {/* Totals */}
                      <div className="flex gap-4 mt-3 pb-3">
                        <div className="text-xs text-gray-500">Total Debits: <span className="font-semibold text-red-600">{totalDebits.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span></div>
                        <div className="text-xs text-gray-500">Total Credits: <span className="font-semibold text-emerald-600">{totalCredits.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span></div>
                      </div>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="max-h-[500px] overflow-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Date</TableHead>
                              <TableHead>Narration</TableHead>
                              <TableHead className="text-right">Debit</TableHead>
                              <TableHead className="text-right">Credit</TableHead>
                              <TableHead className="text-right">Balance</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {filteredTxns.length === 0 ? (
                              <TableRow><TableCell colSpan={5} className="text-center text-gray-400 py-12">No transactions</TableCell></TableRow>
                            ) : filteredTxns.map((t, i) => (
                              <TableRow key={i}>
                                <TableCell className="whitespace-nowrap font-medium text-gray-900">{t.date}</TableCell>
                                <TableCell className="max-w-[260px] truncate" title={t.narration}>{t.narration}</TableCell>
                                <TableCell className="text-right text-red-600 tabular-nums">{t.debit ?? '—'}</TableCell>
                                <TableCell className="text-right text-emerald-600 tabular-nums">{t.credit ?? '—'}</TableCell>
                                <TableCell className="text-right font-medium tabular-nums">{t.balance ?? '—'}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* GROUND TRUTH */}
                <TabsContent value="ground-truth">
                  {diff && (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {[
                          { label: 'Expected',    value: gtTxns.length,       color: 'text-gray-900' },
                          { label: 'Extracted',   value: txns.length,          color: 'text-indigo-700' },
                          { label: 'Missing',     value: diff.missing.length,  color: 'text-red-600' },
                          { label: 'Accuracy',    value: `${diff.accuracy}%`,  color: diff.accuracy >= 95 ? 'text-emerald-600' : 'text-amber-600' },
                        ].map(({ label, value, color }) => (
                          <Card key={label}>
                            <CardContent className="pt-4 pb-4">
                              <p className="text-xs text-gray-400">{label}</p>
                              <p className={cn("text-2xl font-bold mt-1", color)}>{value}</p>
                            </CardContent>
                          </Card>
                        ))}
                      </div>

                      {diff.missing.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-red-600">
                              <XCircle className="w-4 h-4" />
                              Missing Transactions ({diff.missing.length})
                            </CardTitle>
                            <CardDescription>In Ground Truth but NOT found in extracted output</CardDescription>
                          </CardHeader>
                          <CardContent className="p-0">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>Date</TableHead>
                                  <TableHead>Narration</TableHead>
                                  <TableHead className="text-right">Debit</TableHead>
                                  <TableHead className="text-right">Credit</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {diff.missing.map((t, i) => (
                                  <TableRow key={i} className="bg-red-50">
                                    <TableCell className="text-red-800 font-medium">{t.date}</TableCell>
                                    <TableCell className="text-red-700 max-w-[200px] truncate">{t.narration}</TableCell>
                                    <TableCell className="text-right text-red-600">{t.debit ?? '—'}</TableCell>
                                    <TableCell className="text-right text-red-600">{t.credit ?? '—'}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </CardContent>
                        </Card>
                      )}

                      {diff.extra.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-amber-600">
                              <AlertTriangle className="w-4 h-4" />
                              Extra Transactions ({diff.extra.length})
                            </CardTitle>
                            <CardDescription>Extracted but NOT in Ground Truth (possible hallucinations)</CardDescription>
                          </CardHeader>
                          <CardContent className="p-0">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>Date</TableHead>
                                  <TableHead>Narration</TableHead>
                                  <TableHead className="text-right">Debit</TableHead>
                                  <TableHead className="text-right">Credit</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {diff.extra.map((t, i) => (
                                  <TableRow key={i} className="bg-amber-50">
                                    <TableCell className="font-medium">{t.date}</TableCell>
                                    <TableCell className="max-w-[200px] truncate">{t.narration}</TableCell>
                                    <TableCell className="text-right">{t.debit ?? '—'}</TableCell>
                                    <TableCell className="text-right">{t.credit ?? '—'}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </CardContent>
                        </Card>
                      )}

                      {diff.missing.length === 0 && diff.extra.length === 0 && (
                        <div className="flex items-center gap-3 rounded-xl bg-emerald-50 border border-emerald-200 p-6">
                          <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                          <div>
                            <p className="font-semibold text-emerald-800">Perfect Match</p>
                            <p className="text-sm text-emerald-600">All {gtTxns.length} ground truth transactions found. 100% accuracy.</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </TabsContent>

                {/* PARSER INPUT */}
                <TabsContent value="parser-input">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-indigo-500" />
                        Parser Input Text
                      </CardTitle>
                      <CardDescription>Exact text string passed to the LLM ({parserInput.length} chars)</CardDescription>
                    </CardHeader>
                    <CardContent className="p-0">
                      <pre className="text-[11px] leading-relaxed bg-gray-950 text-gray-200 p-4 overflow-auto max-h-[550px] rounded-b-xl whitespace-pre-wrap font-mono">
                        {parserInput || 'No text extracted yet.'}
                      </pre>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* LLM RAW */}
                <TabsContent value="llm-raw">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-indigo-500" />
                        Raw LLM Response
                      </CardTitle>
                      <CardDescription>Unprocessed response string from the transaction extraction model</CardDescription>
                    </CardHeader>
                    <CardContent className="p-0">
                      <pre className="text-[11px] leading-relaxed bg-gray-950 text-emerald-300 p-4 overflow-auto max-h-[550px] rounded-b-xl whitespace-pre-wrap font-mono">
                        {llmRaw || 'No LLM response captured.'}
                      </pre>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* BANK DETECTION */}
                <TabsContent value="bank-json">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <GitCompare className="w-4 h-4 text-indigo-500" />
                        Bank Detection Payload
                      </CardTitle>
                      <CardDescription>
                        Raw JSON returned by <code className="text-xs bg-gray-100 px-1 rounded">classify_document_llm()</code>.
                        Confidence field shown only if LLM returned it.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="p-0">
                      <pre className="text-[11px] leading-relaxed bg-gray-950 text-blue-300 p-4 overflow-auto max-h-[550px] rounded-b-xl whitespace-pre-wrap font-mono">
                        {bankJson ? JSON.stringify(bankJson, null, 2) : 'No bank detection data.'}
                      </pre>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
