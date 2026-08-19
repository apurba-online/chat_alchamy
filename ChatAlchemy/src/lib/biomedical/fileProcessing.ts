import * as pdfjsLib from 'pdfjs-dist';
import pdfWorkerRaw from 'pdfjs-dist/build/pdf.worker.min.mjs?raw';
import { extractBiomedical } from '../api';

if(typeof window!=='undefined'){
  const blob=new Blob([pdfWorkerRaw],{type:'application/javascript'});
  pdfjsLib.GlobalWorkerOptions.workerSrc=URL.createObjectURL(blob);
}

export interface ProcessedFile { content:string; genes:string[]; suggestedDiseases:string[]; summary:string; }

async function readFile(file:File):Promise<string>{
  if(file.type==='application/pdf'||file.name.toLowerCase().endsWith('.pdf')){
    const pdf=await pdfjsLib.getDocument({data:await file.arrayBuffer()}).promise;
    let text='';
    for(let i=1;i<=pdf.numPages;i++){const page=await pdf.getPage(i);const content=await page.getTextContent();text+=(content.items as any[]).map(x=>x.str).join(' ')+'\n';}
    return text;
  }
  return file.text();
}

export async function processFile(file:File):Promise<ProcessedFile>{
  if(!(/\.pdf$/i.test(file.name)||/\.txt$/i.test(file.name)||file.type==='application/pdf'||file.type.startsWith('text/'))) throw new Error('Biomedical Analysis accepts PDF or TXT documents.');
  const content=(await readFile(file)).trim();
  if(!content)throw new Error(`No readable text found in ${file.name}`);
  const extracted=await extractBiomedical(content,file.name);
  return {content,genes:extracted.genes,suggestedDiseases:extracted.suggested_diseases,summary:extracted.summary};
}
