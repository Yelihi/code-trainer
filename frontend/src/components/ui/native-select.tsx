import * as React from "react"
import { cn } from "cn"
import { ChevronDownIcon } from "lucide-react"

function NativeSelect({
  className,
  size = "default",
  multiple,
  ...props
}: Omit<React.ComponentProps<"select">, "size"> & { size?: number | "sm" | "default" }) {
  const listbox = multiple || typeof size === "number" && size > 1
  return (
    <div
      className="group/native-select relative w-full min-w-0 has-[select:disabled]:opacity-50"
      data-slot="native-select-wrapper"
    >
      <select
        data-slot="native-select"
        data-size={typeof size === "string" ? size : "default"}
        size={typeof size === "number" ? size : undefined}
        multiple={multiple}
        className={cn(
          "min-h-11 w-full min-w-0 rounded-md border border-input bg-[#0c0a18] px-5 py-2.5 text-[var(--text-body)] text-foreground [color-scheme:dark] transition-[color,box-shadow] outline-none selection:bg-primary selection:text-primary-foreground disabled:cursor-not-allowed data-[size=sm]:min-h-8 data-[size=sm]:py-1",
          !listbox && "appearance-none pr-11",
          "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50",
          "aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40",
          className
        )}
        {...props}
      />
      {!listbox && <ChevronDownIcon
        className="pointer-events-none absolute top-1/2 right-3.5 size-4 -translate-y-1/2 text-muted-foreground opacity-50 select-none"
        aria-hidden="true"
        data-slot="native-select-icon"
      />}
    </div>
  )
}

function NativeSelectOption({
  className,
  ...props
}: React.ComponentProps<"option">) {
  return (
    <option
      data-slot="native-select-option"
      className={cn("bg-[Canvas] text-[CanvasText]", className)}
      {...props}
    />
  )
}

function NativeSelectOptGroup({
  className,
  ...props
}: React.ComponentProps<"optgroup">) {
  return (
    <optgroup
      data-slot="native-select-optgroup"
      className={cn("bg-[Canvas] text-[CanvasText]", className)}
      {...props}
    />
  )
}

export { NativeSelect, NativeSelectOptGroup, NativeSelectOption }
