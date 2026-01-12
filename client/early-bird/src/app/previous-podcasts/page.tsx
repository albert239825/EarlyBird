"use client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"

type PodcastMetaEntry = {
  datetime: string
  podcast_dir?: string
  podcast_id?: string
}

type PodcastRow = {
  podcastId: string
  datetimeRaw: string
  datetimeLabel: string
  storyTitles: string[]
}

const PreviousPodcasts = () => {
  const [rows, setRows] = useState<PodcastRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPodcasts = async () => {
      try {
        const response = await fetch(`${API_BASE}/get/transcripts`)
        if (!response.ok) throw new Error("Failed to fetch transcripts metadata")
        const data = await response.json()

        const entries: PodcastMetaEntry[] = data?.metadata?.metadata ?? []
        const normalized: PodcastRow[] = []

        for (const entry of entries) {
          const raw = entry.datetime
          const dt = new Date(raw)
          const label = Number.isNaN(dt.getTime())
            ? raw
            : `${dt.getMonth() + 1}/${dt.getDate()}/${dt.getFullYear()}`

          // prefer explicit podcast_id; fallback to last path segment of podcast_dir
          const podcastId =
            entry.podcast_id ??
            (entry.podcast_dir ? entry.podcast_dir.split("/").filter(Boolean).pop() : undefined)

          if (!podcastId) continue

          normalized.push({
            podcastId,
            datetimeRaw: raw,
            datetimeLabel: label,
            storyTitles: [],
          })
        }

        // newest first using raw datetime
        normalized.sort((a, b) => new Date(b.datetimeRaw).getTime() - new Date(a.datetimeRaw).getTime())

        // Fetch story titles for each podcast (best-effort)
        const withTitles = await Promise.all(
          normalized.map(async (row) => {
            try {
              const res = await fetch(`${API_BASE}/podcasts/${row.podcastId}/podcast.json`)
              if (!res.ok) return row
              const pj = await res.json()
              const titles: string[] = (pj?.stories ?? [])
                .map((s: any) => s?.title)
                .filter((t: any) => typeof t === "string" && t.trim())
              return { ...row, storyTitles: titles }
            } catch {
              return row
            }
          })
        )

        setRows(withTitles)
      } catch (error) {
        console.error("Error fetching podcasts:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchPodcasts()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-muted-foreground">Loading podcasts…</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Previous EarlyBird Episodes</h1>
      {rows.length === 0 ? (
        <div className="text-muted-foreground">No podcasts found.</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {rows.map((row) => (
            <Card key={row.podcastId}>
              <CardHeader>
                <CardTitle>{row.datetimeLabel}</CardTitle>
                <div className="text-xs text-muted-foreground font-mono">{row.podcastId}</div>
              </CardHeader>
              <CardContent className="space-y-4">
                {row.storyTitles.length > 0 && (
                  <ul className="list-disc pl-5 space-y-1 text-sm">
                    {row.storyTitles.map((t, i) => (
                      <li key={i}>{t}</li>
                    ))}
                  </ul>
                )}
                <a href={`/podcast-view/${row.podcastId}`} className="block">
                  <Button className="w-full">Open</Button>
                </a>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

export default PreviousPodcasts
