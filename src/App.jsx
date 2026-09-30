import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import GhostFibers from './components/GhostFibers';
import ParserSandbox from './components/ParserSandbox';
import DomainGallery from './components/DomainGallery';
import ProofDashboard from './components/ProofDashboard';
import styles from './App.module.css';

function App() {
  const [activeTab, setActiveTab] = useState('sandbox');

  return (
    <div style={{ width: '100%', minHeight: '100vh', position: 'relative', backgroundColor: '#0A0817', overflowX: 'hidden' }}>
      <GhostFibers 
        blueBoost={1.25} 
        brightness={2} 
        dpr={1} 
        glowColor="#3437A0" 
        glowFalloff={10} 
        glowIntensity={1.6} 
        grain={0} 
        layerSpeed={0.08} 
        layers={4} 
        lineColor="#140E35" 
        lineFrequency={5} 
        lineSharpness={16} 
        lineSpacing={2} 
        rotation={0} 
        rotationSpeed={0.25} 
        scale={2} 
        speed={0.2} 
        twist={0.1} 
        twistFrequency={5} 
        twistSpeed={1.2} 
        vignette={0.8} 
        waveAmplitude={0.015} 
        waveFrequency={3} 
        waveSpeed={0.15} 
      />
      
      <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', zIndex: 10 }}>
        <header className={styles.header}>
          <motion.h1 
            className={styles.title}
          >
            PARSE RESUME USING NER
          </motion.h1>
          <div className={styles.subtitle}>Resume Intelligence Engine</div>
          <div className={styles.credits}>Project by Abu Dujana, Nithish & Pravina</div>
        </header>

        <nav className={styles.nav}>
          <button 
            className={`${styles.navButton} ${activeTab === 'sandbox' ? styles.navButtonActive : ''}`}
            onClick={() => setActiveTab('sandbox')}
          >
            🔬 Parser Sandbox
          </button>
          <button 
            className={`${styles.navButton} ${activeTab === 'gallery' ? styles.navButtonActive : ''}`}
            onClick={() => setActiveTab('gallery')}
          >
            🌐 Domain Gallery
          </button>
          <button 
            className={`${styles.navButton} ${activeTab === 'proof' ? styles.navButtonActive : ''}`}
            onClick={() => setActiveTab('proof')}
          >
            📊 Proof of Work
          </button>
        </nav>

        <main className={styles.content}>
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              {activeTab === 'sandbox' && <ParserSandbox />}
              {activeTab === 'gallery' && <DomainGallery />}
              {activeTab === 'proof' && <ProofDashboard />}
            </motion.div>
          </AnimatePresence>
        </main>

        <footer className={styles.footer}>
          Powered by Custom spaCy NER + Computer Vision
        </footer>
      </div>
    </div>
  );
}

export default App;
