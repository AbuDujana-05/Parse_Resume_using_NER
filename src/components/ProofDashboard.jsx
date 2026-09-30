import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import LiquidGlassCard from './LiquidGlassCard';
import TerminalReplay from './TerminalReplay';
import styles from './ProofDashboard.module.css';
import { apiFetch } from '../api';

const ProofDashboard = () => {
  const [metrics, setMetrics] = useState(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      // Load bundled proof first so the Netlify site never depends on the Python
      // server merely to render the proof dashboard.
      try {
        const fallback = await fetch('/proof/training_metrics.json');
        if (fallback.ok) setMetrics({ metrics: await fallback.json() });
      } catch { /* keep dashboard available */ }

      try {
        const response = await apiFetch('/api/metrics');
        if (response.ok) {
          const data = await response.json();
          setMetrics(data);
        }
      } catch { /* bundled proof is the reliable fallback */ }
      finally {
        setLoadingMetrics(false);
      }
    };
    fetchMetrics();
  }, []);

  const containerVariants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  };

  const handleImageError = (e) => {
    e.target.style.display = 'none';
    e.target.nextSibling.style.display = 'flex';
  };

  return (
    <motion.div 
      className={styles.dashboard}
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      <div className={styles.chartsGrid}>
        <motion.div variants={itemVariants}>
          <LiquidGlassCard className={styles.chartCard}>
            <h3 className={styles.cardTitle}>Training Loss</h3>
            <div className={styles.imageContainer}>
              <img 
                src="/proof/loss_chart.png" 
                alt="Loss Chart" 
                className={styles.chartImage}
                onError={handleImageError}
              />
              <div className={styles.placeholder} style={{ display: 'none' }}>
                <p>Train the model first to generate charts.</p>
              </div>
            </div>
          </LiquidGlassCard>
        </motion.div>
        
        <motion.div variants={itemVariants}>
          <LiquidGlassCard className={styles.chartCard}>
            <h3 className={styles.cardTitle}>Confusion Matrix</h3>
            <div className={styles.imageContainer}>
              <img 
                src="/proof/confusion_matrix.png" 
                alt="Confusion Matrix" 
                className={styles.chartImage}
                onError={handleImageError}
              />
              <div className={styles.placeholder} style={{ display: 'none' }}>
                <p>Train the model first to generate charts.</p>
              </div>
            </div>
          </LiquidGlassCard>
        </motion.div>
      </div>

      <motion.div variants={itemVariants}>
        <TerminalReplay />
      </motion.div>

      <motion.div variants={itemVariants} className={styles.metricsContainer}>
        <LiquidGlassCard>
          <h3 className={styles.cardTitle}>Overall Performance Metrics</h3>
          <div className={styles.metricsGrid}>
            <div className={styles.metricItem}>
              <span className={styles.metricLabel}>Precision</span>
              <span className={styles.metricValue}>
                {loadingMetrics ? '...' : metrics ? ((metrics.metrics?.precision ?? 0) * 100).toFixed(2) + '%' : '--'}
              </span>
            </div>
            <div className={styles.metricItem}>
              <span className={styles.metricLabel}>Recall</span>
              <span className={styles.metricValue}>
                {loadingMetrics ? '...' : metrics ? ((metrics.metrics?.recall ?? 0) * 100).toFixed(2) + '%' : '--'}
              </span>
            </div>
            <div className={styles.metricItem}>
              <span className={styles.metricLabel}>F1 Score</span>
              <span className={styles.metricValue}>
                {loadingMetrics ? '...' : metrics ? ((metrics.metrics?.f1 ?? 0) * 100).toFixed(2) + '%' : '--'}
              </span>
            </div>
          </div>
        </LiquidGlassCard>
      </motion.div>
    </motion.div>
  );
};

export default ProofDashboard;
