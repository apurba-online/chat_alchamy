import { Loader2 } from 'lucide-react';
export function LoadingState(){return <div className="flex items-center justify-center rounded-lg bg-white p-8 dark:bg-gray-800"><div className="flex flex-col items-center gap-4"><Loader2 className="h-8 w-8 animate-spin text-purple-600"/><p className="text-gray-600 dark:text-gray-300">Processing biomedical data...</p></div></div>}
