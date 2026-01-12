"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"

type Segment = {
  segment_id: string
  url: string
  duration_ms: number
  text: string
  speaker: "host" | "expert" | string
  story_index: number
}

type Manifest = {
  podcast_id: string
  segments: Segment[]
}

class SegmentPlayer {
  private segments: Segment[]
  private audio: HTMLAudioElement
  private currentIndex = 0
  private accumulatedMs = 0
  private pendingSeekMs: number | null = null
  private debugLabel: string

  onTimeUpdate?: (ms: number) => void
  onSegmentChange?: (idx: number) => void
  onEndedAll?: () => void

  constructor(segments: Segment[], debugLabel: string) {
    this.segments = segments
    this.debugLabel = debugLabel
    this.audio = new Audio()
    // Helps WebAudio analysis for cross-origin media (requires backend CORS headers)
    this.audio.crossOrigin = "anonymous"
    this.audio.preload = "auto"
    this.attach()
  }

  private attach() {
    const log = (...args: any[]) => console.debug(`[AudioPlayer:${this.debugLabel}]`, ...args)

    // Useful audio element event instrumentation
    const events: Array<keyof HTMLMediaElementEventMap> = [
      "loadstart",
      "loadedmetadata",
      "canplay",
      "canplaythrough",
      "playing",
      "pause",
      "waiting",
      "stalled",
      "suspend",
      "seeking",
      "seeked",
      "timeupdate",
      "ended",
      "error",
    ]
    for (const ev of events) {
      this.audio.addEventListener(ev, () => {
        const err = this.audio.error
        log(
          `event:${ev}`,
          {
            src: this.audio.currentSrc || this.audio.src,
            readyState: this.audio.readyState,
            networkState: this.audio.networkState,
            paused: this.audio.paused,
            currentTime: this.audio.currentTime,
            duration: this.audio.duration,
            playbackRate: this.audio.playbackRate,
            volume: this.audio.volume,
          },
          err
            ? { mediaError: { code: err.code, message: (err as any).message } }
            : undefined
        )
      })
    }

    this.audio.addEventListener("timeupdate", () => {
      this.onTimeUpdate?.(this.getCurrentMs())
    })

    this.audio.addEventListener("ended", () => {
      this.accumulatedMs += this.segments[this.currentIndex]?.duration_ms ?? 0
      this.currentIndex += 1
      if (this.currentIndex >= this.segments.length) {
        this.onEndedAll?.()
        return
      }
      this.loadIndex(this.currentIndex)
      // NOTE: we intentionally do NOT auto-play here to keep playback user-gesture initiated.
      // The UI click handler manages calling audio.play() directly.
      this.onSegmentChange?.(this.currentIndex)
    })
  }

  getAudioElement() {
    return this.audio
  }

  getSegments() {
    return this.segments
  }

  getTotalMs() {
    return this.segments.reduce((sum, s) => sum + (s.duration_ms || 0), 0)
  }

  getCurrentMs() {
    return this.accumulatedMs + Math.floor(this.audio.currentTime * 1000)
  }

  private segmentUrlFor(idx: number) {
    const seg = this.segments[idx]
    if (!seg) return ""
    return seg.url.startsWith("/") ? `${API_BASE}${seg.url}` : `${API_BASE}/${seg.url}`
  }

  private loadIndex(idx: number) {
    const seg = this.segments[idx]
    if (!seg) return

    this.audio.src = this.segmentUrlFor(idx)
    this.audio.load()

    const maybeSeek = () => {
      if (this.pendingSeekMs == null) return
      const localMs = Math.max(0, this.pendingSeekMs - this.accumulatedMs)
      this.audio.currentTime = localMs / 1000
      this.pendingSeekMs = null
    }

    this.audio.addEventListener("loadedmetadata", maybeSeek, { once: true })
  }

  async play(): Promise<void> {
    // Important: call play() in direct user gesture code-path to avoid autoplay rejection.
    if (!this.audio.src && !this.audio.currentSrc) {
      this.loadIndex(this.currentIndex)
    }

    try {
      await this.audio.play()
    } catch (e) {
      console.error(`[AudioPlayer:${this.debugLabel}] audio.play() failed`, e, {
        src: this.audio.currentSrc || this.audio.src,
        readyState: this.audio.readyState,
        networkState: this.audio.networkState,
      })
      throw e
    }
  }

  pause() {
    this.audio.pause()
  }

