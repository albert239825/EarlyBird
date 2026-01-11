import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import './App.css';

function App() {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);

  useEffect(() => {
    // Scene setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    cameraRef.current = camera;
    sceneRef.current = scene;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    mountRef.current.appendChild(renderer.domElement);

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    camera.position.z = 100;
    controls.update();

    // Generate major nodes
    const majorNodes = [];
    const majorNodeObjects = [];
    for (let i = 0; i < 50; i++) {
      majorNodes.push({
        position: new THREE.Vector3(
          (Math.random() - 0.5) * 100,
          (Math.random() - 0.5) * 100,
          (Math.random() - 0.5) * 100
        ),
        connections: []
      });
    }

    // Connect major nodes randomly
    majorNodes.forEach((node, i) => {
      const numConnections = Math.floor(Math.random() * 5) + 1;
      for (let j = 0; j < numConnections; j++) {
        const targetIndex = Math.floor(Math.random() * majorNodes.length);
        if (targetIndex !== i && !node.connections.includes(targetIndex)) {
          node.connections.push(targetIndex);
          majorNodes[targetIndex].connections.push(i);
        }
      }
    });

    // Create visual elements for major nodes
    majorNodes.forEach((node, i) => {
      const geometry = new THREE.SphereGeometry(4, 32, 32); // Increased radius to 5
      const color = new THREE.Color().setHSL(i / 50, 0.7, 0.5);
      const material = new THREE.MeshPhongMaterial({ color });
      const sphere = new THREE.Mesh(geometry, material);
      sphere.position.copy(node.position);
      scene.add(sphere);
      majorNodeObjects.push(sphere);
    });

    // Create connections between major nodes
    majorNodes.forEach((node, i) => {
      node.connections.forEach(targetIndex => {
        const geometry = new THREE.BufferGeometry().setFromPoints([
          node.position,
          majorNodes[targetIndex].position
        ]);
        const material = new THREE.LineBasicMaterial({ color: 0xaaaaaa });
        const line = new THREE.Line(geometry, material);
        scene.add(line);
      });
    });

    // Create minor nodes
    for (let i = 0; i < 500; i++) {
      const parentIndex = Math.floor(Math.random() * majorNodes.length);
      const parent = majorNodes[parentIndex];
      const distance = Math.random() * 5 + 3;
      const position = new THREE.Vector3(
        parent.position.x + (Math.random() - 0.5) * distance,
        parent.position.y + (Math.random() - 0.5) * distance,
        parent.position.z + (Math.random() - 0.5) * distance
      );

      const geometry = new THREE.SphereGeometry(1, 16, 16); // Increased radius to 1
      const material = new THREE.MeshPhongMaterial({
        color: new THREE.Color().setHSL(parentIndex / 50, 0.7, 0.7)
      });
      const sphere = new THREE.Mesh(geometry, material);
      sphere.position.copy(position);
      scene.add(sphere);
    }

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x404040);
    scene.add(ambientLight);
    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(10, 10, 10);
    scene.add(light);

    // Animation
    function animate() {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }
    animate();

    // Cleanup
    return () => {
      if (mountRef.current) {
        mountRef.current.removeChild(renderer.domElement);
      }
    };
  }, []);

  useEffect(() => {
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    function onMouseClick(event) {
      mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

      raycaster.setFromCamera(mouse, cameraRef.current);

      const intersects = raycaster.intersectObjects(sceneRef.current.children);

      if (intersects.length > 0) {
        const intersectedObject = intersects[0].object;

        if (intersectedObject instanceof THREE.Mesh) {
          intersectedObject.material.emissive.setHex(0xffffff);
          setTimeout(() => {
            intersectedObject.material.emissive.setHex(0x000000);
          }, 500);
        }
      }
    }

    window.addEventListener('click', onMouseClick);

    return () => {
      window.removeEventListener('click', onMouseClick);
    };
  }, []);

  return <div ref={mountRef} />;
}

export default App;
