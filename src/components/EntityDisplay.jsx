import React from 'react';
import { motion } from 'framer-motion';
import LiquidGlassCard from './LiquidGlassCard';
import styles from './EntityDisplay.module.css';

const ENTITY_COLORS = {
  PERSON: '#FF6B6B',
  EMAIL: '#4ECDC4',
  PHONE: '#45B7D1',
  LINKEDIN: '#0A66C2',
  GITHUB: '#B8C0CC',
  DESIGNATION: '#96CEB4',
  YEARS_EXPERIENCE: '#FFEAA7',
  TECHNICAL_SKILL: '#DDA0DD',
  SOFT_SKILL: '#C39BD3',
  LANGUAGE: '#5DADE2',
  DEGREE: '#98D8C8',
  INSTITUTION: '#F7DC6F',
  LOCATION: '#82E0AA',
  CERTIFICATION: '#F0B27A',
  CERTIFICATION_PROVIDER: '#F5B7B1',
  HACKATHON: '#FF9F43',
  ACHIEVEMENT: '#F8C471',
  DOMAIN: '#AED6F1',
  PROJECT_TITLE: '#D7BDE2'
};

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 }
};

const EntityDisplay = ({ entities }) => {
  if (!entities || Object.keys(entities).length === 0) {
    return (
      <div className={styles.emptyState}>
        <p>No entities extracted yet.</p>
      </div>
    );
  }

  return (
    <motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className={styles.container}
    >
      {Object.entries(entities).map(([type, values]) => (
        <motion.div key={type} variants={item} className={styles.entityGroup}>
          <LiquidGlassCard className={styles.card} animate={false}>
            <div className={styles.header}>
              <span className={styles.label}>{type.replace('_', ' ')}</span>
              <div 
                className={styles.colorIndicator} 
                style={{ backgroundColor: ENTITY_COLORS[type] || '#ccc' }} 
              />
            </div>
            <div className={styles.values}>
              {values.map((val, idx) => (
                <span 
                  key={idx} 
                  className={styles.chip}
                  style={{ 
                    backgroundColor: `${ENTITY_COLORS[type]}33` || 'rgba(204,204,204,0.2)',
                    borderColor: ENTITY_COLORS[type] || '#ccc',
                    color: ENTITY_COLORS[type] || '#fff'
                  }}
                >
                  {val}
                </span>
              ))}
            </div>
          </LiquidGlassCard>
        </motion.div>
      ))}
    </motion.div>
  );
};

export default EntityDisplay;
