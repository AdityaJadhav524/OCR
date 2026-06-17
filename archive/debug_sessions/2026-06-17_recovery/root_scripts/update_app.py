import re

with open(r'z:\CA\validation_lab\frontend\src\App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
content = content.replace(
    "import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'",
    "import { Lock, Unlock, Eye, EyeOff } from 'lucide-react'\nimport { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'"
)

# 2. Add hashFile before App component
hash_code = """
// -- Password Session Cache ---------------------------------------------------
async function hashFile(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}
""

content = content.replace("// -- Main App", hash_code + "\n// -- Main App")

# 3. Add state variables inside App
state_code = """
  const [pdfFile,        setPdfFile]       = useState<File | null>(null)
  const [needsPassword,  setNeedsPassword] = useState(false)
  const [passwordInput,  setPasswordInput] = useState('')
  const [unlockError,    setUnlockError]   = useState('')
  const [isUnlocking,    setIsUnlocking]   = useState(false)
  const [showPassword,   setShowPassword]  = useState(false)
  const [capsLock,       setCapsLock]      = useState(false)
""

content = content.replace(
  "const [searchQ,        setSearchQ]       = useState('')",
  "const [searchQ,        setSearchQ]       = useState('')\n" + state_code
)

# 4. Modify processPdf
process_code = """
  const processPdf = async (file: File, password?: string) => {
    if (!password) {
      setPdfFileName(file.name)
      setPdfFile(file)
      setResult(null)
    }
    if (password) setIsUnlocking(true)
    else setLoading(true)
    
    setUnlockError('')
    
    try {
      const fd = new FormData()
      fd.append('file', file)
      
      let passToUse = password
      if (!passToUse) {
        const hash = await hashFile(file)
        const cached = sessionStorage.getItem('pdf_pass_' + hash)
        if (cached) passToUse = cached
      }
      
      if (passToUse) fd.append('password', passToUse)

      const res  = await fetch('/api/process', { method: 'POST', body: fd })
      
      if (res.status === 401 || res.status === 400) {
        const data = await res.json()
        if (data.error_code === 'INVALID_PASSWORD') {
          setNeedsPassword(true)
          setUnlockError('Incorrect PDF password')
          if (passToUse) {
            const hash = await hashFile(file)
            sessionStorage.removeItem('pdf_pass_' + hash)
          }
          return
        }
      }
      
      const data = await res.json() as any
      if (data.needs_password) {
        setNeedsPassword(true)
        setResult({ success: false, stages: [{ name: 'PDF Security Check', status: 'PASSWORD_REQUIRED', time_ms: 0, result: 'Encrypted' }], final_transactions: [], pdf_type: 'encrypted' } as any)
        return
      }
      
      if (passToUse) {
        const hash = await hashFile(file)
        sessionStorage.setItem('pdf_pass_' + hash, passToUse)
      }
      
      setNeedsPassword(false)
      setPasswordInput('')
      setResult(data as PipelineResult)
    } catch (e) {
      setResult({ success: false, stages: [], final_transactions: [], error: String(e) } as any)
    } finally {
      setLoading(false)
      setIsUnlocking(false)
    }
  }
""

# Use regex correctly to replace processPdf
content = re.sub(r"const processPdf = async \(file: File\) => \{.*?(?=const loadGt =)", process_code + "\n\n  ", content, flags=re.DOTALL)

# 5. Badges
badge_code = """
          {result && (
            <div className="flex items-center gap-3">
              {pdfType === 'encrypted' && !result.success ? (
                <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold bg-gray-100 text-gray-700">
                  <Lock className="w-3.5 h-3.5" /> ?? Password Protected
                </span>
              ) : pdfType === 'encrypted' && result.success ? (
                <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold bg-blue-100 text-blue-700">
                  <Unlock className="w-3.5 h-3.5" /> ?? Unlocked PDF
                </span>
              ) : (
                <span className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
                  isScanned ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"
                )}>
                  <span className={cn("w-1.5 h-1.5 rounded-full", isScanned ? "bg-amber-500" : "bg-emerald-500")} />
                  {isScanned ? '?? Scanned PDF ? OCR ? Parser' : '?? Digital PDF ? Parser'}
                </span>
              )}
            </div>
          )}
""

content = re.sub(r"\{result && \(\s*<div className=\"flex items-center gap-3\">\s*<span className=\{cn\(.*?\)\}>\s*<span className=\{cn\(.*?\)\} />\s*\{isScanned \? '.*?' : '.*?'\}\s*</span>\s*</div>\s*\)\}", badge_code, content, flags=re.DOTALL)


# 6. Add Modal before <main>
modal_code = """
      {/* -- PASSWORD MODAL --------------------------------------------------- */}
      {needsPassword && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                  <Lock className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Password Protected PDF</h2>
                  <p className="text-sm text-gray-500">This document is encrypted. Enter password to continue.</p>
                </div>
              </div>
              
              <div className="space-y-4">
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={passwordInput}
                    onChange={e => setPasswordInput(e.target.value)}
                    onKeyDown={e => {
                      if (e.getModifierState('CapsLock')) setCapsLock(true); else setCapsLock(false);
                      if (e.key === 'Enter' && passwordInput) processPdf(pdfFile!, passwordInput)
                    }}
                    placeholder="Enter PDF password..."
                    className="w-full pl-4 pr-10 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                
                {capsLock && <p className="text-xs text-amber-600 font-medium flex items-center gap-1"><AlertTriangle className="w-3 h-3"/> Caps Lock is ON</p>}
                {unlockError && <p className="text-xs text-red-600 font-medium flex items-center gap-1"><XCircle className="w-3 h-3"/> {unlockError}</p>}
                
              </div>
            </div>
            
            <div className="bg-gray-50 px-6 py-4 flex items-center justify-end gap-3 border-t border-gray-100">
              <button
                onClick={() => { setNeedsPassword(false); setPdfFile(null); setPdfFileName(''); setResult(null) }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => processPdf(pdfFile!, passwordInput)}
                disabled={!passwordInput || isUnlocking}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {isUnlocking ? <Clock className="w-4 h-4 animate-spin" /> : <Unlock className="w-4 h-4" />}
                Unlock & Process
              </button>
            </div>
          </div>
        </div>
      )}
""

content = content.replace("<main className=", modal_code + "\n      <main className=")

# 7. Add debug fields
debug_fields = """
                      ['Encrypted',       bankStage || ocrStage ? (stages.find(s => s.name === 'PDF Security Check')?.extra_data?.is_encrypted ? 'true' : 'false') : '—'],
                      ['Password Provided', stages.find(s => s.name === 'PDF Security Check')?.status === 'UNLOCKED' || stages.find(s => s.name === 'PDF Security Check')?.status === 'INVALID_PASSWORD' ? 'true' : 'false'],
                      ['Unlock Success',  stages.find(s => s.name === 'PDF Security Check')?.status === 'UNLOCKED' ? 'true' : 'false'],
                      ['Page Count',      result?.ocr_pages ? String(result.ocr_pages) : '—'],
""

content = content.replace("['PDF Type',        pdfType],", "['PDF Type',        pdfType],\n" + debug_fields)

with open(r'z:\CA\validation_lab\frontend\src\App.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done updating App.tsx")
