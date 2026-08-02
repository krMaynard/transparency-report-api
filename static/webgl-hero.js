import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.179.1/build/three.module.js";

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const canvases = document.querySelectorAll("[data-webgl-hero] .webgl-hero__canvas");

if (!reduceMotion.matches) {
  canvases.forEach((canvas) => {
    const host = canvas.closest("[data-webgl-hero]");
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, preserveDrawingBuffer: true });
    const cluster = new THREE.Group();
    const nodes = new THREE.Group();
    const links = new THREE.Group();
    let frameId = 0;

    camera.position.set(0, 0, 8.8);
    scene.add(cluster, nodes, links);

    const primary = 0x4ec1b1;
    const secondary = 0x8fe0d7;
    const mesh = new THREE.Mesh(
      new THREE.IcosahedronGeometry(2.15, 2),
      new THREE.MeshBasicMaterial({
        color: primary,
        wireframe: true,
        transparent: true,
        opacity: 0.24
      })
    );
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(1.7, 0.018, 10, 120),
      new THREE.MeshBasicMaterial({
        color: secondary,
        transparent: true,
        opacity: 0.62
      })
    );
    ring.rotation.x = Math.PI / 2.8;
    cluster.add(mesh, ring);

    const nodeGeometry = new THREE.SphereGeometry(0.03, 8, 8);
    const nodeMaterial = new THREE.MeshBasicMaterial({ color: secondary, transparent: true, opacity: 0.66 });
    const positions = [];
    for (let i = 0; i < 54; i += 1) {
      const radius = 2.5 + Math.random() * 2.2;
      const angle = Math.random() * Math.PI * 2;
      const z = (Math.random() - 0.5) * 2.5;
      positions.push(new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius * 0.72, z));
    }
    positions.forEach((position, i) => {
      const node = new THREE.Mesh(nodeGeometry, nodeMaterial);
      node.position.copy(position);
      node.userData = { angle: Math.atan2(position.y / 0.72, position.x), radius: Math.hypot(position.x, position.y / 0.72), speed: 0.0012 + (i % 7) * 0.00028 };
      nodes.add(node);
    });

    const linkMaterial = new THREE.LineBasicMaterial({ color: primary, transparent: true, opacity: 0.16 });
    for (let i = 0; i < positions.length - 1; i += 3) {
      const geometry = new THREE.BufferGeometry().setFromPoints([positions[i], positions[(i + 5) % positions.length]]);
      links.add(new THREE.Line(geometry, linkMaterial));
    }

    const resize = () => {
      const width = Math.max(1, host.clientWidth);
      const height = Math.max(1, host.clientHeight);
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      renderer.setPixelRatio(dpr);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      cluster.position.x = width > 720 ? width / height * 0.95 : 0.7;
      nodes.position.copy(cluster.position);
      links.position.copy(cluster.position);
      const scale = width > 720 ? 1 : 0.76;
      cluster.scale.setScalar(scale);
      nodes.scale.setScalar(scale);
      links.scale.setScalar(scale);
    };

    const render = (time) => {
      const t = time * 0.001;
      cluster.rotation.y = t * 0.16;
      cluster.rotation.x = Math.sin(t * 0.32) * 0.1;
      nodes.rotation.y = cluster.rotation.y;
      links.rotation.y = cluster.rotation.y;
      ring.rotation.z = t * 0.18;
      nodes.children.forEach((node) => {
        node.userData.angle += node.userData.speed;
        node.position.x = Math.cos(node.userData.angle) * node.userData.radius;
        node.position.y = Math.sin(node.userData.angle) * node.userData.radius * 0.72;
      });
      renderer.render(scene, camera);
      frameId = window.requestAnimationFrame(render);
    };

    try {
      resize();
      host.classList.add("is-webgl-ready");
      frameId = window.requestAnimationFrame(render);
      window.addEventListener("resize", resize, { passive: true });
      reduceMotion.addEventListener("change", () => {
        if (reduceMotion.matches && frameId) window.cancelAnimationFrame(frameId);
      }, { once: true });
    } catch (error) {
      host.classList.remove("is-webgl-ready");
    }
  });
}
