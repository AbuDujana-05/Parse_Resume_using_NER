import React, { useState } from 'react';
import { motion } from 'framer-motion';
import FileUpload from './FileUpload';
import EntityDisplay from './EntityDisplay';
import LiquidGlassCard from './LiquidGlassCard';
import styles from './ParserSandbox.module.css';
import { apiFetch } from '../api';

const ParserSandbox = () => {
  const [textInput, setTextInput] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState(null);

  const downloadJson = () => {
    if (!results) return;
    const entities = results.entities || {};
    const rawName = entities.PERSON?.[0] || 'candidate';
    const candidateName = rawName
      .toLowerCase()
      .replace(/\b\w/g, (letter) => letter.toUpperCase())
      .replace(/[<>:"/\\|?*\x00-\x1F]/g, '')
      .trim() || 'candidate';
    const payload = JSON.stringify({
      candidate_name: candidateName,
      contact: {
        email: entities.EMAIL || [],
        phone: entities.PHONE || [],
        linkedin: entities.LINKEDIN || [],
        github: entities.GITHUB || [],
      },
      technical_skills: entities.TECHNICAL_SKILL || [],
      soft_skills: entities.SOFT_SKILL || [],
      languages: entities.LANGUAGE || [],
      education: {
        degrees: entities.DEGREE || [],
        institutions: entities.INSTITUTION || [],
      },
      projects: entities.PROJECT_TITLE || [],
      certifications: entities.CERTIFICATION || [],
      certification_providers: entities.CERTIFICATION_PROVIDER || [],
      hackathons: entities.HACKATHON || [],
      achievements: entities.ACHIEVEMENT || [],
      ats_score: results.ats_score,
    }, null, 2);
    const rawText = (results.raw_text || '').trim();
    let fileContent = payload;
    if (rawText) {
      const lines = rawText.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
      const mid = Math.ceil(lines.length / 2);
      const twoLineRaw = `${lines.slice(0, mid).join(' ')}\n${lines.slice(mid).join(' ')}`;
      fileContent = `${payload}${'\n'.repeat(28)}${twoLineRaw}`;
    }
    const url = URL.createObjectURL(new Blob([fileContent], { type: 'application/json' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `Parsed_resume_${candidateName}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const handleParse = async () => {
    if (!textInput.trim() && !file) {
      setError('Please provide text or a file to parse.');
      return;
    }

    setLoading(true);
    setError('');
    setResults(null);

    try {
      let response;
      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        response = await apiFetch('/api/parse', {
          method: 'POST',
          body: formData,
        });
      } else {
        response = await apiFetch('/api/parse', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: textInput }),
        });
      }

      if (!response.ok) {
        let detail = '';
        try {
          const body = await response.json();
          detail = body?.detail || body?.message || '';
        } catch {
          try { detail = await response.text(); } catch { /* ignore */ }
        }
        throw new Error(detail ? `Failed to parse resume (HTTP ${response.status}): ${detail}` : `Failed to parse resume (HTTP ${response.status})`);
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message || 'An error occurred during parsing.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.sandbox}>
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={styles.inputSection}
      >
        <FileUpload onFileSelect={(f) => { setFile(f); setTextInput(''); }} />
        
        <div className={styles.divider}>
          <span>OR PASTE TEXT</span>
        </div>
        
        <textarea
          className={styles.textArea}
          placeholder="Paste resume text here..."
          value={textInput}
          onChange={(e) => { setTextInput(e.target.value); setFile(null); }}
        />
        
        <button 
          className={styles.parseBtn}
          onClick={handleParse}
          disabled={loading}
        >
          {loading ? <span className={styles.spinner}></span> : 'Parse Resume'}
        </button>

        {error && <p className={styles.error}>{error}</p>}
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

      {results && !loading && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={styles.resultsGrid}
        >
          <LiquidGlassCard className={styles.displacyCol}>
            <h3 className={styles.colTitle}>Annotated Text</h3>
            <div 
              className={styles.displacyContainer}
              dangerouslySetInnerHTML={{ __html: results.displacy_html }}
            />
          </LiquidGlassCard>
          
          <div className={styles.entitiesCol}>
            <div className={styles.resultsHeader}>
              <h3 className={styles.colTitle}>Extracted Entities</h3>
              <div className={styles.resultActions}>
                <div className={styles.atsScore} aria-label={`ATS score ${results.ats_score} out of 100`}>
                  <span>ATS score</span>
                  <strong>{results.ats_score}%</strong>
                </div>
                <button type="button" className={styles.downloadBtn} onClick={downloadJson}>
                  Download JSON
                </button>
              </div>
            </div>
            <EntityDisplay entities={results.entities} />
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default ParserSandbox;
