import React from 'react';
import { motion } from 'framer-motion';
import styles from './LiquidGlassCard.module.css';

const LiquidGlassCard = ({ children, className = '', onClick, hoverable = false, style, animate = true }) => {
  const CardContent = (
    <div
      className={`${styles.card} ${hoverable ? styles.hoverable : ''} ${className}`}
      onClick={onClick}
      style={style}
    >
      {children}
    </div>
  );

  if (animate) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className={styles.motionWrapper}
      >
        {CardContent}
      </motion.div>
    );
  }

  return CardContent;
};

export default LiquidGlassCard;
