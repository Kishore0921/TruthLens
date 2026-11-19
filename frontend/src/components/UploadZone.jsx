import React, { useRef, useState } from 'react';
import { UploadCloud, File, AlertCircle } from 'lucide-react';

export default function UploadZone({ onFilesSelected, isUploading, uploadProgress }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFilesSelected(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onFilesSelected(Array.from(e.target.files));
      e.target.value = ''; // Reset input
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
        isDragOver
          ? 'border-cyan-400 bg-cyan-950/20'
          : 'border-slate-700 bg-slate-900/60 hover:border-slate-600 hover:bg-slate-900'
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFileChange}
        accept=".jpg,.jpeg,.png,.webp,.mp4,.mov,.avi,.mkv,.wav,.mp3,.m4a,.flac,.aac,.txt,.pdf,.docx"
      />

      <div className="flex flex-col items-center justify-center space-y-3">
        <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-cyan-400 border border-slate-700">
          <UploadCloud className="w-6 h-6" />
        </div>
        <div>
          <p className="text-sm font-medium text-slate-200">
            Click to upload or drag & drop forensic evidence
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Multimodal formats: Images (JPG, PNG, WEBP), Videos (MP4, MOV), Audio (WAV, MP3, FLAC), Documents (TXT, PDF, DOCX)
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-1.5 pt-2 text-[11px] font-mono text-slate-400">
          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">Max 100MB</span>
          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">SHA-256 Verified</span>
          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">Original Preserved</span>
        </div>

        {isUploading && (
          <div className="w-full max-w-md mt-4">
            <div className="flex justify-between text-xs font-mono text-cyan-400 mb-1">
              <span>Uploading & Hashing Evidence...</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div
                className="bg-cyan-500 h-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
