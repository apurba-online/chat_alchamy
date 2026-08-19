import { X } from 'lucide-react';
import { GeneImageViewer } from './GeneImageViewer';
export function Modal({isOpen,onClose,ensemblId,geneName}:{isOpen:boolean;onClose:()=>void;ensemblId?:string;geneName?:string}){
  if(!isOpen)return null;
  return <div className="fixed inset-0 z-50 flex items-center justify-center"><div className="fixed inset-0 bg-black/50" onClick={onClose}/><div className="relative max-h-[90vh] w-[92vw] max-w-6xl overflow-y-auto rounded-xl bg-white p-4 shadow-xl dark:bg-gray-800"><button onClick={onClose} className="absolute right-3 top-3 z-10 rounded-full p-2 hover:bg-gray-100 dark:hover:bg-gray-700"><X className="h-5 w-5"/></button>{ensemblId&&geneName?<GeneImageViewer ensemblId={ensemblId} geneName={geneName}/>:<p className="p-8">No gene selected.</p>}</div></div>;
}