  setVolume(v: number) {
    this.audio.volume = Math.max(0, Math.min(1, v))
  }

  setPlaybackRate(r: number) {
    this.audio.playbackRate = r
  }

  seekTo(ms: number) {
    const clamped = Math.max(0, Math.min(this.getTotalMs(), ms))
    let acc = 0
    for (let i = 0; i < this.segments.length; i++) {
      const d = this.segments[i].duration_ms || 0
      if (clamped <= acc + d) {
        this.currentIndex = i
        this.accumulatedMs = acc
        this.pendingSeekMs = clamped
        this.loadIndex(i)
        this.onSegmentChange?.(i)
        this.onTimeUpdate?.(clamped)
        return
      }
      acc += d
    }
  }
}

function formatMs(ms: number) {
  const totalSec = Math.floor(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}:${String(s).padStart(2, "0")}`
}

export default function AudioPlayer({ podcastId }: { podcastId: string }) {
  const [manifest, setManifest] = useState<Manifest | null>(null)
  const [player, setPlayer] = useState<SegmentPlayer | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentMs, setCurrentMs] = useState(0)
  const [currentSegIdx, setCurrentSegIdx] = useState(0)
  const [volume, setVolume] = useState(1)
  const [muted, setMuted] = useState(false)
  const [rate, setRate] = useState(1)

  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const rafRef = useRef<number | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null)

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      const res = await fetch(`${API_BASE}/podcasts/${podcastId}/manifest`)
      if (!res.ok) throw new Error("Failed to load manifest")
      const data = (await res.json()) as Manifest
      if (cancelled) return
      setManifest(data)

      console.debug("[AudioPlayer] manifest loaded", {
        podcastId,
        segments: (data.segments || []).length,
        firstUrl: data.segments?.[0]?.url,
      })

      const p = new SegmentPlayer(data.segments || [], podcastId)
      p.onTimeUpdate = (ms) => setCurrentMs(ms)
      p.onSegmentChange = (idx) => setCurrentSegIdx(idx)
      p.onEndedAll = () => setIsPlaying(false)
      setPlayer(p)
    }
    run().catch((e) => {
      // eslint-disable-next-line no-console
      console.error(e)
    })
    return () => {
      cancelled = true
    }
  }, [podcastId])

  const totalMs = player?.getTotalMs() ?? 0
  const progressPct = totalMs ? Math.max(0, Math.min(100, (currentMs / totalMs) * 100)) : 0

  const segmentStarts = useMemo(() => {
    if (!manifest) return []
    const starts: number[] = []
    let acc = 0
    for (const s of manifest.segments || []) {
      starts.push(acc)
      acc += s.duration_ms || 0
    }
    return starts
  }, [manifest])

  const ensureAudioGraph = () => {
    if (!player) return
    if (audioCtxRef.current && analyserRef.current && sourceRef.current) return

    const audioEl = player.getAudioElement()
    const ctx = new AudioContext()
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 256
    analyser.smoothingTimeConstant = 0.8

    const src = ctx.createMediaElementSource(audioEl)
    src.connect(analyser)
    analyser.connect(ctx.destination)

    console.debug("[AudioPlayer] WebAudio graph created", {
      audioContextState: ctx.state,
      fftSize: analyser.fftSize,
    })

    audioCtxRef.current = ctx
    analyserRef.current = analyser
    sourceRef.current = src
  }

  useEffect(() => {
    if (!isPlaying) return
    if (!canvasRef.current) return
    if (!analyserRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const analyser = analyserRef.current
    const data = new Uint8Array(analyser.frequencyBinCount)

    const resize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect()
      if (rect) {
        canvas.width = rect.width
        canvas.height = rect.height
      }
    }
    resize()
    window.addEventListener("resize", resize)

    const draw = () => {
      rafRef.current = requestAnimationFrame(draw)
      analyser.getByteFrequencyData(data)
      ctx.fillStyle = "rgb(0,0,0)"
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      const n = data.length
      const barW = (canvas.width / n) * 2.2
      let x = 0
      for (let i = 0; i < n; i++) {
        const v = data[i] / 255
        const h = v * canvas.height
        const hue = (i / n) * 240
        ctx.fillStyle = `hsl(${hue}, 100%, 50%)`
        ctx.fillRect(x, canvas.height - h, barW, h)
        x += barW + 1
      }
    }
    draw()

    return () => {
      window.removeEventListener("resize", resize)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
  }, [isPlaying])

  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      rafRef.current = null
      try {
        sourceRef.current?.disconnect()
        analyserRef.current?.disconnect()
        audioCtxRef.current?.close()
      } catch {
        // ignore
      }
      sourceRef.current = null
      analyserRef.current = null
      audioCtxRef.current = null
    }
  }, [])

  if (!manifest || !player) {
    return <div className="text-sm text-muted-foreground">Loading audio…</div>
  }

  const segments = manifest.segments || []

  const togglePlay = async () => {
    if (!player) return
    if (isPlaying) {
      player.pause()
      setIsPlaying(false)
      return
    }
    ensureAudioGraph()
    if (audioCtxRef.current?.state === "suspended") {
      const before = audioCtxRef.current.state
      await audioCtxRef.current.resume().catch((e) => {
        console.error("[AudioPlayer] audioContext.resume() failed", e)
      })
      console.debug("[AudioPlayer] audioContext.resume()", { before, after: audioCtxRef.current.state })
    }
    try {
      await player.play()
      setIsPlaying(true)
    } catch {
      setIsPlaying(false)
    }
  }

  const onSeek = (pct: number) => {
    if (!player) return
    const ms = Math.floor((pct / 100) * totalMs)
    player.seekTo(ms)
  }

  const onToggleMute = () => {
    if (!player) return
    if (muted) {
      player.setVolume(volume || 0.7)
      setMuted(false)
    } else {
      player.setVolume(0)
      setMuted(true)
    }
  }

  const onVolume = (v: number) => {
    if (!player) return
    setVolume(v)
    setMuted(v === 0)
    player.setVolume(v)
  }

  const onRate = (r: number) => {
    if (!player) return
    setRate(r)
    player.setPlaybackRate(r)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Button onClick={togglePlay} className="h-12 w-12 px-0">
          <span className="text-xs font-semibold">{isPlaying ? "Pause" : "Play"}</span>
        </Button>

        <div className="flex-1 space-y-2">
          <input
            type="range"
            min={0}
            max={100}
            value={progressPct}
            onChange={(e) => onSeek(Number(e.target.value))}
            className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{formatMs(currentMs)}</span>
            <span>{formatMs(totalMs)}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button onClick={onToggleMute} className="h-10 w-10 px-0">
            <span className="text-xs font-semibold">{muted ? "Mute" : "Vol"}</span>
          </Button>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={muted ? 0 : volume}
            onChange={(e) => onVolume(Number(e.target.value))}
            className="w-24 h-2 bg-secondary rounded-lg appearance-none cursor-pointer"
          />
        </div>

        <select
          value={rate}
          onChange={(e) => onRate(Number(e.target.value))}
          className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value={0.5}>0.5x</option>
          <option value={0.75}>0.75x</option>
          <option value={1}>1x</option>
          <option value={1.25}>1.25x</option>
          <option value={1.5}>1.5x</option>
          <option value={2}>2x</option>
        </select>

        <Button
          className="border border-input bg-background hover:bg-accent hover:text-accent-foreground"
          onClick={() => window.open(`${API_BASE}/podcasts/${podcastId}/download`, "_blank")}
        >
          Download
        </Button>
      </div>

      <div className="h-32 bg-black rounded-lg overflow-hidden">
        <canvas ref={canvasRef} className="w-full h-full" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Segments</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {segments.map((seg, idx) => {
              const isCurrent = idx === currentSegIdx
              const startMs = segmentStarts[idx] ?? 0
              return (
                <button
                  key={seg.segment_id}
                  onClick={() => player.seekTo(startMs)}
                  className={[
                    "w-full text-left p-3 rounded-lg border transition-colors",
                    isCurrent ? "bg-primary text-primary-foreground border-primary" : "bg-card hover:bg-accent border-border",
                  ].join(" ")}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium opacity-70">
                          {seg.speaker === "host" ? "Host" : "Expert"}
                        </span>
                        {seg.story_index >= 0 && <span className="text-xs opacity-50">Story {seg.story_index + 1}</span>}
                        <span className="text-xs opacity-50">{formatMs(startMs)}</span>
                      </div>
                      <div className="text-sm line-clamp-2">{seg.text}</div>
                    </div>
                    <div className="text-xs opacity-70 whitespace-nowrap">{formatMs(seg.duration_ms || 0)}</div>
                  </div>
                </button>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

