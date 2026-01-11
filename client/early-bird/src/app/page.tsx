"use client"
import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Loader2 } from "lucide-react"
import Image from "next/image"
import { io } from "socket.io-client"
import { motion, AnimatePresence } from "framer-motion" // Add this import

export default function Home() {
  // Pre-generated podcast file states
  const [loading, setLoading] = useState(false)
  const [files, setFiles] = useState<string[]>([])
  const [audioBlobs, setAudioBlobs] = useState<{ [key: string]: Blob }>({})
  const [currentFileIndex, setCurrentFileIndex] = useState(-1)
  const [isRecording, setIsRecording] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  // Podcast script state (for interactive audio)
  const [waiting, setWaiting] = useState(true)
  const [indexPlaying, setIndexPlaying] = useState(0)
  const [indexScriptIndexPlaying, setScriptIndexPlaying] = useState(0)
  const [allDone, setAllDone] = useState(false)
  const [dataJson, setDataJson] = useState<any>(null)

  // Refs to hold current state values for asynchronous loops.
  const dataJsonRef = useRef<any>(null)
  const indexPlayingRef = useRef(indexPlaying)
  const indexScriptIndexPlayingRef = useRef(indexScriptIndexPlaying)
  const waitingRef = useRef(waiting)
  const allDoneRef = useRef(allDone)

  // --- NEW: Interrupt State --- 
  // This state flag will be true while we are processing an interrupt.
  const [isInterrupting, setIsInterrupting] = useState(false)
  const isInterruptingRef = useRef(isInterrupting)
  useEffect(() => {
    isInterruptingRef.current = isInterrupting
  }, [isInterrupting])
  // --------------------------------

  // This flag ensures only one podcast loop runs at a time.
  const playbackLoopActiveRef = useRef(false)

  // This ref is used for interactive ElevenLabs audio playback.
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  // Keep our refs in sync with state.
  useEffect(() => {
    dataJsonRef.current = dataJson
  }, [dataJson])
  useEffect(() => {
    indexPlayingRef.current = indexPlaying
  }, [indexPlaying])
  useEffect(() => {
    indexScriptIndexPlayingRef.current = indexScriptIndexPlaying
  }, [indexScriptIndexPlaying])
  useEffect(() => {
    waitingRef.current = waiting
  }, [waiting])
  useEffect(() => {
    allDoneRef.current = allDone
  }, [allDone])

  const [alltext, setAlltext] = useState([])

  // --- SOCKET CONNECTION ---
  useEffect(() => {
    const socket = io("http://localhost:8000")
    socket.on("connect", () => {
      console.log("Connected to WebSocket server")
    })
    socket.on("my_response", (data) => {
      console.log("Received message:", data)
      if (data?.data?.data) {
        setDataJson(data)
      }
    })
    socket.on("disconnect", () => {
      console.log("Disconnected from WebSocket server")
    })
    return () => {
      socket.disconnect()
    }
  }, [])

  // VOICE IDs
  const host_voice = "9BWtsMINqrJLrRacOk9x"
  const guest_voice = "CwhRBWXzGAHq8TQ4Fs17"

  /**
   * Stops any playing audio—both the interactive (ElevenLabs) audio and the pre‐generated <audio> element.
   */
  function stopAllAudio() {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }
  }

  /**
   * Plays text using the ElevenLabs API.
   * If an interrupt is active (checked via isInterruptingRef), the promise immediately resolves false.
   */
  const playAudioAndWait = async (text: string, voice: string) => {
    setAlltext((prev) => [...prev, text])
    return new Promise(async (resolve) => {
      if (isInterruptingRef.current) {
        return resolve(false)
      }
      try {
        const response = await fetch(
          "https://api.elevenlabs.io/v1/text-to-speech/" + voice,
          {
            method: "POST",
            headers: {
              accept: "audio/mpeg",
              "xi-api-key":
                "sk_3a0d683894df57a344b44c211e6f49ecf0a5eae43c003342",
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              text,
              model_id: "eleven_multilingual_v2",
              voice_settings: {
                stability: 0.5,
                similarity_boost: 0.75,
                style: 0.0,
                use_speaker_boost: true,
              },
            }),
          }
        )
        const audioBlob = await response.blob()
        const audio = new Audio()
        currentAudioRef.current = audio
        audio.src = URL.createObjectURL(audioBlob)
        audio.onended = () => {
          currentAudioRef.current = null
          resolve(true)
        }
        audio.play()
        const checkInterruptInterval = setInterval(() => {
          if (isInterruptingRef.current) {
            audio.pause()
            clearInterval(checkInterruptInterval)
            currentAudioRef.current = null
            resolve(false)
          }
        }, 100)
      } catch (error) {
        console.error("Error playing audio:", error)
        resolve(false)
      }
    })
  }

  async function genNext(index: number) {
    await fetch("http://localhost:8000/generate_next", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ next_id: index }),
    })
  }

  /**
   * Main podcast playback loop.
   * It exits immediately if isInterrupting is true.
   * Indexes are advanced only if no interrupt occurs.
   */
  async function continuePlayingPodcast() {
    if (playbackLoopActiveRef.current) return
    playbackLoopActiveRef.current = true
    console.log("Podcast loop started")
    try {
      while (true) {
        // If an interrupt is active, exit the loop.
        if (isInterruptingRef.current) {
          console.log("Podcast loop paused due to interrupt")
          break
        }
        setWaiting(true)
        waitingRef.current = true

        const latestData = dataJsonRef.current
        if (
          allDoneRef.current ||
          !latestData ||
          !latestData.data ||
          !latestData.data.data
        )
          break

        if (indexPlayingRef.current >= latestData.data.data.length) break

        let script = latestData.data.data[indexPlayingRef.current].script.texts
        if (indexScriptIndexPlayingRef.current >= script.length) break

        // Ensure no audio is playing.
        stopAllAudio()

        // Clear waiting state.
        setWaiting(false)
        waitingRef.current = false
        setLoading(false)

        let rem =
          latestData.data.data[indexPlayingRef.current].script.main_remaining

        // If we’re at the end of the current script and more content is expected, trigger generation.
        if (indexScriptIndexPlayingRef.current + 1 === script.length && rem > 0) {
          genNext(indexPlayingRef.current)
        }

        const role = script[indexScriptIndexPlayingRef.current].role
        const text = script[indexScriptIndexPlayingRef.current].content
        const voice = role === "host" ? host_voice : guest_voice

        const playResult = await playAudioAndWait(text, voice)
        // If playback was interrupted, do not update indexes.
        if (!playResult) break

        // Refresh script and remaining count.
        script = dataJsonRef.current.data.data[indexPlayingRef.current].script.texts
        rem = dataJsonRef.current.data.data[indexPlayingRef.current].script.main_remaining

        if (indexScriptIndexPlayingRef.current + 1 < script.length) {
          const newScriptIndex = indexScriptIndexPlayingRef.current + 1
          setScriptIndexPlaying(newScriptIndex)
          indexScriptIndexPlayingRef.current = newScriptIndex
          continue
        }
        if (rem > 0) {
          const newScriptIndex = indexScriptIndexPlayingRef.current + 1
          setScriptIndexPlaying(newScriptIndex)
          indexScriptIndexPlayingRef.current = newScriptIndex
          setWaiting(true)
          waitingRef.current = true
          break
        }
        if (indexPlayingRef.current + 1 < dataJsonRef.current.data.data.length) {
          const newIndexPlaying = indexPlayingRef.current + 1
          setIndexPlaying(newIndexPlaying)
          indexPlayingRef.current = newIndexPlaying
          setScriptIndexPlaying(0)
          indexScriptIndexPlayingRef.current = 0
          continue
        }
        const totalArticles =
          dataJsonRef.current.data.data[indexPlayingRef.current].total_articles
        if (indexPlayingRef.current + 1 < totalArticles) {
          const newIndexPlaying = indexPlayingRef.current + 1
          setIndexPlaying(newIndexPlaying)
          indexPlayingRef.current = newIndexPlaying
          setScriptIndexPlaying(0)
          indexScriptIndexPlayingRef.current = 0
          setWaiting(true)
          waitingRef.current = true
          break
        }
        setAllDone(true)
        allDoneRef.current = true
        break
      }
    } finally {
      playbackLoopActiveRef.current = false
      console.log("Podcast loop ended")
    }
  }

  // Start the podcast loop only when data is available, waiting is true, and no interrupt is active.
  useEffect(() => {
    if (dataJson && waiting && !isInterrupting) {
      continuePlayingPodcast()
    }
  }, [dataJson, waiting, isInterrupting])

  // --- GENERATE PODCAST FILES (Pre-generated audio) ---
  async function generatePodcast(event: React.FormEvent) {
    event.preventDefault()
    setLoading(true)
    try {
      const response = await fetch("http://localhost:8000/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
      if (!response.ok) throw new Error("Failed to generate podcast")
      const data = await response.json()
      console.log(data)
      const fileDir = data.file_urls
      const fileList = Array.from({ length: 7 }, (_, i) => `${fileDir}/interaction_${i + 1}.mp3`)
      console.log(fileList)
      setFiles(fileList)
    } catch (error) {
      console.error("Error:", error)
    }
  }

  /**
   * Monitors microphone input. When a loud sound is detected,
   * stops all audio and triggers speech recognition.
   */
  async function startMicrophoneMonitoring() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const audioContext = new AudioContext()
      const source = audioContext.createMediaStreamSource(stream)
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 2048
      source.connect(analyser)
      const dataArray = new Uint8Array(analyser.frequencyBinCount)
      const amplitudeThreshold = 1000 // Adjust as needed.
      let silenceTimeout: ReturnType<typeof setTimeout> | null = null

      function checkVolume() {
        analyser.getByteTimeDomainData(dataArray)
        let sum = 0
        for (let i = 0; i < dataArray.length; i++) {
          sum += Math.abs(dataArray[i] - 128)
        }
        const avg = sum / dataArray.length

        if (avg > amplitudeThreshold) {
          if (!isInterruptingRef.current) {
            console.log("Interrupt detected!")
            stopAllAudio()
            setIsInterrupting(true)
            startSpeechRecognition()
          }
          if (silenceTimeout) clearTimeout(silenceTimeout)
          silenceTimeout = setTimeout(() => {
            if (recognitionRef.current) recognitionRef.current.stop()
          }, 1000)
        }
        requestAnimationFrame(checkVolume)
      }
      checkVolume()
    } catch (error) {
      console.error("Error starting microphone monitoring:", error)
    }
  }

  /**
   * Starts browser speech recognition.
   * When a result is received, handle the interrupt.
   */
  function startSpeechRecognition() {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      console.error("SpeechRecognition not supported in this browser.")
      return
    }
    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = "en-US"

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0][0].transcript
      console.log("Transcribed:", transcript)
      handleInterrupt(transcript)
    }
    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event)
      // Clear the interrupt flag and resume the podcast loop.
      setIsInterrupting(false)
      continuePlayingPodcast()
    }
    recognition.onend = () => {
      // If ended without a result, treat as empty transcript.
      if (isInterruptingRef.current) {
        handleInterrupt("")
      }
    }
    recognition.start()
    recognitionRef.current = recognition
  }

  /**
   * Handles the interrupt by sending the transcript to the backend.
   * Plays the response audio, then clears the interrupt flag and resumes the podcast.
   */
  async function handleInterrupt(transcript: string) {
    console.log("Handling interrupt with transcript:", transcript)
    if (transcript && dataJsonRef.current && !waitingRef.current) {
      try {
        const response = await fetch("http://localhost:8000/generate_answer", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            index: indexPlayingRef.current,
            question: transcript,
          }),
        })
        if (!response.ok) {
          console.error("Interrupt API request failed")
        } else {
          const data = await response.json()
          const message = data.message
          console.log("Interrupt API response:", message)
          // Play the answer audio.
          await playAudioAndWait(message, guest_voice)
        }
      } catch (error) {
        console.error("Error in interrupt API request:", error)
      }
    }
    // Clear the interrupt flag and resume the podcast loop.
    setIsInterrupting(false)
    continuePlayingPodcast()
  }

  // Start monitoring the microphone when the component mounts.
  useEffect(() => {
    startMicrophoneMonitoring()
  }, [])

  // --- Pre-generated Podcast Playback ---
  useEffect(() => {
    if (currentFileIndex >= 0 && currentFileIndex < files.length && audioRef.current) {
      // Stop any interactive audio.
      stopAllAudio()
      const currentFile = files[currentFileIndex]
      const blob = audioBlobs[currentFile]
      if (blob) {
        audioRef.current.src = URL.createObjectURL(blob)
        audioRef.current.play()
        setIsPlaying(true)
      }
    }
  }, [currentFileIndex, files, audioBlobs])

  const handleAudioEnd = () => {
    if (currentFileIndex < files.length - 1) {
      setCurrentFileIndex((prev) => prev + 1)
    } else {
      setIsPlaying(false)
    }
  }

  // --- Manual Interrupt Recording (Optional) ---
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: "audio/mp3" })
        const formData = new FormData()
        formData.append("audio", audioBlob)
        try {
          const response = await fetch("http://localhost:8000/interrupt", {
            method: "POST",
            body: formData,
          })
          if (!response.ok) throw new Error("Failed to process interrupt")
          const responseBlob = await response.blob()
          // Insert the interrupt response right after the current file.
          const newFiles = [...files]
          const responseFileName = `interrupt-response-${Date.now()}.mp3`
          newFiles.splice(currentFileIndex + 1, 0, responseFileName)
          setFiles(newFiles)
          setAudioBlobs((prev) => ({
            ...prev,
            [responseFileName]: responseBlob,
          }))
        } catch (error) {
          console.error("Error processing interrupt:", error)
        }
      }
      recorder.start()
      setIsRecording(true)
    } catch (error) {
      console.error("Error starting recording:", error)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-center space-y-4">
        <Image
          src="/logo.jpg"
          alt="EarlyBird Logo"
          width={64}
          height={64}
          className="mx-auto dark:invert"
        />
        <h1 className="text-4xl font-bold">Welcome to EarlyBird</h1>
        <p className="text-xl text-muted-foreground">
          Start your day with personalized podcasts
        </p>
      </div>

      <form onSubmit={generatePodcast} className="text-center">
        {!dataJson && <Button type="submit" size="lg" disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating Podcast...
            </>
          ) : (
            "Generate Today's Podcast"
          )}
        </Button>}
      </form>

      {files.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Your Morning Tech Podcast</CardTitle>
            <CardDescription>
              Article {indexPlaying + 1} of {5}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col-reverse gap-3">
              <AnimatePresence mode="popLayout">
                {alltext.map((text, index) => (
                  <motion.div
                    key={text + index}
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3 }}
                    className={`
                      ${index === alltext.length - 1 
                        ? "text-base font-medium text-foreground" 
                        : "text-sm text-muted-foreground"
                      }
                      transition-all duration-200
                    `}
                  >
                    {text}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
            {isPlaying && currentFileIndex < 6 && (
              <div className="flex justify-center gap-4">
                <Button
                  onClick={startRecording}
                  disabled={isRecording}
                  className="bg-red-500 hover:bg-red-600"
                >
                  Start Interrupt
                </Button>
                <Button onClick={stopRecording} disabled={!isRecording}>
                  Stop Interrupt
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}