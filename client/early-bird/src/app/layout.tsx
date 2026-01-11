import Link from "next/link"
import Image from "next/image"
import { Inter } from "next/font/google"
import "./globals.css"
import { ReactNode } from "react";
const inter = Inter({ subsets: ["latin"] })

export const metadata = {
  title: "EarlyBird - Daily Podcast Generator",
  description: "Start your day with personalized podcasts based on your interests",
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="flex flex-col min-h-screen">
          <header className="bg-primary text-primary-foreground shadow-md">
            <nav className="container mx-auto px-4 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Image
                    src="/logo.jpg"
                    alt="EarlyBird Logo"
                    width={32}
                    height={32}
                    className="dark:invert"
                  />
                  <span className="text-xl font-bold">EarlyBird</span>
                </div>
                <ul className="flex space-x-4">
                  <li>
                    <Link href="/" className="hover:underline">
                      Home
                    </Link>
                  </li>
                  <li>
                    <Link href="/previous-podcasts" className="hover:underline">
                      Previous Podcasts
                    </Link>
                  </li>
                  <li>
                    <Link href="/podcast-graph" className="hover:underline">
                      Podcast Graph
                    </Link>
                  </li>
                </ul>
              </div>
            </nav>
          </header>
          <main className="flex-grow container mx-auto px-4 py-8">{children}</main>
          <footer className="bg-primary text-primary-foreground py-4">
            <div className="container mx-auto px-4 text-center">
              © 2025 EarlyBird. Start your day with personalized podcasts.
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}

