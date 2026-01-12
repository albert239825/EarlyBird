"use client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

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
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [podcastToDelete, setPodcastToDelete] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

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

  const handleDeleteClick = (podcastId: string) => {
    setPodcastToDelete(podcastId)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!podcastToDelete) return

    setDeleting(true)
    try {
      const response = await fetch(`${API_BASE}/podcasts/${podcastToDelete}`, {
        method: "DELETE",
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData?.error || "Failed to delete podcast")
      }

      // Remove from local state
      setRows((prev) => prev.filter((row) => row.podcastId !== podcastToDelete))
      setDeleteDialogOpen(false)
      setPodcastToDelete(null)
    } catch (error) {
      console.error("Error deleting podcast:", error)
      alert(error instanceof Error ? error.message : "Failed to delete podcast")
    } finally {
      setDeleting(false)
    }
  }

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false)
    setPodcastToDelete(null)
  }

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
              <CardHeader className="relative">
                <CardTitle>{row.datetimeLabel}</CardTitle>
                <div className="text-xs text-muted-foreground font-mono">{row.podcastId}</div>
                <button
                  onClick={() => handleDeleteClick(row.podcastId)}
                  className="absolute top-4 right-4 p-1.5 rounded-md hover:bg-destructive/10 text-destructive hover:text-destructive/80 transition-colors"
                  aria-label="Delete podcast"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M3 6h18" />
                    <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                    <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                  </svg>
                </button>
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

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Podcast</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this podcast? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleDeleteCancel} disabled={deleting}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? "Deleting..." : "Yes, Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default PreviousPodcasts
