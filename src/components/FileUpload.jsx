import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import styles from './FileUpload.module.css';

const FileUpload = ({ onFileSelect }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = (files) => {
    const file = files[0];
    const validTypes = ['.pdf', '.docx', '.pptx', '.png', '.jpg', '.jpeg'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    const maxBytes = import.meta.env.PROD ? 4 * 1024 * 1024 : 20 * 1024 * 1024;
    if (file.size > maxBytes) {
      alert(`File is too large for this deployment. Maximum supported size is ${maxBytes / (1024 * 1024)} MB.`);
      return;
    }

    if (validTypes.includes(fileExtension)) {
      setSelectedFile(file);
      if (onFileSelect) onFileSelect(file);
    } else {
      alert('Invalid file type. Please upload a PDF, DOCX, PPTX, or Image.');
    }
  };

  const handleClick = () => {
    fileInputRef.current.click();
  };

  return (
    <motion.div 
      className={`${styles.uploadZone} ${isDragging ? styles.dragging : ''}`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={handleClick}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        className={styles.fileInput}
        accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg"
      />
      <div className={styles.content}>
        <span className={styles.icon}>📄</span>
        {selectedFile ? (
          <p className={styles.fileName}>Selected: {selectedFile.name}</p>
        ) : (
          <div>
            <p className={styles.text}>Drag & Drop your resume here</p>
            <p className={styles.subtext}>or click to browse (.pdf, .docx, .png, .jpg)</p>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default FileUpload;
