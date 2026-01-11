import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

interface PodcastMetadata {
    title: string;
    description: string;
    author: string;
    date: string;
}

const PodcastViewPage = () => {
    const router = useRouter();
    const { id } = router.query;
    const [audioSrc, setAudioSrc] = useState<string | null>(null);
    const [metadata, setMetadata] = useState<PodcastMetadata | null>(null);

    useEffect(() => {
        if (id) {
            // Fetch audio file
            fetch(`/api/podcast/audio/${id}`)
                .then(response => response.json())
                .then(data => {
                    setAudioSrc(data.audioUrl);
                })
                .catch(error => {
                    console.error('Error fetching audio file:', error);
                });

            // Fetch metadata
            fetch(`/api/podcast/metadata/${id}`)
                .then(response => response.json())
                .then(data => {
                    setMetadata(data);
                })
                .catch(error => {
                    console.error('Error fetching metadata:', error);
                });
        }
    }, [id]);

    if (!id) {
        return <div>Loading...</div>;
    }

    return (
        <div>
            {metadata && (
                <div>
                    <h1>{metadata.title}</h1>
                    <p>{metadata.description}</p>
                    <p><strong>Author:</strong> {metadata.author}</p>
                    <p><strong>Date:</strong> {metadata.date}</p>
                </div>
            )}
            {audioSrc ? (
                <audio controls>
                    <source src={audioSrc} type="audio/mpeg" />
                    Your browser does not support the audio element.
                </audio>
            ) : (
                <p>Loading audio...</p>
            )}
        </div>
    );
};

export default PodcastViewPage;