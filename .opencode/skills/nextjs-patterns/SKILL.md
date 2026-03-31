---
name: nextjs-patterns
description: Next.js App Router architecture standards for frontend development. Covers folder structure, Server vs Client component rules, data fetching patterns, Route Handlers, loading and error boundaries, TypeScript strict mode, environment variables, and theming. Load this before writing any Next.js code.
license: MIT
compatibility: opencode
---

## What I cover

Next.js App Router project structure, Server vs Client component decision rules, data fetching patterns (Server Components + SWR), Route Handlers, loading.tsx and error.tsx boundaries, environment variable handling, TypeScript strict setup, Tailwind theming, and accessibility baseline.

## When to use me

Load this skill at the start of every frontend task before writing any code. Also useful when reviewing Next.js code for architectural compliance or diagnosing hydration and rendering issues.

---

## Project Structure

Every Next.js project must follow this structure exactly:

```
frontend/
├── app/
│   ├── layout.tsx               # Root layout — fonts, providers, ThemeProvider, global CSS
│   ├── page.tsx                 # Home route (Server Component by default)
│   ├── loading.tsx              # Global loading UI — Suspense boundary
│   ├── error.tsx                # Global error boundary — must be 'use client'
│   ├── not-found.tsx            # Global 404 page
│   ├── globals.css              # CSS custom properties, Tailwind base
│   └── [feature]/
│       ├── page.tsx             # Route page — Server Component
│       ├── layout.tsx           # Nested layout (only if needed)
│       ├── loading.tsx          # Route-level loading state
│       ├── error.tsx            # Route-level error boundary
│       └── _components/         # Components private to this route only
│           └── FeatureForm.tsx
├── components/
│   ├── ui/                      # Pure stateless UI primitives
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   └── Modal.tsx
│   └── [feature]/               # Shared feature-level components
├── lib/
│   ├── api.ts                   # All fetch wrappers — base URL from env
│   ├── auth.ts                  # Auth helpers (token storage, headers)
│   └── utils.ts                 # Shared pure utility functions
├── hooks/                       # Custom React hooks ('use client' only)
│   └── useAuth.ts
├── types/
│   └── index.ts                 # All TypeScript interfaces and API types
├── public/                      # Static assets — images, fonts, icons
├── .env.local                   # Never commit — NEXT_PUBLIC_* and server vars
├── .env.example                 # All required env vars with placeholders
├── next.config.ts               # Next.js config
├── tailwind.config.ts           # Tailwind config with custom tokens
└── tsconfig.json                # Must have strict: true
```

---

## Server vs Client Component — Decision Rules

**Default is always Server Component. Only add `'use client'` when genuinely required.**

```
Server Component (default — no directive)
  ✓ Fetches data directly (async/await)
  ✓ Accesses environment variables (server-only)
  ✓ Renders static or data-driven HTML
  ✓ Imports server-only libraries (database, fs, etc.)
  ✗ Cannot use useState, useEffect, useReducer
  ✗ Cannot attach event listeners

Client Component ('use client' at top of file)
  ✓ Uses React hooks (useState, useEffect, useContext, etc.)
  ✓ Attaches event handlers (onClick, onChange, onSubmit, etc.)
  ✓ Uses browser APIs (window, localStorage, navigator, etc.)
  ✓ Uses third-party libraries that require browser context
  ✗ Cannot be async
  ✗ Cannot directly access server-only resources
```

**The golden rule: push `'use client'` boundary as deep in the tree as possible.**

```tsx
// ✅ Correct — only the interactive part is a Client Component
// app/products/page.tsx (Server Component)
import { ProductList } from './_components/ProductList'
import { AddToCartButton } from './_components/AddToCartButton' // 'use client'

export default async function ProductsPage() {
  const products = await fetchProducts() // server-side fetch, no useEffect
  return (
    <div>
      <ProductList products={products} />
      <AddToCartButton /> {/* only this small leaf is a Client Component */}
    </div>
  )
}

// ❌ Wrong — entire page marked 'use client' just for one button
'use client'
export default function ProductsPage() {
  const [products, setProducts] = useState([])
  useEffect(() => { fetch('/api/products').then(...) }, [])
  // This loses all Server Component benefits
}
```

---

## Data Fetching Patterns

### Server Component — direct async fetch (preferred)

```tsx
// app/dashboard/page.tsx
import { cookies } from 'next/headers'

async function getDashboardData(userId: string) {
  const res = await fetch(`${process.env.API_URL}/dashboard/${userId}`, {
    headers: { Authorization: `Bearer ${getServerToken()}` },
    next: { revalidate: 60 }, // ISR: revalidate every 60 seconds
    // or: cache: 'no-store'  // always fresh (SSR)
    // or: cache: 'force-cache' // indefinite cache (SSG)
  })
  if (!res.ok) throw new Error(`Failed to fetch dashboard: ${res.status}`)
  return res.json()
}

export default async function DashboardPage() {
  const data = await getDashboardData('123') // no useEffect, no useState
  return <DashboardView data={data} />
}
```

### Client Component — SWR for client-side fetching

```tsx
// components/LiveNotifications.tsx
'use client'
import useSWR from 'swr'
import { apiFetch } from '@/lib/api'

const fetcher = (url: string) => apiFetch(url).then(r => r.json())

export function LiveNotifications({ userId }: { userId: string }) {
  const { data, error, isLoading } = useSWR(
    `/api/notifications/${userId}`,
    fetcher,
    { refreshInterval: 5000 }
  )

  if (isLoading) return <NotificationSkeleton />
  if (error) return <ErrorMessage message="Could not load notifications" />
  return <NotificationList items={data.data} />
}
```

