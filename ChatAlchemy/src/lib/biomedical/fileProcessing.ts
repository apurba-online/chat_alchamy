import { uploadBiomedicalDocument } from '../api';

export interface ProcessedFile { content: string; genes: string[]; suggestedDiseases: string[]; summary: string; }

export async function processFile(file: File): Promise<ProcessedFile> {
  if (!(/\.pdf$/i.test(file.name) || /\.txt$/i.test(file.name) || file.type === 'application/pdf' || file.type.startsWith('text/'))) throw new Error('Biomedical Analysis accepts PDF or TXT documents.');
  const extracted = await uploadBiomedicalDocument(file);
  return { content: '', genes: extracted.genes, suggestedDiseases: extracted.suggested_diseases, summary: extracted.summary };
}
