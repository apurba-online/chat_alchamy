import { useState } from 'react';
import { Download, ExternalLink } from 'lucide-react';
import { DiseaseModal } from './DiseaseModal';
import { Modal } from './Modal';
import { downloadBlob, exportTableXlsx } from '../lib/api';

interface Props {
  headers: string[];
  rows: unknown[][];
  caption?: string;
}

const DISEASE_ID_SPLIT_RE = /\[((?:EFO|MONDO|OTAR|Orphanet|HP|NCIT|DOID)_[A-Za-z0-9]+)\]/gi;

export function DataTable({ headers, rows, caption }: Props) {
  const [all, setAll] = useState(false);
  const [disease, setDisease] = useState<string | null>(null);
  const [gene, setGene] = useState<{ id: string; name: string } | null>(null);
  const [exporting, setExporting] = useState(false);

  const displayed = all ? rows : rows.slice(0, 10);
  const ensemblIndex = headers.findIndex(header => /ensembl/i.test(header));
  const geneIndex = headers.findIndex(header => /gene symbol|^gene$/i.test(header));

  const exportExcel = async () => {
    setExporting(true);
    try {
      downloadBlob(await exportTableXlsx({ headers, rows, caption }), 'chatalchemy-results.xlsx');
    } finally {
      setExporting(false);
    }
  };

  const render = (cell: unknown, row: unknown[], index: number) => {
    const value = String(cell ?? '');

    if (index === geneIndex && ensemblIndex >= 0) {
      const id = String(row[ensemblIndex] ?? '');
      return (
        <button
          className="font-medium text-blue-600 hover:underline dark:text-blue-400"
          onClick={() => id && setGene({ id, name: value })}
        >
          {value.toUpperCase()}
        </button>
      );
    }

    const parts = value.split(DISEASE_ID_SPLIT_RE);
    if (parts.length > 1) {
      return (
        <span>
          {parts.map((part, partIndex) =>
            partIndex % 2 === 1 ? (
              <button
                key={`${part}-${partIndex}`}
                className="text-purple-600 hover:underline dark:text-purple-400"
                onClick={() => setDisease(part)}
                title={`Open disease information for ${part}`}
              >
                [{part}]
              </button>
            ) : (
              <span key={`text-${partIndex}`}>{part}</span>
            ),
          )}
        </span>
      );
    }

    if (/^ENSG\d+$/i.test(value)) {
      return (
        <a
          className="inline-flex items-center gap-1 text-purple-600 hover:underline dark:text-purple-400"
          href={`https://ensembl.org/Homo_sapiens/Gene/Summary?g=${encodeURIComponent(value)}`}
          target="_blank"
          rel="noreferrer"
        >
          {value}
          <ExternalLink className="h-3 w-3" />
        </a>
      );
    }

    return value;
  };

  return (
    <>
      <div className="overflow-x-auto rounded-xl border border-gray-100 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">{caption || 'Results'}</h3>
          <button
            onClick={() => void exportExcel()}
            disabled={exporting}
            title="Export to Excel"
            className="p-2 text-gray-500 hover:text-purple-600 disabled:opacity-40"
          >
            <Download className="h-5 w-5" />
          </button>
        </div>
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b dark:border-gray-700">
              {headers.map(header => (
                <th
                  key={header}
                  className="whitespace-nowrap p-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayed.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className="border-b last:border-0 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/40"
              >
                {row.map((cell, cellIndex) => (
                  <td
                    key={cellIndex}
                    className="max-w-[420px] p-3 align-top text-gray-700 dark:text-gray-300"
                  >
                    {render(cell, row, cellIndex)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length > 10 && (
          <div className="mt-3 text-center">
            <button
              onClick={() => setAll(!all)}
              className="text-sm text-purple-600 hover:underline dark:text-purple-400"
            >
              {all ? 'Show Less' : `Show All (${rows.length} rows)`}
            </button>
          </div>
        )}
      </div>
      <DiseaseModal isOpen={!!disease} onClose={() => setDisease(null)} efoId={disease || ''} />
      <Modal
        isOpen={!!gene}
        onClose={() => setGene(null)}
        ensemblId={gene?.id}
        geneName={gene?.name}
      />
    </>
  );
}
