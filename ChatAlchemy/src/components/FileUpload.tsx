import React, { useCallback, useState } from 'react';
import { Upload, Loader2, Plus } from 'lucide-react';
import { processFile } from '../lib/knowledge';

interface FileUploadProps {
  onUploadComplete: (filename: string) => void;
  onError: (error: string) => void;
}

export function FileUpload({ onUploadComplete, onError }: FileUploadProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [showUpload, setShowUpload] = useState(false);

  const handleFileProcess = async (file: File) => {
    const fileExtension = file.name.split('.').pop()?.toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(fileExtension || '')) {
      onError('Only CSV and Excel files (xlsx, xls) are supported');
      return;
    }

    setIsLoading(true);
    try {
      const data = await processFile(file);
      if (data.length === 0) {
        throw new Error('No valid data found in file');
      }
      onUploadComplete(`${file.name} (${data.length} records)`);
      setShowUpload(false);
    } catch (error: any) {
      onError(error.message || `Error processing ${file.name}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = Array.from(e.dataTransfer.files);
    for (const file of files) {
      await handleFileProcess(file);
    }
  }, [onUploadComplete, onError]);

  const handleFileChange = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      for (const file of Array.from(files)) {
        await handleFileProcess(file);
      }
    }
    event.target.value = '';
  }, [onUploadComplete, onError]);

  if (!showUpload) {
    return (
      <button
        onClick={() => setShowUpload(true)}
        className="flex items-center gap-2 text-sm text-purple-600 hover:text-purple-700 font-medium"
      >
        <Plus className="h-4 w-4" />
        Upload Data
      </button>
    );
  }

  return (
    <div className="relative">
      <div
        className={`relative border-2 ${
          dragActive ? 'border-purple-500 bg-purple-50' : 'border-dashed border-gray-300'
        } rounded-lg p-4 text-center transition-colors`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileChange}
          className="hidden"
          id="file-upload"
          multiple
        />
        <label
          htmlFor="file-upload"
          className="cursor-pointer block"
        >
          <div className="flex items-center justify-center gap-2">
            {isLoading ? (
              <Loader2 className="h-5 w-5 text-purple-500 animate-spin" />
            ) : (
              <Upload className="h-5 w-5 text-gray-400" />
            )}
            <span className="text-sm text-gray-600">
              {isLoading ? 'Processing...' : 'Drop CSV/Excel or click'}
            </span>
          </div>
        </label>
      </div>
      <button
        onClick={() => setShowUpload(false)}
        className="absolute -top-2 -right-2 p-1 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}