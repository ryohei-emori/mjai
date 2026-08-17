"use client"

// Centered modal primitive, sibling to sheet.tsx (both wrap Radix Dialog).
// Sheets are edge-anchored and narrow, which does not suit long-form content
// such as the correction prompt editor — hence this separate wrapper.

import * as React from "react"
import * as DialogPrimitive from "@radix-ui/react-dialog"
import { X } from "lucide-react"

import { cn } from "@/lib/utils"

const Dialog = DialogPrimitive.Root

const DialogTrigger = DialogPrimitive.Trigger

const DialogClose = DialogPrimitive.Close

const DialogPortal = DialogPrimitive.Portal

const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
  />
))
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName

/**
 * Named dialog widths (see docs/UI-DESIGN.md → Dialog Widths). `prose` is the
 * reading width for confirmations and short explanations; `wide` is for
 * long-form editors, where a reading measure works against the user — the
 * correction prompt is thousands of characters of dense rules, and wrapping it
 * into a column makes it unreviewable.
 */
const DIALOG_SIZES = {
  prose: "max-w-3xl",
  wide: "max-w-5xl",
} as const

export type DialogSize = keyof typeof DIALOG_SIZES

const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & {
    size?: DialogSize
  }
>(({ className, children, size = "prose", ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        // `max-h-[90%]` rather than `90vh`: this element is `fixed`, so a
        // percentage resolves against the initial containing block, which is
        // the viewport the browser is actually showing (and which shrinks for
        // the on-screen keyboard — see layout.tsx `interactiveWidget`). `vh`
        // reports the largest possible viewport, so on a phone the dialog's
        // footer ended up below the fold with nothing to scroll it into view.
        // `overflow-y-auto` is the backstop for the case the two above cannot
        // cover: once a flexible child has shrunk to its own floor there is
        // nothing left to give, and without a scroll the footer's buttons would
        // simply be unreachable.
        "fixed left-1/2 top-1/2 z-50 flex max-h-[90%] w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 overflow-y-auto rounded-lg border border-outline-variant bg-surface p-4 sm:p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
        DIALOG_SIZES[size],
        className
      )}
      {...props}
    >
      {children}
      {/* A 16px glyph is not a finger-sized target, so `touch-target` gives it
          the 44px minimum where the pointer cannot hover. */}
      <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none touch-target">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
))
DialogContent.displayName = DialogPrimitive.Content.displayName

const DialogHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col space-y-1.5", className)} {...props} />
)
DialogHeader.displayName = "DialogHeader"

const DialogFooter = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col-reverse gap-2 sm:flex-row sm:justify-end",
      className
    )}
    {...props}
  />
)
DialogFooter.displayName = "DialogFooter"

const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold text-on-surface", className)}
    {...props}
  />
))
DialogTitle.displayName = DialogPrimitive.Title.displayName

const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-body-sm text-on-surface-variant", className)}
    {...props}
  />
))
DialogDescription.displayName = DialogPrimitive.Description.displayName

export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
}
