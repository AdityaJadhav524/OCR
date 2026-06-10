import * as React from "react"
import { cn } from "@/lib/utils"

const TabsContext = React.createContext<{
  value: string
  onValueChange: (value: string) => void
} | null>(null)

export function Tabs({ defaultValue, value, onValueChange, className, children }: {
  defaultValue?: string
  value?: string
  onValueChange?: (value: string) => void
  className?: string
  children: React.ReactNode
}) {
  const [active, setActive] = React.useState(value || defaultValue || "")
  React.useEffect(() => { if (value !== undefined) setActive(value) }, [value])
  const handleChange = (val: string) => { setActive(val); onValueChange?.(val) }
  return (
    <TabsContext.Provider value={{ value: active, onValueChange: handleChange }}>
      <div className={cn("w-full", className)}>{children}</div>
    </TabsContext.Provider>
  )
}

export function TabsList({ className, children }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("flex items-center gap-1 rounded-lg bg-gray-100 p-1", className)}>
      {children}
    </div>
  )
}

export function TabsTrigger({ value, className, children, disabled }: {
  value: string; disabled?: boolean
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const ctx = React.useContext(TabsContext)!
  const active = ctx.value === value
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => ctx.onValueChange(value)}
      className={cn(
        "px-3 py-1.5 rounded-md text-sm font-medium transition-all",
        "disabled:opacity-50 disabled:pointer-events-none",
        active
          ? "bg-white text-gray-900 shadow-sm"
          : "text-gray-500 hover:text-gray-900 hover:bg-white/50",
        className
      )}
    >{children}</button>
  )
}

export function TabsContent({ value, className, children }: {
  value: string
} & React.HTMLAttributes<HTMLDivElement>) {
  const ctx = React.useContext(TabsContext)!
  if (ctx.value !== value) return null
  return <div className={cn("mt-2", className)}>{children}</div>
}
