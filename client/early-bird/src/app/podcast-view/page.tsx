"use client"

export default function PodcastViewIndexPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Podcast View</h1>
      <p className="text-muted-foreground">
        Open a specific podcast at <span className="font-mono">/podcast-view/&lt;podcast_id&gt;</span>.
      </p>
      <a className="underline" href="/previous-podcasts">
        Go to Previous Podcasts
      </a>
    </div>
  )
}