"use client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useEffect, useState } from "react"

const PreviousPodcasts = () => {
  const [previousPodcasts, setPreviousPodcasts] = useState<{ title: string, date: string, topic: string }[]>([])

  useEffect(() => {
    const fetchPodcasts = async () => {
      try {
        const response = await fetch("http://localhost:8000/get/transcripts")
        const data = await response.json();
        console.log(data);
        let podcasts = []
        for (const podcast of data["metadata"]["metadata"]) {
            const date = new Date(podcast.datetime);
            const formattedDate = `${date.getMonth() + 1}/${date.getDate()}/${date.getFullYear()}`;
            const formattedTopic = `${podcast.stories[0].topic} \n ${podcast.stories[1].topic} \n ${podcast.stories[2].topic}`;
            podcasts.push({
            title: formattedDate,
            date: podcast.datetime,
            topic: formattedTopic,
            })
        }
        setPreviousPodcasts(podcasts)
      } catch (error) {
        console.error("Error fetching podcasts:", error)
      }
    }

    fetchPodcasts()
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Previous EarlyBird Episodes</h1>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {previousPodcasts.map((podcast) => (
          <Card key={podcast.title + podcast.topic}>
            <CardHeader>
              <CardTitle>{podcast.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-disc pl-5 space-y-1">
              {podcast.topic.split('\n').map((topic, index) => (
                <li key={index}>{topic}</li>
              ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default PreviousPodcasts

