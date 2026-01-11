"use client";

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import styles from './PodcastGraph.module.css';

// Dynamically import Plotly to ensure it runs only on the client-side
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

// Define the structure of a Node
interface Node {
  id: number;
  position: [number, number, number];
  label: string;
  interest_score: number;
}

const PodcastGraph: React.FC = () => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [x, setX] = useState<number[]>([]);
  const [y, setY] = useState<number[]>([]);
  const [z, setZ] = useState<number[]>([]);
  const [labels, setLabels] = useState<string[]>([]);
  const [colors, setColors] = useState<string[]>([]);

  useEffect(() => {
    // Fetch nodes data from the API
    const fetchNodes = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/graph_init');
        const data = await response.json();
        setNodes(data.nodes);
      } catch (error) {
        console.error('Error fetching graph data:', error);
      }
    };

    fetchNodes();
  }, []);

  useEffect(() => {
    // Update coordinates, labels, and colors when nodes change
    if (nodes.length > 0) {
      setX(nodes.map((node) => node.position[0]));
      setY(nodes.map((node) => node.position[1]));
      setZ(nodes.map((node) => node.position[2]));
      setLabels(nodes.map((node) => node.label));
      setColors(
        nodes.map((node) => {
          const score = node.interest_score;
          // Calculate the color based on interest_score
          const red = 255;
          const green = 255;
          const blue = Math.round(255 * (1 - score));
          return `rgb(${red}, ${green}, ${blue})`;
        })
      );
    }
  }, [nodes]);

  // Handler for click events on the plot
  const handlePlotClick = async (event: any) => {
    if (event && event.points && event.points.length > 0) {
      console.log('click event');
      const point = event.points[0];
      const xCoord = point.x;
      const yCoord = point.y;
      const zCoord = point.z;
      try {
        const response = await fetch(
          `http://localhost:8000/api/graph_update/${xCoord}/${yCoord}/${zCoord}`
        );
        const data = await response.json();
        setNodes(data.nodes);
      } catch (error) {
        console.error('Error calling graph update function:', error);
      }
    }
  };

  return (
    <div className={styles.container}>
      <Plot
        data={[
          {
            x,
            y,
            z,
            mode: 'markers+text',
            marker: { size: 10, color: colors }, // Increased marker size
            type: 'scatter3d',
            text: labels,
            hoverinfo: 'text',
            textposition: 'top center',
            textfont: {
              size: 15, // Increased text size
              color: '#A6EC99', // White text color
            },
          },
        ]}
        layout={{
          template: 'plotly_dark', // Apply dark theme
          scene: {
            xaxis: { visible: false },
            yaxis: { visible: false },
            zaxis: { visible: false },
            camera: {
              eye: { x: 0.4, y: 0.4, z: 0.4 }, // Adjust these values to set the desired zoom level
            },
            aspectmode: 'data', // Ensures the aspect ratio follows the data
          },
          margin: { l: 0, r: 0, t: 0, b: 0 }, // Remove margins
          paper_bgcolor: '#121212', // Dark background color
        }}
        useResizeHandler={true}
        style={{ width: '100%', height: '100%' }} // Ensure the plot fills the container
        onClick={handlePlotClick}
      />
    </div>
  );
};

export default PodcastGraph;
