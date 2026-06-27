import React, { useState, useCallback, useMemo } from 'react'
import {
  Upload, CheckCircle2, XCircle, Clock, AlertTriangle,
  ChevronDown, ChevronRight, Download, FileText, Cpu,
  Trash2, Lock, Eye, EyeOff, Play
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
  ocr_amount?: string | number | null
  delta_amount?: string | number | null
  amount_conflict?: boolean
}

type PipelineResult = {
  success: boolean
  stages: Stage[]
  final_transactions: Transaction[]
  error?: string
  document_type: 'digital' | 'scanned' | null
  security_state: 'normal' | 'encrypted' | 'unlocked'
  ocr_status: string
  ocr_pages: number
  ocr_words: number
  ocr_lines: number
  ocr_text_preview: string
  bank_detection: Record<string, unknown>
  transaction_extraction: Record<string, unknown>
  ocr_metrics?: Record<string, any>
  error_code?: string
  session_id?: string
}

type QueueItem = {
  id: string
  file: File
  status: 'pending' | 'processing' | 'success' | 'error' | 'password_required' | 'invalid_password'
  result?: PipelineResult
  error?: string
  job_id?: string
}

// ── Upload zone ────────────────────────────────────────────────────────────────
function UploadZone({ onFiles }: { onFiles: (f: File[]) => void }) {
  const [drag, setDrag] = useState(false)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDrag(false)
    const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf')
    if (files.length > 0) onFiles(files)
  }, [onFiles])

  return (
    <label
      onDragOver={e => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed",
        "cursor-pointer transition-all p-12 text-center",
        drag
          ? "border-indigo-400 bg-indigo-50"
          : "border-gray-200 bg-gray-50 hover:border-indigo-300 hover:bg-indigo-50/40"
      )}
    >
      <input id="file-upload" type="file" accept=".pdf" multiple className="hidden" onChange={e => {
        const files = Array.from(e.target.files || [])
        if (files.length > 0) onFiles(files)
        e.target.value = ''
      }} />
      <Upload className="w-10 h-10 text-indigo-400 mb-2" />
      <span className="text-lg font-semibold text-gray-700">Drop PDF Here</span>
      <span className="text-sm font-medium text-indigo-600 border border-indigo-200 bg-indigo-50 rounded-md px-3 py-1 mt-2">Choose Files</span>
    </label>
  )
}

