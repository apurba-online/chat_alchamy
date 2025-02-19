import React, { useCallback } from 'react';
import { Upload } from 'lucide-react';
import { loadDataset } from '../lib/knowledge';

interface FileUploadProps {
  onUploadComplete: () => void;
}

export function FileUpload({ onUploadComplete }: FileUploadProps) {
  const handleFileChange = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      await loadDataset(file);
      onUploadComplete();
    } catch (error) {
      console.error('Error loading dataset:', error);
      alert('Error loading dataset. Please check the file format and try again.');
    }
  }, [onUploadComplete]);

  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
      <label className="cursor-pointer block">
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileChange}
          className="hidden"
        />
        <div className="flex flex-col items-center gap-2">
          <Upload className="h-8 w-8 text-gray-400" />
          <span className="text-sm text-gray-600">
            Upload your dataset (CSV or Excel)
          </span>
          <span className="text-xs text-gray-500">
            Drag and drop or click to select
          </span>
        </div>
      </label>
    </div>
  );
}