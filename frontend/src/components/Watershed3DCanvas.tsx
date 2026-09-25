"use client";

import React, { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, OrbitControls } from "@react-three/drei";
import * as THREE from "three";

// ==========================================
// 1. Avon Arch Dam Model (Check Dam)
// Inspired by Eastern Arch Avon Dam (NSW)
// ==========================================
function AvonArchDamModel() {
  const groupRef = useRef<THREE.Group>(null);
  const waterRef = useRef<THREE.Mesh>(null);
  const cascadeRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(t * 0.25) * 0.22;
    }
    if (waterRef.current) {
      waterRef.current.position.y = 0.35 + Math.sin(t * 2) * 0.025;
    }
    if (cascadeRef.current) {
      cascadeRef.current.scale.y = 1 + Math.sin(t * 4) * 0.08;
    }
  });

  return (
    <group ref={groupRef} scale={[0.85, 0.85, 0.85]}>
      {/* Canyon Rock Abutments Left & Right */}
      <mesh position={[-2.4, 0.4, 0]} rotation={[0, 0.2, 0.1]}>
        <cylinderGeometry args={[1.2, 1.6, 2.2, 7]} />
        <meshStandardMaterial color="#362B4A" roughness={0.9} flatShading />
      </mesh>
      <mesh position={[2.4, 0.4, 0]} rotation={[0, -0.2, -0.1]}>
        <cylinderGeometry args={[1.2, 1.6, 2.2, 7]} />
        <meshStandardMaterial color="#362B4A" roughness={0.9} flatShading />
      </mesh>

      {/* Curved Arch Dam Wall (Avon Arch Dam structure) */}
      <mesh position={[0, 0.5, 0]} rotation={[0, Math.PI, 0]}>
        <cylinderGeometry args={[2.5, 2.6, 1.6, 24, 1, false, Math.PI * 0.25, Math.PI * 0.5]} />
        <meshStandardMaterial color="#9B8DC9" roughness={0.35} metalness={0.1} />
      </mesh>

      {/* Spillway Crest Pillars */}
      <mesh position={[-0.4, 1.35, -0.2]}>
        <boxGeometry args={[0.15, 0.3, 0.4]} />
        <meshStandardMaterial color="#7A6BA8" roughness={0.4} />
      </mesh>
      <mesh position={[0.4, 1.35, -0.2]}>
        <boxGeometry args={[0.15, 0.3, 0.4]} />
        <meshStandardMaterial color="#7A6BA8" roughness={0.4} />
      </mesh>

      {/* Downstream Stepped Stilling Basin Apron */}
      <mesh position={[0, -0.3, 0.9]}>
        <boxGeometry args={[3.2, 0.3, 1.6]} />
        <meshStandardMaterial color="#281F3D" roughness={0.95} />
      </mesh>

      {/* Upstream Deep Reservoir Water Surface */}
      <mesh ref={waterRef} position={[0, 0.35, -1.1]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[2.2, 32]} />
        <meshStandardMaterial color="#0284C7" roughness={0.1} metalness={0.8} transparent opacity={0.9} />
      </mesh>

      {/* Cascade Waterfall Stream Spillway */}
      <mesh ref={cascadeRef} position={[0, 0.4, 0.3]} rotation={[0.5, 0, 0]}>
        <planeGeometry args={[0.7, 1.1]} />
        <meshStandardMaterial color="#38BDF8" roughness={0.05} metalness={0.9} transparent opacity={0.85} />
      </mesh>
    </group>
  );
}

// ==========================================
// 2. Farm Pond Kit Model
// Inspired by Farm Pond Asset Kit (Earthen Water Storage Basin)
// ==========================================
function FarmPondKitModel() {
  const groupRef = useRef<THREE.Group>(null);
  const waterRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(t * 0.22) * 0.25;
    }
    if (waterRef.current) {
      waterRef.current.scale.x = 1 + Math.sin(t * 1.5) * 0.02;
      waterRef.current.scale.y = 1 + Math.cos(t * 1.5) * 0.02;
    }
  });

  return (
    <group ref={groupRef} scale={[0.85, 0.85, 0.85]}>
      {/* Outer Agricultural Landscape Terrain */}
      <mesh position={[0, -0.4, 0]}>
        <boxGeometry args={[4.8, 0.3, 4.4]} />
        <meshStandardMaterial color="#2E2442" roughness={0.9} />
      </mesh>

      {/* Earthen Embankment Bund Ring */}
      <mesh position={[0, -0.05, 0]}>
        <cylinderGeometry args={[2.1, 2.7, 0.5, 12]} />
        <meshStandardMaterial color="#554475" roughness={0.85} flatShading />
      </mesh>

      {/* Excavated Pond Basin Inner Liner */}
      <mesh position={[0, 0.08, 0]}>
        <cylinderGeometry args={[1.7, 1.2, 0.45, 12]} />
        <meshStandardMaterial color="#1C162E" roughness={0.9} />
      </mesh>

      {/* Farm Pond Water Body Surface */}
      <mesh ref={waterRef} position={[0, 0.18, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[1.55, 32]} />
        <meshStandardMaterial color="#0EA5E9" roughness={0.12} metalness={0.82} transparent opacity={0.92} />
      </mesh>

      {/* Inflow Feeder Canal Channel */}
      <mesh position={[-2.0, 0.05, -0.2]} rotation={[0, 0, -0.08]}>
        <boxGeometry args={[1.2, 0.15, 0.5]} />
        <meshStandardMaterial color="#38BDF8" roughness={0.2} transparent opacity={0.8} />
      </mesh>

      {/* Agricultural Vegetation & Trees around Bund */}
      <mesh position={[1.5, 0.35, 1.1]}>
        <dodecahedronGeometry args={[0.35, 0]} />
        <meshStandardMaterial color="#22C55E" roughness={0.6} flatShading />
      </mesh>
      <mesh position={[1.7, 0.25, 0.6]}>
        <dodecahedronGeometry args={[0.25, 0]} />
        <meshStandardMaterial color="#16A34A" roughness={0.6} flatShading />
      </mesh>
      <mesh position={[-1.4, 0.32, -1.3]}>
        <dodecahedronGeometry args={[0.3, 0]} />
        <meshStandardMaterial color="#15803D" roughness={0.6} flatShading />
      </mesh>
    </group>
  );
}

