"use client"

import { useEffect, useMemo, useState } from "react"
import { useParams } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import AudioPlayer from "@/components/AudioPlayer"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"

type Manifest = {
  podcast_id: string
  segments: Array<{
    segment_id: string
    story_index: number
    speaker: string
    text: string
  }>
}

export default function PodcastViewPage() {
  const params = useParams()
  const podcastId = params?.id as string
  const [manifest, setManifest] = useState<Manifest | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!podcastId) return
    let cancelled = false
    const run = async () => {
      try {
        const res = await fetch(`${API_BASE}/podcasts/${podcastId}/manifest`)
        if (!res.ok) throw new Error("Manifest not found yet")
        const data = (await res.json()) as Manifest
        if (cancelled) return
        setManifest(data)
      } catch (e) {
        if (cancelled) return
        setError(e instanceof Error ? e.message : "Failed to load manifest")
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [podcastId])

  const grouped = useMemo(() => {
    const by: Record<string, Manifest["segments"]> = {}
    for (const seg of manifest?.segments ?? []) {
      const key = String(seg.story_index)
      if (!by[key]) by[key] = []
      by[key].push(seg)
    }
    return by
  }, [manifest])

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Podcast: {podcastId}</CardTitle>
        </CardHeader>
        <CardContent>
          <AudioPlayer podcastId={podcastId} />
          {error && <div className="mt-4 text-sm text-muted-foreground">{error}</div>}
        </CardContent>
      </Card>

      {manifest && (
        <Card>
          <CardHeader>
            <CardTitle>Transcript</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.entries(grouped).map(([storyIndex, segs]) => (
              <div key={storyIndex} className="space-y-2">
                {Number(storyIndex) >= 0 && <div className="font-semibold">Story {Number(storyIndex) + 1}</div>}
                <div className="space-y-1">
                  {segs.map((seg) => (
                    <div key={seg.segment_id} className="p-2 rounded border bg-card">
                      <span className="text-xs font-medium text-muted-foreground mr-2">
                        {seg.speaker === "host" ? "Host" : "Expert"}:
                      </span>
                      <span className="text-sm">{seg.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

