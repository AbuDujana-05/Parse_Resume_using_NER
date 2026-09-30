import React, { useState } from 'react';
import { motion } from 'framer-motion';
import LiquidGlassCard from './LiquidGlassCard';
import EntityDisplay from './EntityDisplay';
import styles from './DomainGallery.module.css';
import { apiFetch } from '../api';

const DOMAINS = [
  {
    id: 1,
    icon: '💻',
    name: 'Software Engineer',
    text: "John Smith is a Senior Software Enginner with 8 years of experience in full-stack development. He specializes in Python, JavaScript, React, Node.js, and AWS cloud services. John holds a Bachlors of Science in Computer Science from Stanford University, located in Palo Alto, California. He is certified in AWS Solutions Architect and Google Cloud Professional. His notable projects include CloudScale Analytics Platform and MicroserviceHub Framework. Contact: john.smith@techmail.com, Phone: (555) 234-5678. Domain: Software Engineering."
  },
  {
    id: 2,
    icon: '🏥',
    name: 'Cardiologist',
    text: "Dr. Sarah Jhonson is a board-certified Cardiologist with 15 years of experience in cardiovascular medicine. She specializes in Patient Care, EMR Systems, Echocardiography, Cardiac Catheterization, and HIPAA Compliance. Dr. Johnson earned her Doctor of Medicine degree from Johns Hopkins University in Baltimore, Maryland. She holds certifications in Advanced Cardiac Life Support and Board Certified Cardiologist. Key projects: Cardiac Telehealth Initiative and Heart Failure Prediction Model. Email: s.johnson@hospital.org, Phone: 555.789.0123. Domain: Healthcare."
  },
  {
    id: 3,
    icon: '⚖️',
    name: 'Corporate Counsel',
    text: "Michael Chen, Esq. is a seasoned Corporate Counsel with 12 years of experience in corporate law. His expertise includes Contract Law, Mergers and Acquisitions, Due Diligence, Compliance, and Intellectual Proprty. Michael graduated with a Juris Doctor from Harvard Law School in Cambridge, Massachusetts. He is certified as a Bar Certified Attorney and Certified Compliance Professional. Notable cases include TechCorp Merger Advisory and Global IP Portfolio Restructuring. Contact: m.chen@lawfirm.com | (555) 345-6789. Domain: Legal."
  },
  {
    id: 4,
    icon: '🎨',
    name: '3D Animator',
    text: "Luna Rodriguez is a talented 3D Animator and Visual Artist with 6 years of experience in digital media production. Her skills include Blender, Maya, ZBrush, After Effects, and Motion Graphics. Luna holds a Bachelor of Fine Arts from Rhode Island School of Design in Providence, Rhode Island. Certified in Autodesk Maya Professional and Adobe Certified Expert. Projects: Nebula Dreams Animation Series and Augmented Reality Art Installation. Email: luna.art@creative.io, Phone: +1-555-456-7890. Domain: Arts and Design."
  },
  {
    id: 5,
    icon: '📊',
    name: 'Financial Analyst',
    text: "Robert Williams is a Senior Financial Analist and Portfolio Manager with 10 years of experience in investment banking. He is skilled in Financial Modeling, Risk Analysis, Bloomberg Terminal, Excel VBA, and Quantitative Analysis. Robert holds a Masters of Business Administration from Wharton School of Business in Philadelphia, Pennsylvania. Certifications: CFA Charterholder and Financial Risk Manager. Key projects: Algorithmic Trading Platform and Cross-Border M&A Valuation Framework. Email: r.williams@finance.com, Phone: (555) 567-8901. Domain: Finance."
  },
  {
    id: 6,
    icon: '📢',
    name: 'Marketing Manager',
    text: "Emily Nakamura is a dynamic Digital Marketing Manager with 7 years of experience in growth marketing. Her skillset includes SEO, Google Analytics, Content Strategy, A/B Testing, and Facebook Ads management. Emily earned a Bachelors of Arts in Marketing from University of Michigan in Ann Arbor, Michigan. She is a Google Analytics Certified Professional and HubSpot Inbound Marketing certified. Projects include Viral Brand Awareness Campaign and E-commerce Conversion Optimization Engine. Contact: emily.n@marketing.co, (555) 678-9012. Domain: Marketing."
  },
  {
    id: 7,
    icon: '👥',
    name: 'HR Business Partner',
    text: "David Okafor is an experienced HR Business Partner and Talent Acquisition Specialist with 9 years of experience in human resources management. His competencies include Talent Acquisition, Employee Relations, Workday, Performance Management, and Diversity and Inclusion. David holds a Masters of Science in Human Resources from Cornell University in Ithaca, New York. Certified as a SHRM Senior Certified Professional and Certified Compensation Professional. Projects: Global Talent Pipeline System and AI-Driven Employee Engagement Platform. Email: d.okafor@hrmail.com, Phone: 5556789012. Domain: Human Resources."
  },
  {
    id: 8,
    icon: '🏗️',
    name: 'Civil Engineer',
    text: "Priya Sharma is a licensed Civil Enginner and Structural Engineer with 11 years of experience in infrastructure development. She is proficient in AutoCAD, SolidWorks, MATLAB, Structural Analysis, and Project Management. Priya earned her Master of Science in Civil Engineering from MIT in Cambridge, Massachusetts. Certifications include Professional Engineer License and LEED Accredited Professional. Major projects: Metropolitan Bridge Retrofit Project and Seismic Resilience Assessment Framework. Email: p.sharma@engineering.net, Phone: (555) 890-1234. Domain: Engineering."
  },
  {
    id: 9,
    icon: '🏨',
    name: 'Hotel Manager',
    text: "Carlos Mendez is an accomplished Hotel Manager and Executive Chef with 13 years of experience in luxury hospitality management. His expertise spans Guest Relations, Revenue Management, Opera PMS, Food Safety, and Banquet Management. Carlos holds a Bachelors of Science in Hospitality Management from Cornell University School of Hotel Administration in Ithaca, New York. He is ServSafe Manager Certified and Certified Hotel Administrator. Projects: Five-Star Guest Experience Redesign and Farm-to-Table Restaurant Concept Launch. Email: carlos.m@luxuryhotels.com, Phone: +1-555-901-2345. Domain: Hospitality."
  },
  {
    id: 10,
    icon: '🔧',
    name: 'Master Electrician',
    text: "James O'Brien is a Master Electrican and HVAC Technician with 20 years of experience in commercial and residential electrical systems. His skills include Electrical Wiring, HVAC Installation, Blueprint Reading, PLC Programming, and OSHA Safety compliance. James completed his Journeyman Electrician Certification at Milwaukee Area Technical College in Milwaukee, Wisconsin. He holds a Master Electrician License and EPA Section 608 Certification. Projects: Smart Building Automation Retrofit and Industrial Power Distribution Upgrade. Contact: j.obrien@trades.net, (555) 012-3456. Domain: Skilled Trades."
  }
];

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, scale: 0.9 },
  show: { opacity: 1, scale: 1 }
};