// ==========================================
// 3. Low-Poly River & Recharge Basin (Percolation Tank)
// Inspired by Low Poly River & Channel Silt Traps
// ==========================================
function LowPolyRiverModel() {
  const groupRef = useRef<THREE.Group>(null);
  const waterRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(t * 0.28) * 0.22;
    }
    if (waterRef.current) {
      waterRef.current.position.y = 0.12 + Math.sin(t * 2.2) * 0.02;
    }
  });

  return (
    <group ref={groupRef} scale={[0.82, 0.82, 0.82]}>
      {/* Terraced Landscape Terrain Blocks */}
      <mesh position={[0, -0.45, 0]}>
        <boxGeometry args={[4.6, 0.3, 4.2]} />
        <meshStandardMaterial color="#261C39" roughness={0.9} flatShading />
      </mesh>
      <mesh position={[-1.6, -0.15, 0]}>
        <boxGeometry args={[1.4, 0.35, 4.0]} />
        <meshStandardMaterial color="#443563" roughness={0.85} flatShading />
      </mesh>
      <mesh position={[1.6, -0.15, 0]}>
        <boxGeometry args={[1.4, 0.35, 4.0]} />
        <meshStandardMaterial color="#443563" roughness={0.85} flatShading />
      </mesh>

      {/* Meandering River Channel Bed */}
      <mesh position={[0, -0.2, 0]}>
        <boxGeometry args={[1.8, 0.25, 4.0]} />
        <meshStandardMaterial color="#191329" roughness={0.95} />
      </mesh>

      {/* Percolation Rock Weirs / Check Steps */}
      <mesh position={[0, 0.02, -1.0]}>
        <boxGeometry args={[1.7, 0.2, 0.3]} />
        <meshStandardMaterial color="#7A68A3" roughness={0.7} flatShading />
      </mesh>
      <mesh position={[0, 0.02, 0.8]}>
        <boxGeometry args={[1.7, 0.2, 0.3]} />
        <meshStandardMaterial color="#7A68A3" roughness={0.7} flatShading />
      </mesh>

      {/* Translucent Low Poly River Water Surface */}
      <mesh ref={waterRef} position={[0, 0.12, 0]}>
        <boxGeometry args={[1.6, 0.08, 3.8]} />
        <meshStandardMaterial color="#06B6D4" roughness={0.08} metalness={0.85} transparent opacity={0.88} />
      </mesh>

      {/* Riverbank Boulders & Vegetation */}
      <mesh position={[-0.9, 0.15, -0.5]}>
        <dodecahedronGeometry args={[0.2, 0]} />
        <meshStandardMaterial color="#64748B" roughness={0.9} flatShading />
      </mesh>
      <mesh position={[0.9, 0.15, 0.4]}>
        <dodecahedronGeometry args={[0.22, 0]} />
        <meshStandardMaterial color="#64748B" roughness={0.9} flatShading />
      </mesh>
      <mesh position={[-1.1, 0.2, 1.2]}>
        <dodecahedronGeometry args={[0.3, 0]} />
        <meshStandardMaterial color="#10B981" roughness={0.6} flatShading />
      </mesh>
    </group>
  );
}

