import { analyzeBiomedical } from '../api';

export interface AnalysisInput { genes?:string[]; query?:string; suggestedDiseases?:string[]; paperSummary?:string; }
export async function analyzeGeneDisease(input:AnalysisInput){
  return analyzeBiomedical(input);
}