---

## API Client (lib/api.ts)

**Never write raw `fetch` calls scattered across components. Always centralize.**

```typescript
// lib/api.ts
const BASE_URL = process.env.NEXT_PUBLIC_API_URL

if (!BASE_URL) {
  throw new Error('NEXT_PUBLIC_API_URL is not defined. Check your .env.local file.')
}

type RequestOptions = RequestInit & { token?: string }

export async function apiFetch(path: string, options: RequestOptions = {}) {
  const { token, ...fetchOptions } = options

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...fetchOptions.headers,
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...fetchOptions, headers })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `HTTP ${res.status}`)
  }

  return res
}

// Convenience methods
export const api = {
  get: (path: string, token?: string) =>
    apiFetch(path, { method: 'GET', token }),
  post: (path: string, body: unknown, token?: string) =>
    apiFetch(path, { method: 'POST', body: JSON.stringify(body), token }),
  put: (path: string, body: unknown, token?: string) =>
    apiFetch(path, { method: 'PUT', body: JSON.stringify(body), token }),
  delete: (path: string, token?: string) =>
    apiFetch(path, { method: 'DELETE', token }),
}
```

---

## Route Handlers

```typescript
// app/api/[resource]/route.ts
import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  req: NextRequest,
  { params }: { params: { resource: string } }
) {
  try {
    const data = await fetchFromBackend(params.resource)
    return NextResponse.json({ data }, { status: 200 })
  } catch (err) {
    console.error('[GET /api/resource]', err)
    return NextResponse.json({ error: 'Failed to fetch resource' }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const result = await createResource(body)
    return NextResponse.json({ data: result }, { status: 201 })
  } catch (err) {
    console.error('[POST /api/resource]', err)
    return NextResponse.json({ error: 'Failed to create resource' }, { status: 500 })
  }
}
```

---

## Loading and Error Boundaries

**Every route must have loading.tsx and error.tsx. No exceptions.**

```tsx
// app/[feature]/loading.tsx — automatically shown during navigation
export default function Loading() {
  return (
    <div className="flex items-center justify-center min-h-[200px]">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )
}
```

```tsx
// app/[feature]/error.tsx — must be 'use client', receives error + reset
'use client'

import { useEffect } from 'react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('[Route Error]', error)
  }, [error])

  return (
    <div className="flex flex-col items-center justify-center min-h-[200px] gap-4">
      <p className="text-destructive">Something went wrong: {error.message}</p>
      <button
        onClick={reset}
        className="px-4 py-2 bg-primary text-primary-foreground rounded-md"
      >
        Try again
      </button>
    </div>
  )
}
```

---

## Layout and Providers

```tsx
// app/layout.tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: { template: '%s | App Name', default: 'App Name' },
  description: 'App description',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        {/* Add providers here: ThemeProvider, AuthProvider, etc. */}
        {children}
      </body>
    </html>
  )
}
```

---

## Theming

**Default is Dark Theme. Implement via CSS custom properties — never hardcode colors.**

```css
/* app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --muted: 210 40% 96%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --border: 214.3 31.8% 91.4%;
    --destructive: 0 84.2% 60.2%;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --primary: 217.2 91.2% 59.8%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --border: 217.2 32.6% 17.5%;
    --destructive: 0 62.8% 30.6%;
  }

  /* Default to dark theme */
  html { @apply dark; }
}
```

---

## TypeScript Setup

```json
// tsconfig.json — required settings
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

**Type all API responses. Never use `any`.**

```typescript
// types/index.ts
export interface User {
  id: number
  email: string
  name: string
  created_at: string
}

export interface ApiResponse<T> {
  data: T
  message: string
  total?: number
}

export interface ApiError {
  error: string
  details?: Record<string, string> | string
}
```

---

## Environment Variables

```bash
# .env.local (never commit)
NEXT_PUBLIC_API_URL=http://localhost:5000    # Exposed to browser — backend base URL
API_SECRET=server-only-secret               # Never use NEXT_PUBLIC_ for secrets

# .env.example (always commit — placeholder values)
NEXT_PUBLIC_API_URL=http://localhost:5000
API_SECRET=your-secret-here
```

**Always validate env vars at startup:**

```typescript
// lib/env.ts
export function requireEnv(key: string): string {
  const value = process.env[key]
  if (!value) throw new Error(`Missing required environment variable: ${key}`)
  return value
}
```

---

## Accessibility Baseline

- All interactive elements must have accessible labels (`aria-label`, `aria-labelledby`, or visible text)
- Color contrast must meet WCAG AA (4.5:1 for normal text, 3:1 for large text)
- All images must have `alt` text — empty string `alt=""` for decorative images
- Forms must use `<label>` elements linked via `htmlFor`
- Focus states must be visible — never remove `outline` without providing an alternative

---

## Self-Verify Checklist (run mentally before every handoff)

- [ ] No `'use client'` on pages or layouts unless absolutely required
- [ ] All data fetching in Server Components uses `async/await`, not `useEffect`
- [ ] `NEXT_PUBLIC_API_URL` used for all backend calls — never hardcoded
- [ ] Every route has `loading.tsx` and `error.tsx`
- [ ] `npm run build` passes with zero errors or warnings
- [ ] No `any` types in the codebase
- [ ] `.env.example` includes all env vars used
- [ ] All images have `alt` attributes