// ==========================================
// 4. Sentinel-2 / Bhuvan GIS Earth Observation Satellite
// Inspired by Remote Sensing Telemetry Satellite
// ==========================================
function SatelliteGISModel() {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (groupRef.current) {
      groupRef.current.rotation.y = t * 0.35;
      groupRef.current.rotation.z = Math.sin(t * 0.5) * 0.08;
    }
  });

  return (
    <group ref={groupRef} scale={[0.85, 0.85, 0.85]}>
      {/* Central Satellite Body (Gold Thermal Blanket Foil) */}
      <mesh position={[0, 0.4, 0]}>
        <cylinderGeometry args={[0.5, 0.55, 1.2, 12]} />
        <meshStandardMaterial color="#D97706" metalness={0.9} roughness={0.25} />
      </mesh>

      {/* Main Bus Silver Electronics Bay */}
      <mesh position={[0, 1.1, 0]}>
        <cylinderGeometry args={[0.45, 0.45, 0.4, 12]} />
        <meshStandardMaterial color="#94A3B8" metalness={0.8} roughness={0.3} />
      </mesh>

      {/* Sensor Lens Optic Housing (Pointing Down) */}
      <mesh position={[0, -0.3, 0]}>
        <cylinderGeometry args={[0.35, 0.25, 0.3, 16]} />
        <meshStandardMaterial color="#0F172A" metalness={0.95} roughness={0.1} />
      </mesh>

      {/* Dual Solar Panel Arrays Left & Right */}
      <mesh position={[-1.7, 0.4, 0]}>
        <boxGeometry args={[1.8, 0.04, 0.6]} />
        <meshStandardMaterial color="#1E40AF" metalness={0.85} roughness={0.15} />
      </mesh>
      <mesh position={[1.7, 0.4, 0]}>
        <boxGeometry args={[1.8, 0.04, 0.6]} />
        <meshStandardMaterial color="#1E40AF" metalness={0.85} roughness={0.15} />
      </mesh>

      {/* Solar Panel Connecting Rods */}
      <mesh position={[-0.7, 0.4, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.04, 0.04, 0.4, 8]} />
        <meshStandardMaterial color="#E2E8F0" metalness={0.9} />
      </mesh>
      <mesh position={[0.7, 0.4, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.04, 0.04, 0.4, 8]} />
        <meshStandardMaterial color="#E2E8F0" metalness={0.9} />
      </mesh>

      {/* High-Gain Parabolic Antenna Dish */}
      <mesh position={[0, 1.45, 0]} rotation={[Math.PI * 0.15, 0, 0]}>
        <sphereGeometry args={[0.35, 16, 8, 0, Math.PI * 2, 0, Math.PI * 0.4]} />
        <meshStandardMaterial color="#E2E8F0" metalness={0.6} roughness={0.4} side={THREE.DoubleSide} />
      </mesh>

      {/* Earth Surface Sphere Below Satellite */}
      <mesh position={[0, -2.4, 0]}>
        <sphereGeometry args={[1.8, 32, 32]} />
        <meshStandardMaterial color="#0284C7" roughness={0.5} metalness={0.3} />
      </mesh>

      {/* Sensor Multispectral Scanning Laser Beam */}
      <mesh position={[0, -1.2, 0]}>
        <coneGeometry args={[0.9, 1.5, 16, 1, true]} />
        <meshStandardMaterial color="#A855F7" transparent opacity={0.25} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

// ==========================================
// Main Cycling 3D Canvas Controller
// ==========================================
export default function Watershed3DCanvas({
  activeStructureIndex,
  onSelectStructure,
}: {
  activeStructureIndex: number;
  onSelectStructure: (idx: number) => void;
}) {
  return (
    <div className="relative w-full h-[420px] md:h-[480px] rounded-2xl overflow-hidden bg-[#161226]/90 border border-[#A997DF]/30 shadow-2xl">
      {/* Interactive Lightweight WebGL Canvas */}
      <Canvas
        camera={{ position: [0, 2.5, 4.5], fov: 45 }}
        gl={{ powerPreference: "high-performance", antialias: true }}
      >
        <ambientLight intensity={0.7} />
        <directionalLight position={[5, 8, 5]} intensity={1.2} color="#E2D9F3" />
        <pointLight position={[-4, -2, -4]} intensity={0.5} color="#A997DF" />

        <Float speed={2} rotationIntensity={0.2} floatIntensity={0.4}>
          {activeStructureIndex === 0 && <AvonArchDamModel />}
          {activeStructureIndex === 1 && <FarmPondKitModel />}
          {activeStructureIndex === 2 && <LowPolyRiverModel />}
          {activeStructureIndex === 3 && <SatelliteGISModel />}
        </Float>

        <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={0.8} maxPolarAngle={Math.PI / 2.2} />
      </Canvas>

      {/* Floating Structure Selector Pills */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center space-x-1.5 bg-[#161226]/95 backdrop-blur-md px-3 py-1.5 rounded-full border border-[#A997DF]/30 shadow-xl z-20 max-w-[95%] overflow-x-auto">
        {[
          { label: "Avon Arch Dam", icon: "🧱" },
          { label: "Farm Pond Kit", icon: "🌊" },
          { label: "Low-Poly River", icon: "🏞️" },
          { label: "Sentinel Satellite", icon: "🛰️" },
        ].map((item, idx) => (
          <button
            key={item.label}
            onClick={() => onSelectStructure(idx)}
            className={`px-2.5 py-1 text-xs font-bold rounded-full transition-all cursor-pointer flex items-center gap-1 shrink-0 ${
              activeStructureIndex === idx
                ? "bg-gradient-to-r from-[#7058B6] to-[#5B44A0] text-white shadow-md border border-purple-400/40"
                : "text-[#C3B8DF] hover:text-white hover:bg-[#221C3A]"
            }`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
