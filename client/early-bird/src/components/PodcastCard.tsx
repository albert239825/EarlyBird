import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

type PodcastCardProps = {
  podcastId: string
  datetimeLabel: string
  storyTitles: string[]
  onDelete: (podcastId: string) => void
}

const PodcastCard = ({ podcastId, datetimeLabel, storyTitles, onDelete }: PodcastCardProps) => {
  return (
    <Card>
      <CardHeader className="relative">
        <CardTitle>{datetimeLabel}</CardTitle>
        <div className="text-xs text-muted-foreground font-mono">{podcastId}</div>
        <button
          onClick={() => onDelete(podcastId)}
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
        {storyTitles.length > 0 && (
          <ul className="list-disc pl-5 space-y-1 text-sm">
            {storyTitles.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        )}
        <a href={`/podcast-view/${podcastId}`} className="block">
          <Button className="w-full">Open</Button>
        </a>
      </CardContent>
    </Card>
  )
}

export default PodcastCard
