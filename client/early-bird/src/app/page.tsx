"use client"
import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"

type GenStatus =
  | "not_started"
  | "researching"
  | "scripting"
  | "generating_audio"
  | "complete"
  | "error"

type GenerationStatusResponse = {
  status: GenStatus
  progress: number
  current_story_index: number
  stories_complete: number
  total_stories: number
  artifacts: {
    titles: Array<{ story_index: number; title: string }>
    research: Record<string, string>
    scripts: Record<string, Array<{ speaker: string; text: string }>>
  }
}

const CATEGORY_OPTIONS = ["Technology", "Science", "Business", "World News", "Politics", "Custom", "Random"] as const

function Spinner() {
  return (
    <div
      className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
      aria-label="Loading"
    />
  )
}

export default function Home() {
  const router = useRouter()
  const [numStoriesInput, setNumStoriesInput] = useState<string>("3")
  const [numStories, setNumStories] = useState<number>(3)
  const [categories, setCategories] = useState<Array<string | null>>(Array(3).fill(null))
  const [submitting, setSubmitting] = useState(false)

  const [podcastId, setPodcastId] = useState<string | null>(null)
  const [status, setStatus] = useState<GenerationStatusResponse | null>(null)
  const [polling, setPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const totalStories = status?.total_stories ?? numStories

  // Determine dropdown value: if category is not in CATEGORY_OPTIONS (excluding Custom/Random), it's Custom
  const categoryValue = useMemo(
    () => categories.map((c) => {
      if (c === null) return "Random"
      // Check if it's one of the predefined options (excluding Custom and Random)
      const predefined = ["Technology", "Science", "Business", "World News", "Politics"]
      if (predefined.includes(c)) return c
      // Otherwise it's a custom value
      return "Custom"
    }),
    [categories]
  )

  // Get the custom text for display in the input
  const getCustomCategoryText = (idx: number): string => {
    const cat = categories[idx]
    if (cat === null) return ""
    const predefined = ["Technology", "Science", "Business", "World News", "Politics", "Random"]
    if (predefined.includes(cat)) return ""
    return cat
  }

  const getNumStoriesError = (): string | null => {
    if (!numStoriesInput.trim()) return "Required"
    const num = Number(numStoriesInput)
    if (isNaN(num)) return "Must be a number"
    if (num < 1) return "Minimum is 1"
    if (num > 5) return "Maximum is 5"
    if (!Number.isInteger(num)) return "Must be whole number"
    return null
  }

  const onNumStoriesChange = (raw: string) => {
    setNumStoriesInput(raw)
  }

  const onNumStoriesBlur = () => {
    const num = Number(numStoriesInput)
    const clamped = Math.floor(Math.max(1, Math.min(10, isNaN(num) ? 1 : num)))
    
    setNumStories(clamped)
    setNumStoriesInput(String(clamped))
    
    // Update categories array to match new count
    setCategories((prev) => {
      const copy = prev.slice(0, clamped)
      while (copy.length < clamped) copy.push(null)
      return copy
    })
  }

  const onCategoryChange = (idx: number, v: string) => {
    setCategories((prev) => {
      const copy = [...prev]
      if (v === "Random") {
        copy[idx] = null
      } else if (v === "Custom") {
        // Keep existing custom text if available, otherwise set to empty string
        const existingCustom = getCustomCategoryText(idx)
        copy[idx] = existingCustom || ""
      } else {
        copy[idx] = v
      }
      return copy
    })
  }

  const onCustomCategoryChange = (idx: number, value: string) => {
    // Update the category directly with the custom value
    setCategories((prev) => {
      const copy = [...prev]
      copy[idx] = value || null
      return copy
    })
  }

  const startGeneration = async () => {
    setError(null)
    setSubmitting(true)
    setStatus(null)
    setPodcastId(null)

    try {
      // Categories are already in the correct format (string or null)
      const res = await fetch(`${API_BASE}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ num_articles: numStories, categories }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.error || "Failed to start generation")
      }
      const body = (await res.json()) as { podcast_id: string }
      setPodcastId(body.podcast_id)
      setPolling(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start generation")
    } finally {
      setSubmitting(false)
    }
  }

  // Poll status while generating
  useEffect(() => {
    if (!podcastId || !polling) return

    let cancelled = false
    const tick = async () => {
      try {
        const res = await fetch(`${API_BASE}/podcasts/${podcastId}/status`)
        if (!res.ok) throw new Error("Failed to fetch status")
        const data = (await res.json()) as GenerationStatusResponse
        if (cancelled) return
        setStatus(data)
        if (data.status === "complete" || data.status === "error") {
          setPolling(false)
        }
      } catch (e) {
        if (cancelled) return
        setError(e instanceof Error ? e.message : "Polling failed")
      }
    }

    tick()
    const interval = setInterval(tick, 2000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [podcastId, polling])

  const statusText: string = useMemo(() => {
    if (!status) return "Starting…"
    switch (status.status) {
      case "researching":
        return "Researching stories…"
      case "scripting":
        return "Writing scripts…"
      case "generating_audio":
        return "Generating audio…"
      case "complete":
        return "Complete!"
      case "error":
        return "Error"
      default:
        return "Preparing…"
    }
  }, [status])

  const progress = Math.max(0, Math.min(100, status?.progress ?? 0))

  return (
    <div className="space-y-6">
      <div className="text-center space-y-4">
        <img src="/logo.jpg" alt="EarlyBird Logo" width={64} height={64} className="mx-auto dark:invert" />
        <h1 className="text-4xl font-bold">Welcome to EarlyBird</h1>
        <p className="text-xl text-muted-foreground">
          Start your day with personalized podcasts
        </p>
      </div>

      {!podcastId && !polling && (
        <Card>
          <CardHeader>
            <CardTitle>Generate New Podcast</CardTitle>
            <CardDescription>Pick story count + categories (or Random) and generate.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="numStories">Number of stories</Label>
              <Input
                id="numStories"
                type="number"
                min={1}
                max={10}
                value={numStoriesInput}
                onChange={(e) => onNumStoriesChange(e.target.value)}
                onBlur={onNumStoriesBlur}
              />
              {getNumStoriesError() && (
                <div className="text-sm text-destructive mt-1">{getNumStoriesError()}</div>
              )}
            </div>

            <div className="space-y-4">
              <Label>Categories</Label>
              {Array.from({ length: numStories }).map((_, idx) => (
                <div key={idx} className="space-y-2">
                  <Label htmlFor={`cat-${idx}`}>Story {idx + 1}</Label>
                  <select
                    id={`cat-${idx}`}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    value={categoryValue[idx] ?? "Random"}
                    onChange={(e) => onCategoryChange(idx, e.target.value)}
                  >
                    {CATEGORY_OPTIONS.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                  {categoryValue[idx] === "Custom" && (
                    <Input
                      id={`custom-cat-${idx}`}
                      type="text"
                      placeholder="Enter custom category or topic"
                      value={getCustomCategoryText(idx)}
                      onChange={(e) => onCustomCategoryChange(idx, e.target.value)}
                      className="mt-2"
                    />
                  )}
                </div>
              ))}
            </div>

            <Button
              onClick={startGeneration}
              className="w-full h-11 px-8 rounded-md"
              disabled={submitting || !!getNumStoriesError()}
            >
              {submitting ? (
                <>
                  <Spinner />
                  Starting…
                </>
              ) : (
                "Generate Podcast"
              )}
            </Button>

            {error && <div className="text-sm text-destructive">{error}</div>}
          </CardContent>
        </Card>
      )}

      {podcastId && status && (
        <Card>
          <CardHeader>
            <CardTitle>Generating</CardTitle>
            <CardDescription>{statusText}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Progress</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                <div className="h-full bg-primary" style={{ width: `${progress}%` }} />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Stories</Label>
              <div className="grid grid-cols-3 gap-2">
                {Array.from({ length: totalStories }).map((_, idx) => {
                  const done = idx < status.stories_complete
                  const active = idx === status.current_story_index
                  return (
                    <div
                      key={idx}
                      className={[
                        "p-2 rounded border text-sm",
                        done
                          ? "bg-green-100 dark:bg-green-900 border-green-500"
                          : active
                          ? "bg-yellow-100 dark:bg-yellow-900 border-yellow-500"
                          : "bg-gray-100 dark:bg-gray-800 border-gray-300",
                      ].join(" ")}
                    >
                      Story {idx + 1}
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Artifacts</Label>
              <Accordion type="multiple" className="w-full">
                {Array.from({ length: totalStories }).map((_, idx) => {
                  const title =
                    status.artifacts.titles.find((t) => t.story_index === idx)?.title ??
                    `Story ${idx + 1}`
                  const research = status.artifacts.research[String(idx)]
                  const script = status.artifacts.scripts[String(idx)]
                  return (
                    <AccordionItem key={idx} value={`story-${idx}`}>
                      <AccordionTrigger>{title}</AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-3">
                          <div>
                            <div className="text-xs font-medium text-muted-foreground mb-1">Research</div>
                            {research ? (
                              <div className="text-sm whitespace-pre-wrap">{research}</div>
                            ) : (
                              <div className="text-sm text-muted-foreground">Not ready yet…</div>
                            )}
                          </div>
                          <div>
                            <div className="text-xs font-medium text-muted-foreground mb-1">Script preview</div>
                            {script?.length ? (
                              <div className="space-y-2">
                                {script.map((u, i) => (
                                  <div key={i} className="text-sm">
                                    <span className="font-medium">{u.speaker}:</span> {u.text}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="text-sm text-muted-foreground">Not ready yet…</div>
                            )}
                          </div>
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  )
                })}
              </Accordion>
            </div>

            {podcastId && (
              <div className="space-y-4">
                <div className="text-sm text-muted-foreground">
                  Generated: <span className="font-mono">{podcastId}</span>
                </div>
                <Button
                  onClick={() => router.push(`/podcast-view/${podcastId}`)}
                  disabled={status?.status !== "complete"}
                  className="w-full h-11 px-8 rounded-md"
                >
                  {status?.status === "complete" ? "View Podcast" : "Generation in progress..."}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}