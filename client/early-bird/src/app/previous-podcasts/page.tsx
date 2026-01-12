"use client"
import { useEffect, useState } from "react"
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
import PodcastCard from "@/components/PodcastCard"

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
            <PodcastCard
              key={row.podcastId}
              podcastId={row.podcastId}
              datetimeLabel={row.datetimeLabel}
              storyTitles={row.storyTitles}
              onDelete={handleDeleteClick}
            />
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