const DomainGallery = () => {
  const [activeDomain, setActiveDomain] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  const handleDomainSelect = async (domain) => {
    setActiveDomain(domain.id);
    setLoading(true);
    setResults(null);
    setError('');

    try {
      const response = await apiFetch('/api/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: domain.text }),
      });

      if (!response.ok) {
        let detail = '';
        try {
          const body = await response.json();
          detail = body?.detail || body?.message || '';
        } catch { /* ignore */ }
        throw new Error(detail ? `Failed to parse sample text (HTTP ${response.status}): ${detail}` : `Failed to parse sample text (HTTP ${response.status})`);
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.gallery}>
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className={styles.carouselContainer}
      >
        <div className={styles.carousel}>
          {DOMAINS.map((domain) => (
            <motion.button
              key={domain.id}
              variants={itemVariants}
              className={`${styles.domainBtn} ${activeDomain === domain.id ? styles.active : ''}`}
              onClick={() => handleDomainSelect(domain)}
            >
              <span className={styles.icon}>{domain.icon}</span>
              <span className={styles.name}>{domain.name}</span>
            </motion.button>
          ))}
        </div>
      </motion.div>

      {loading && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className={styles.loadingState}
        >
          <div className={styles.skeletonText}></div>
          <div className={styles.skeletonText}></div>
          <div className={styles.skeletonText} style={{ width: '60%' }}></div>
        </motion.div>
      )}

      {error && <p className={styles.error}>{error}</p>}

      {results && !loading && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={styles.resultsGrid}
        >
          <LiquidGlassCard className={styles.displacyCol}>
            <h3 className={styles.colTitle}>Sample Text</h3>
            <div className={styles.originalText}>
              {DOMAINS.find(d => d.id === activeDomain)?.text}
            </div>
            <h3 className={styles.colTitle} style={{ marginTop: '20px' }}>Annotated Result</h3>
            <div 
              className={styles.displacyContainer}
              dangerouslySetInnerHTML={{ __html: results.displacy_html }}
            />
          </LiquidGlassCard>
          
          <div className={styles.entitiesCol}>
            <h3 className={styles.colTitle}>Extracted Entities</h3>
            <EntityDisplay entities={results.entities} />
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default DomainGallery;