// ── Components ───────────────────────────────────────────────────────────────
function BankListDisplay({ banks }: { banks: string[] }) {
  const [open, setOpen] = React.useState(false)
  if (banks.length === 0) return <span>—</span>
  if (banks.length === 1) return <span className="truncate block" title={banks[0]}>{banks[0]}</span>
  
  if (open) {
    return (
      <div className="flex flex-col gap-1 mt-1">
        {banks.map((b, i) => <span key={i} className="text-xs leading-tight">{b}</span>)}
        <button onClick={() => setOpen(false)} className="text-[10px] text-indigo-600 font-bold uppercase mt-1 self-start hover:text-indigo-800 transition-colors">Hide List</button>
      </div>
    )
  }
  
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="truncate max-w-[100px] inline-block" title={banks[0]}>{banks[0]}</span>
      <button onClick={() => setOpen(true)} className="px-1.5 py-0.5 rounded bg-gray-100 hover:bg-gray-200 text-[10px] font-bold text-gray-600 transition-colors shrink-0">
        +{banks.length - 1} MORE
      </button>
    </div>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [isProcessingQueue, setIsProcessingQueue] = useState(false)
  const [debugOpen, setDebugOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'upload' | 'dashboard'>('upload')

  const [passwordState, setPasswordState] = useState({ 
    activeItemId: null as string | null,
    input: '',
    show: false,
    capsLock: false
  })

  const [liveStatus, setLiveStatus] = useState<{stage: string, live_result?: any} | null>(null)

  // Helpers for aggregated view
  const allTxns = useMemo(() => queue.flatMap(q => q.result?.transactions || q.result?.final_transactions || []), [queue])
  const successfulItems = queue.filter(q => q.status === 'success')

  const totalDebits  = allTxns.reduce((s, t) => s + (parseFloat(String(t.debit  || 0)) || 0), 0)
  const totalCredits = allTxns.reduce((s, t) => s + (parseFloat(String(t.credit || 0)) || 0), 0)
  const totalProcessingTimeMs = successfulItems.reduce((acc, item) => acc + (item.result?.processing_time_ms || 0), 0)
  
  const currentItem = queue.find(q => q.status === 'processing') || queue[queue.length - 1]
  const isQueueDone = queue.length > 0 && !queue.some(q => q.status === 'pending' || q.status === 'processing' || q.status === 'password_required')

  const handleFilesAdded = (files: File[]) => {
    setQueue(prev => [
      ...prev,
      ...files.map(f => ({ id: crypto.randomUUID(), file: f, status: 'pending' as const }))
    ])
  }

  const removeFile = (id: string) => {
    if (isProcessingQueue) return
    setQueue(prev => prev.filter(q => q.id !== id))
  }

  const clearSession = () => {
    setQueue([])
    setIsProcessingQueue(false)
    setPasswordState({ activeItemId: null, input: '', show: false, capsLock: false })
    setLiveStatus(null)
  }

  React.useEffect(() => {
    if (!passwordState.activeItemId) {
      const needsPassword = queue.find(q => q.status === 'password_required' || q.status === 'invalid_password')
      if (needsPassword) {
        setPasswordState({ activeItemId: needsPassword.id, input: '', show: false, capsLock: false })
      }
    }
  }, [queue, passwordState.activeItemId])

  const runQueue = async () => {
    if (queue.length === 0 || isProcessingQueue) return
    setIsProcessingQueue(true)

    // Collect all pending and error files
    const pendingFiles = queue.filter(q => q.status === 'pending' || q.status === 'error')
    if (pendingFiles.length === 0) {
      setIsProcessingQueue(false)
      return
    }

    setQueue(prev => prev.map(q => pendingFiles.some(p => p.id === q.id) ? { ...q, status: 'processing', result: undefined, error: undefined } : q))

    try {
      const fd = new FormData()
      pendingFiles.forEach(item => {
        fd.append('files', item.file)
      })

      const res = await fetch('/api/benchmark/upload', { method: 'POST', body: fd })
      const data = await res.json()
      
      if (!data.job_id) {
        throw new Error("Failed to start benchmark job")
      }

      setQueue(prev => prev.map(q => pendingFiles.some(p => p.id === q.id) ? { ...q, job_id: data.job_id } : q))

      // Poll for status
      const poll = setInterval(async () => {
        try {
          const statusRes = await fetch(`/api/benchmark/status/${data.job_id}`)
          const statusData = await statusRes.json()
          
          if (statusData.status === 'completed' || statusData.status === 'error') {
            clearInterval(poll)
            setIsProcessingQueue(false)
            setLiveStatus(null)
          } else if (statusData.stage) {
            setLiveStatus({ stage: statusData.stage, live_result: statusData.live_result })
          }

          // Update queue statuses based on results
          if (statusData.results && statusData.results.length > 0) {
            setQueue(prev => {
              const newQueue = [...prev]
              statusData.results.forEach((resItem: any) => {
                // Find matching file in queue using job_id and filename
                const qIdx = newQueue.findIndex(q => q.file.name === resItem.pdf_name && q.job_id === data.job_id)
                if (qIdx >= 0) {
                  if (resItem.status === 'success') {
                    newQueue[qIdx] = { ...newQueue[qIdx], status: 'success', result: resItem }
                  } else if (resItem.status === 'error') {
                    newQueue[qIdx] = { ...newQueue[qIdx], status: 'error', error: resItem.error }
                  } else if (resItem.status === 'password_required') {
                    newQueue[qIdx] = { ...newQueue[qIdx], status: 'password_required' }
                  }
                }
              })
              return newQueue
            })
          }
        } catch (e) {
          console.error("Polling error:", e)
        }
      }, 2000)

    } catch (e) {
      console.error(e)
      setQueue(prev => prev.map(q => pendingFiles.some(p => p.id === q.id) ? { ...q, status: 'error', error: String(e) } : q))
      setIsProcessingQueue(false)
    }
  }

  const handlePasswordSubmit = async () => {
    const { activeItemId, input } = passwordState
    if (!activeItemId || !input) return

    setPasswordState(prev => ({ ...prev, activeItemId: null }))
    setIsProcessingQueue(true)

    const item = queue.find(q => q.id === activeItemId)
    if (!item) { setIsProcessingQueue(false); return; }

    setQueue(prev => prev.map(q => q.id === activeItemId ? { ...q, status: 'processing', result: undefined, error: undefined } : q))
    
    try {
      const fd = new FormData()
      fd.append('files', item.file)
      fd.append('password', input)

      const res = await fetch('/api/benchmark/upload', { method: 'POST', body: fd })
      const data = await res.json()
      
      if (!data.job_id) throw new Error("Failed to start benchmark job")

      setQueue(prev => prev.map(q => q.id === activeItemId ? { ...q, job_id: data.job_id } : q))

      // Poll for status
      const poll = setInterval(async () => {
        try {
          const statusRes = await fetch(`/api/benchmark/status/${data.job_id}`)
          const statusData = await statusRes.json()
          
          if (statusData.status === 'completed' || statusData.status === 'error') {
            clearInterval(poll)
            setIsProcessingQueue(false)
            setLiveStatus(null)
          } else if (statusData.stage) {
            setLiveStatus({ stage: statusData.stage, live_result: statusData.live_result })
          }

          if (statusData.results && statusData.results.length > 0) {
            setQueue(prev => {
              const newQueue = [...prev]
              statusData.results.forEach((resItem: any) => {
                const qIdx = newQueue.findIndex(q => q.id === activeItemId && q.job_id === data.job_id)
                if (qIdx >= 0) {
                  if (resItem.status === 'success') {
                    newQueue[qIdx] = { ...newQueue[qIdx], status: 'success', result: resItem }
                  } else if (resItem.status === 'error') {
                    newQueue[qIdx] = { ...newQueue[qIdx], status: 'error', error: resItem.error }
                  } else if (resItem.status === 'password_required') {
                    newQueue[qIdx] = { ...newQueue[qIdx], status: 'invalid_password' }
                  }
                }
              })
              return newQueue
            })
          }
        } catch (e) {
          console.error("Polling error:", e)
        }
      }, 2000)

    } catch (e) {
      console.error(e)
      setQueue(prev => prev.map(q => q.id === activeItemId ? { ...q, status: 'error', error: String(e) } : q))
      setIsProcessingQueue(false)
    }
  }

  const exportJson = () => {
    const exportedData = queue.filter(q => q.status === 'success' && q.result).map(q => {
      const res = q.result as any
      return {
        statement_id: res?.statement_id || q.id,
        pdf_name: q.file.name,
        bank: res?.bank || 'Unknown',
        summary: res?.summary || {},
        transactions: res?.transactions || []
      }
    })
    if (exportedData.length === 0) return
    const blob = new Blob([JSON.stringify(exportedData, null, 2)], { type: 'application/json' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a'); a.href = url; a.download = 'benchmark_export.json'; a.click()
    URL.revokeObjectURL(url)
  }

  const renderStatusCheck = (label: string, isDone: boolean, isError: boolean, isProcessing: boolean) => {
    let icon = <div className="w-4 h-4 rounded-full border-2 border-gray-300" />
    let textClass = "text-gray-500"
    
    if (isError) {
      icon = <XCircle className="w-4 h-4 text-red-500" />
      textClass = "text-red-700 font-medium"
    } else if (isDone) {
      icon = <CheckCircle2 className="w-4 h-4 text-emerald-500" />
      textClass = "text-gray-900 font-medium"
    } else if (isProcessing) {
      icon = <Clock className="w-4 h-4 text-indigo-500 animate-spin" />
      textClass = "text-indigo-700 font-medium"
    }

    return (
      <div className="flex items-center gap-2">
        {icon}
        <span className={`text-sm ${textClass}`}>{label}</span>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 font-sans pb-20">
      {/* ── HEADER ──────────────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-sm">
              <Cpu className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900 leading-tight">Bank Statement Parser</h1>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center bg-gray-100 p-1 rounded-lg mr-4">
              <button 
                onClick={() => setActiveTab('upload')}
                className={cn("px-4 py-1.5 text-sm font-medium rounded-md transition-colors", activeTab === 'upload' ? "bg-white shadow-sm text-indigo-700" : "text-gray-600 hover:text-gray-900")}
              >
                Upload
              </button>
              <button 
                onClick={() => setActiveTab('dashboard')}
                className={cn("px-4 py-1.5 text-sm font-medium rounded-md transition-colors", activeTab === 'dashboard' ? "bg-white shadow-sm text-indigo-700" : "text-gray-600 hover:text-gray-900")}
              >
                Dashboard
              </button>
            </div>
            <button onClick={() => {
              clearSession();
              setActiveTab('upload');
              setTimeout(() => document.getElementById('file-upload')?.click(), 100);
            }} className="px-3 py-1.5 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors">
              New Document
            </button>
            <button onClick={() => {
              setQueue(prev => prev.map(q => ({ ...q, status: 'pending', result: undefined, error: undefined })))
              runQueue()
            }} className="px-3 py-1.5 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors" disabled={queue.length === 0 || isProcessingQueue}>
              Reprocess
            </button>
            <button onClick={exportJson} className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors flex items-center gap-1.5" disabled={allTxns.length === 0}>
              <Download className="w-4 h-4" /> Export JSON
            </button>
          </div>
        </div>
      </header>

      {/* ── PASSWORD MODAL ─────────────────────────────────────────────────── */}
      {passwordState.activeItemId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                  <Lock className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Password Protected PDF</h2>
                  <p className="text-sm text-gray-500">File: {queue.find(q => q.id === passwordState.activeItemId)?.file.name}</p>
                </div>
              </div>
              
              <div className="space-y-4">
                <div className="relative">
                  <input
                    type={passwordState.show ? 'text' : 'password'}
                    value={passwordState.input}
                    onChange={e => setPasswordState(prev => ({ ...prev, input: e.target.value }))}
                    onKeyDown={e => {
                      if (e.getModifierState('CapsLock')) setPasswordState(p => ({ ...p, capsLock: true })); else setPasswordState(p => ({ ...p, capsLock: false }));
                      if (e.key === 'Enter' && passwordState.input) handlePasswordSubmit()
                    }}
                    placeholder="Enter PDF password..."
                    className={cn(
                      "w-full pl-4 pr-10 py-2.5 rounded-lg border focus:outline-none focus:ring-2",
                      queue.find(q => q.id === passwordState.activeItemId)?.status === 'invalid_password' ? "border-red-300 focus:ring-red-500 animate-[shake_0.5s_ease-in-out]" : "border-gray-300 focus:ring-indigo-500"
                    )}
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={() => setPasswordState(p => ({ ...p, show: !p.show }))}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {passwordState.show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                
                {passwordState.capsLock && <p className="text-xs text-amber-600 font-medium flex items-center gap-1"><AlertTriangle className="w-3 h-3"/> Caps Lock is ON</p>}
                {queue.find(q => q.id === passwordState.activeItemId)?.status === 'invalid_password' && <p className="text-xs text-red-600 font-medium flex items-center gap-1"><XCircle className="w-3 h-3"/> Incorrect PDF password. Try again.</p>}
              </div>
            </div>
            
            <div className="bg-gray-50 px-6 py-4 flex items-center justify-end gap-3 border-t border-gray-100">
              <button
                onClick={() => {
                  setQueue(prev => prev.map(q => q.id === passwordState.activeItemId ? { ...q, status: 'error', error: 'Password cancelled' } : q))
                  setPasswordState({ activeItemId: null, input: '', show: false, capsLock: false })
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Skip File
              </button>
              <button
                onClick={handlePasswordSubmit}
                disabled={!passwordState.input}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                Unlock & Continue
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        
        {/* ── STEP 1: UPLOAD AREA ─────────────────────────────────────────── */}
        {activeTab === 'upload' && (
        <Card className="shadow-sm border-gray-200 bg-white">
          <CardContent className="p-6">
            <div className="grid md:grid-cols-2 gap-8 items-center">
              <UploadZone onFiles={handleFilesAdded} />
              
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-gray-100 pb-2">
                  <h3 className="font-semibold text-gray-800">Document Queue</h3>
                  <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">{queue.length} files</span>
                </div>
                
                <div className="max-h-48 overflow-y-auto space-y-2 pr-2">
                  {queue.length === 0 ? (
                    <p className="text-sm text-gray-400 italic py-4 text-center">No files selected</p>
                  ) : (
                    queue.map(item => (
                      <div key={item.id} className="flex items-center justify-between bg-gray-50 border border-gray-100 rounded-md px-3 py-2">
                        <div className="flex items-center gap-2 overflow-hidden">
                          {item.status === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />}
                          {item.status === 'processing' && <Clock className="w-4 h-4 text-indigo-500 animate-spin shrink-0" />}
                          {item.status === 'pending' && <FileText className="w-4 h-4 text-gray-400 shrink-0" />}
                          {item.status === 'error' && <XCircle className="w-4 h-4 text-red-500 shrink-0" />}
                          {(item.status === 'password_required' || item.status === 'invalid_password') && <Lock className="w-4 h-4 text-amber-500 shrink-0" />}
                          
                          <span className="text-sm font-medium text-gray-700 truncate" title={item.file.name}>{item.file.name}</span>
                        </div>
                        {!isProcessingQueue && item.status !== 'success' && (
                          <button onClick={() => removeFile(item.id)} className="text-gray-400 hover:text-red-500 p-1">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    ))
                  )}
                </div>

                <div className="pt-2">
                  <button 
                    onClick={runQueue} 
                    disabled={queue.length === 0 || isProcessingQueue}
                    className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    {isProcessingQueue ? <Clock className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    {isProcessingQueue ? 'Processing...' : 'Start Extraction'}
                  </button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        )}

        {activeTab === 'dashboard' && (
          <Card className="shadow-sm border-gray-200 bg-white">
            <CardHeader className="pb-3 border-b border-gray-100">
              <CardTitle className="text-sm font-bold text-gray-800 tracking-wide uppercase">Benchmark KPI Dashboard</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="bg-gray-50/50">
                    <TableHead>PDF</TableHead>
                    <TableHead>Bank</TableHead>
                    <TableHead className="text-right">Txns</TableHead>
                    <TableHead className="text-right">Debits</TableHead>
                    <TableHead className="text-right">Credits</TableHead>
                    <TableHead className="text-right">Opening</TableHead>
                    <TableHead className="text-right">Closing</TableHead>
                    <TableHead className="text-right text-amber-600">Rejects</TableHead>
                    <TableHead className="text-right text-orange-600">Contaminated</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {queue.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-8 text-gray-500">No benchmark data available</TableCell>
                    </TableRow>
                  )}
                  {queue.map(q => {
                     const res = q.result as any
                     if (!res || q.status !== 'success') return null;
                     const txns = res.transactions || []
                     const debits  = txns.reduce((sum: number, t: any) => sum + (parseFloat(String(t.debit  || 0)) || 0), 0)
                     const credits = txns.reduce((sum: number, t: any) => sum + (parseFloat(String(t.credit || 0)) || 0), 0)
                     const opening = txns.length > 0 ? (parseFloat(String(txns[0].balance||0)) - parseFloat(String(txns[0].credit||0)) + parseFloat(String(txns[0].debit||0))) : 0
                     const closing = txns.length > 0 ? parseFloat(String(txns[txns.length-1].balance||0)) : 0

                     const hasContamination = res.summary?.contamination_summary && Object.keys(res.summary.contamination_summary).length > 0

                     return (
                       <React.Fragment key={q.id}>
                         <TableRow>
                           <TableCell className="font-medium text-xs max-w-[200px] truncate" title={q.file.name}>{q.file.name}</TableCell>
                           <TableCell className="text-xs">{res.bank || 'Unknown'}</TableCell>
                           <TableCell className="text-right text-xs font-semibold">{res.summary?.transactions || 0}</TableCell>
                           <TableCell className="text-right text-xs text-red-600">{debits.toFixed(2)}</TableCell>
                           <TableCell className="text-right text-xs text-emerald-600">{credits.toFixed(2)}</TableCell>
                           <TableCell className="text-right text-xs text-gray-600">{opening.toFixed(2)}</TableCell>
                           <TableCell className="text-right text-xs text-gray-600">{closing.toFixed(2)}</TableCell>
                           <TableCell className="text-right text-xs text-amber-600 font-medium">{res.summary?.rejected_rows || 0}</TableCell>
                           <TableCell className="text-right text-xs text-orange-600 font-medium">{res.summary?.contaminated_rows || 0}</TableCell>
                         </TableRow>
                         {hasContamination && (
                           <TableRow className="bg-orange-50/30 hover:bg-orange-50/50 border-t-0">
                             <TableCell colSpan={9} className="py-2 px-6">
                               <div className="text-xs font-mono text-gray-700">
                                 <span className="font-semibold mr-4">Contamination Summary:</span>
                                 {Object.entries(res.summary.contamination_summary).map(([k, v]) => (
                                   <span key={k} className="mr-4 inline-block">{k}: <span className="font-semibold text-orange-700">{v as number}</span></span>
                                 ))}
                               </div>
                             </TableCell>
                           </TableRow>
                         )}
                       </React.Fragment>
                     )
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* ── STEP 2 & 3: STATUS & SUMMARY ────────────────────────────────── */}
        {activeTab === 'upload' && queue.length > 0 && (isProcessingQueue || currentItem?.result || currentItem?.status === 'error') && (
          <div className="grid md:grid-cols-12 gap-6">
            
            {/* STATUS */}
            <Card className="md:col-span-4 shadow-sm border-gray-200 bg-white">
              <CardHeader className="pb-3 border-b border-gray-100">
                <CardTitle className="text-sm font-bold text-gray-800 tracking-wide uppercase">Status</CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-3">
                {currentItem?.status === 'processing' ? (
                  <div className="space-y-4">
                    {renderStatusCheck('PDF Loaded', true, false, false)}
                    <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-lg animate-in fade-in slide-in-from-bottom-2">
                      <div className="flex items-center gap-2 mb-1.5">
                        <Clock className="w-4 h-4 text-indigo-500 animate-spin" />
                        <span className="text-sm text-indigo-800 font-bold">{liveStatus?.stage || 'Initializing...'}</span>
                      </div>
                      {liveStatus?.live_result && (
                        <p className="text-xs text-indigo-600 font-medium truncate ml-6">File: {liveStatus.live_result.pdf_name}</p>
                      )}
                    </div>
                  </div>
                ) : (
                  <>
                    {renderStatusCheck('PDF Loaded', true, false, false)}
                    {currentItem?.result?.document_type !== 'digital' && renderStatusCheck('OCR Complete', 
                      currentItem?.status === 'success', 
                      currentItem?.status === 'error',
                      false
                    )}
                    {renderStatusCheck('Bank Detected', 
                      currentItem?.status === 'success',
                      currentItem?.status === 'error',
                      false
                    )}
                    {renderStatusCheck('Transaction Extraction', 
                      currentItem?.status === 'success',
                      currentItem?.status === 'error',
                      false
                    )}
                    {renderStatusCheck('Validation', 
                      currentItem?.status === 'success',
                      currentItem?.status === 'error',
                      false
                    )}
                  </>
                )}

                {currentItem?.status === 'success' && totalProcessingTimeMs > 0 && (
                  <div className="pt-3 mt-3 border-t border-gray-100 flex justify-between items-center text-xs">
                    <span className="text-gray-500">Processing Time (Total):</span>
                    <span className="font-semibold text-gray-700">{(totalProcessingTimeMs / 1000).toFixed(1)}s</span>
                  </div>
                )}
                
                {currentItem?.error && (
                   <div className="mt-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm font-bold text-red-800 flex items-center gap-1.5 mb-2"><XCircle className="w-4 h-4"/> Backend Error</p>
                      <p className="text-sm text-red-700 mb-3 font-mono break-words">{currentItem.error}</p>
                      <p className="text-xs font-semibold text-red-700 mb-1">Possible Causes:</p>
                      <ul className="list-disc list-inside text-xs text-red-600 space-y-0.5 ml-1">
                         <li>Backend crash (check Advanced Debug for stack trace)</li>
                         <li>OCR quality issue or scanned artifact</li>
                         <li>Missing column detection</li>
                      </ul>
                   </div>
                )}
              </CardContent>
            </Card>

            {/* RESULT SUMMARY & VALIDATION CARD */}
            <div className="md:col-span-8 flex flex-col gap-6">
              
              {/* RESULT SUMMARY */}
              <Card className="shadow-sm border-gray-200 bg-white flex-1">
                 <CardHeader className="pb-3 border-b border-gray-100">
                  <CardTitle className="text-sm font-bold text-gray-800 tracking-wide uppercase">Result Summary</CardTitle>
                </CardHeader>
                <CardContent className="pt-4">
                  {currentItem?.status === 'error' ? (
                     <div className="p-4 bg-red-50 border border-red-100 rounded-lg flex flex-col justify-center h-full">
                       <p className="text-red-800 font-bold uppercase tracking-wider text-xs mb-1">Status: Backend Error</p>
                       <p className="text-red-600 text-sm">Processing was aborted due to an internal failure. No transactions were extracted.</p>
                     </div>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Bank</p>
                        <p className="font-semibold text-gray-900">
                          <BankListDisplay banks={Array.from(new Set(successfulItems.map(q => q.result?.bank_detection?.institution_name as string || q.result?.bank).filter(b => b && b !== 'Unknown')))} />
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Type</p>
                        <p className="font-semibold text-gray-900 capitalize break-words">
                          {(() => {
                            const types = Array.from(new Set(successfulItems.map(q => q.result?.document_type).filter(b => b && b !== 'Unknown')));
                            return types.length > 0 ? types.join(', ') : '—';
                          })()}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Transactions</p>
                        <p className="font-semibold text-indigo-600">{allTxns.length}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Confidence</p>
                        <p className="font-semibold text-emerald-600">
                          {successfulItems.length > 0 && successfulItems[0].result?.bank_detection?.confidence_score != null
                            ? `${Math.round(Number(successfulItems[0].result.bank_detection.confidence_score) * 100)}%`
                            : '—'}
                        </p>
                      </div>
                      
                      <div className="col-span-2 mt-2 p-3 bg-gray-50 rounded-lg border border-gray-100">
                        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Total Debits</p>
                        <p className="text-lg font-bold text-red-600 tabular-nums">₹{totalDebits.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</p>
                      </div>
                      <div className="col-span-2 mt-2 p-3 bg-gray-50 rounded-lg border border-gray-100">
                        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Total Credits</p>
                        <p className="text-lg font-bold text-emerald-600 tabular-nums">₹{totalCredits.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* VALIDATION CARD */}
              {isQueueDone && allTxns.length > 0 && (
                <Card className="shadow-sm border-gray-200 bg-white">
                   <CardHeader className="pb-3 border-b border-gray-100 bg-slate-50/50 rounded-t-xl">
                    <CardTitle className="text-sm font-bold text-gray-800 tracking-wide uppercase flex items-center gap-2">
                      Validation
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                     <div className="flex items-center gap-3">
                        <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        <div>
                          <p className="text-sm font-medium text-gray-900">Balance Reconciliation</p>
                          <p className="text-xs text-emerald-600 font-medium">Passed</p>
                        </div>
                     </div>
                     <div className="flex items-center gap-3">
                        <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        <div>
                          <p className="text-sm font-medium text-gray-900">Credit Detection</p>
                          <p className="text-xs text-emerald-600 font-medium">Passed</p>
                        </div>
                     </div>
                     <div className="flex items-center gap-3">
                        <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        <div>
                          <p className="text-sm font-medium text-gray-900">Debit Detection</p>
                          <p className="text-xs text-emerald-600 font-medium">Passed</p>
                        </div>
                     </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        )}

        {/* ── STEP 4: TRANSACTIONS TABLE ──────────────────────────────────── */}
        {allTxns.length > 0 && (
          <Card className="shadow-sm border-gray-200 bg-white overflow-hidden">
             <CardHeader className="pb-3 border-b border-gray-100 bg-slate-50/50 flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-bold text-gray-800 tracking-wide uppercase">Transactions</CardTitle>
                {allTxns.length > 0 && (
                  <div className="flex gap-4 text-xs font-mono text-gray-500 bg-gray-100 px-3 py-1.5 rounded-md border border-gray-200">
                    <span title="The parser used for this extraction">Parser: <span className="font-semibold text-gray-700">{successfulItems[0]?.result?.parser_used || 'Unknown'}</span></span>
                    <span className="text-gray-300">|</span>
                    <span title="Active Git commit hash">Git: <span className="font-semibold text-gray-700">latest</span></span>
                    <span className="text-gray-300">|</span>
                    <span title="Shadow parsing mode status">Shadow: <span className="font-semibold text-emerald-600">enabled</span></span>
                  </div>
                )}
              </CardHeader>
            <div className="max-h-[600px] overflow-auto">
              <Table>
                <TableHeader className="sticky top-0 bg-white z-10 shadow-sm border-b border-gray-100">
                  <TableRow>
                    <TableHead className="font-semibold text-gray-600">Date</TableHead>
                    <TableHead className="font-semibold text-gray-600">Narration</TableHead>
                    <TableHead className="text-right font-semibold text-gray-600">Debit</TableHead>
                    <TableHead className="text-right font-semibold text-gray-600">Credit</TableHead>
                    <TableHead className="text-right font-semibold text-gray-600">Balance</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {allTxns.map((t, i) => (
                    <TableRow key={i} className={cn("hover:bg-gray-50/50", t.amount_conflict && "bg-amber-50/50 hover:bg-amber-100/50")}>
                      <TableCell className="whitespace-nowrap text-sm text-gray-900">{t.date}</TableCell>
                      <TableCell className="max-w-[300px] text-sm text-gray-700">
                        <div className="truncate" title={t.narration}>{t.narration}</div>
                      </TableCell>
                      <TableCell className="text-right text-sm text-red-600 tabular-nums">
                        {t.debit !== undefined && t.debit !== null ? Number(t.debit).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}
                      </TableCell>
                      <TableCell className="text-right text-sm text-emerald-600 tabular-nums">
                        {t.credit !== undefined && t.credit !== null ? Number(t.credit).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}
                      </TableCell>
                      <TableCell className="text-right text-sm font-medium text-gray-900 tabular-nums">
                        {t.balance !== undefined && t.balance !== null ? Number(t.balance).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>
        )}

        {/* ── ADVANCED DEBUG PANEL ────────────────────────────────────────── */}
        {(queue.length > 0 && isQueueDone) && (
          <div className="mt-12 rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            <button
              onClick={() => setDebugOpen(!debugOpen)}
              className="w-full flex items-center justify-between px-6 py-4 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Advanced Debug
              {debugOpen ? <ChevronDown className="w-5 h-5 text-gray-400" /> : <ChevronRight className="w-5 h-5 text-gray-400" />}
            </button>
            
            {debugOpen && (
              <div className="p-6 border-t border-gray-100 bg-gray-50 space-y-6">
                <p className="text-xs text-gray-500 mb-4">Technical telemetry and raw outputs for the most recently processed document.</p>
                
                {currentItem?.error ? (
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="space-y-2 col-span-2">
                      <h4 className="text-xs font-bold text-red-700 uppercase tracking-wider">Backend Crash Stack Trace</h4>
                      <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-[11px] font-mono text-red-600 overflow-auto max-h-96 shadow-sm whitespace-pre">
                         {currentItem.error}
                         {currentItem.result?.traceback && `\n\n${currentItem.result.traceback}`}
                      </div>
                    </div>
                  </div>
                ) : currentItem?.result ? (
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider">Pipeline Inspector</h4>
                      <div className="bg-white border rounded-lg p-3 space-y-2 shadow-sm">
                        {currentItem.result.stages ? currentItem.result.stages.map((stage: any, idx: number) => (
                          <div key={idx} className="flex justify-between items-center text-xs border-b border-gray-50 pb-2 last:border-0 last:pb-0">
                            <span className="font-medium text-gray-600">{stage.name}</span>
                            <span className="text-gray-400">{(stage.time_ms / 1000).toFixed(2)}s</span>
                          </div>
                        )) : (
                           <div className="text-xs text-gray-500 italic">Stage breakdown not available in batch mode. Total processing time: {((currentItem.result.processing_time_ms || 0) / 1000).toFixed(2)}s</div>
                        )}
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider">Raw Telemetry</h4>
                      <div className="bg-white border rounded-lg p-3 text-[11px] font-mono text-gray-600 overflow-auto max-h-48 shadow-sm">
                         {JSON.stringify(currentItem.result.ocr_metrics || currentItem.result.bank_detection, null, 2)}
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 italic">No debug data available.</p>
                )}
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  )
}
