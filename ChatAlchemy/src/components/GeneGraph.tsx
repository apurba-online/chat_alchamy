import { useEffect, useRef, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';
import { Download } from 'lucide-react';
import { saveAs } from 'file-saver';
import { analyzeBiomedical } from '../lib/api';
cytoscape.use(cola as any);
export function GeneGraph({geneName}:{ensemblId:string;geneName:string}){
  const [elements,setElements]=useState<any[]>([]);const [error,setError]=useState<string|null>(null);const [loading,setLoading]=useState(true);const cyRef=useRef<any>(null);
  useEffect(()=>{setLoading(true);setError(null);analyzeBiomedical({genes:[geneName]}).then(r=>setElements(r.networkData||[])).catch(e=>setError(e instanceof Error?e.message:'Failed to load graph')).finally(()=>setLoading(false))},[geneName]);
  if(loading)return <div className="flex h-[520px] items-center justify-center rounded-lg bg-gray-50 dark:bg-gray-900"><div className="h-8 w-8 animate-spin rounded-full border-b-2 border-purple-600"/></div>;
  if(error)return <div className="flex h-[520px] items-center justify-center text-red-500">{error}</div>;
  return <div className="space-y-2"><div className="flex justify-end"><button onClick={()=>{const blob=cyRef.current?.png({full:true,scale:2,output:'blob'});if(blob)saveAs(blob,`${geneName}-network.png`)}} className="p-2 text-gray-500 hover:text-purple-600" title="Download PNG"><Download className="h-5 w-5"/></button></div><div className="h-[520px] overflow-hidden rounded-lg border dark:border-gray-700"><CytoscapeComponent elements={elements} style={{width:'100%',height:'100%'}} cy={(cy:any)=>{cyRef.current=cy}} layout={{name:'cola',nodeSpacing:100,edgeLength:140,animate:true,maxSimulationTime:1500} as any} stylesheet={[{selector:'node',style:{'background-color':'#6366f1','label':'data(label)','font-size':'11px','text-wrap':'wrap','text-max-width':'90px','color':'#111827'}},{selector:'node[type="disease"]',style:{'background-color':'#e11d48','shape':'diamond'}},{selector:'node[type="drug"]',style:{'background-color':'#059669','shape':'round-rectangle'}},{selector:'edge',style:{'width':'data(weight)','line-color':'#9333ea','target-arrow-color':'#9333ea','target-arrow-shape':'triangle','curve-style':'bezier','label':'data(label)','font-size':'9px'}}] as any}/></div></div>;
}
