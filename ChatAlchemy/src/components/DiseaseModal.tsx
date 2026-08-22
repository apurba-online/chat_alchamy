import { useEffect, useState } from 'react';
import { ExternalLink, Loader2, X } from 'lucide-react';
import {
  getCompoundDetails,
  getDiseaseDetails,
  type CompoundDetails,
  type DiseaseDetailDrug,
  type DiseaseDetails,
} from '../lib/api';

export function DiseaseModal({
  isOpen,
  onClose,
  efoId,
}: {
  isOpen: boolean;
  onClose: () => void;
  efoId: string;
}) {
  const [info, setInfo] = useState<DiseaseDetails | null>(null);
  const [drug, setDrug] = useState<DiseaseDetailDrug | null>(null);
  const [chem, setChem] = useState<CompoundDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [chemLoading, setChemLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chemError, setChemError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !efoId) return;
    let cancelled = false;
    setLoading(true);
    setInfo(null);
    setDrug(null);
    setChem(null);
    setError(null);
    setChemError(null);
    void getDiseaseDetails(efoId)
      .then(result => {
        if (!cancelled) setInfo(result);
      })
      .catch(err => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Could not load the Open Targets disease record.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen, efoId]);

  useEffect(() => {
    if (!drug) return;
    let cancelled = false;
    setChem(null);
    setChemError(null);
    setChemLoading(true);
    void getCompoundDetails(drug.name)
      .then(result => {
        if (!cancelled) setChem(result);
      })
      .catch(err => {
        if (!cancelled) {
          setChemError(err instanceof Error ? err.message : 'Could not load the PubChem compound record.');
        }
      })
      .finally(() => {
        if (!cancelled) setChemLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [drug]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative max-h-[90vh] w-[92vw] max-w-5xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
        <button
          onClick={onClose}
          className="absolute right-3 top-3 rounded-full p-2 hover:bg-gray-100 dark:hover:bg-gray-700"
          aria-label="Close disease information"
        >
          <X className="h-5 w-5" />
        </button>
        <h3 className="mb-4 text-xl font-semibold dark:text-white">Disease Information</h3>

        {loading ? (
          <div className="flex min-h-48 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
            {error}
          </div>
        ) : info ? (
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-white">{info.name}</h4>
              <p className="mb-4 text-xs text-gray-500">{info.id || efoId}</p>
              <div className="mb-2 flex items-center justify-between gap-3">
                <h5 className="font-medium text-gray-900 dark:text-gray-100">Clinical drug candidates</h5>
                <span className="text-xs text-gray-400">Open Targets</span>
              </div>
              {info.drugs.length ? (
                <div className="space-y-2">
                  {info.drugs.map(candidate => (
                    <button
                      key={candidate.id || candidate.name}
                      onClick={() => setDrug(candidate)}
                      className={`flex w-full items-center justify-between gap-3 rounded-lg border p-2.5 text-left transition ${
                        drug?.name === candidate.name
                          ? 'border-purple-500 bg-purple-50/60 dark:bg-purple-950/20'
                          : 'border-gray-200 hover:border-purple-300 dark:border-gray-700'
                      }`}
                    >
                      <span className="font-medium text-gray-800 dark:text-gray-100">{candidate.name}</span>
                      <span className="shrink-0 text-xs text-purple-600 dark:text-purple-400">
                        {candidate.max_clinical_stage || 'stage unavailable'}
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg bg-gray-50 p-4 text-sm text-gray-500 dark:bg-gray-900">
                  No current clinical drug candidates were returned for this disease by Open Targets.
                </div>
              )}
              <a
                href={info.source_url || `https://platform.opentargets.org/disease/${encodeURIComponent(efoId)}`}
                target="_blank"
                rel="noreferrer"
                className="mt-4 inline-flex items-center gap-1 text-sm text-purple-600 hover:underline dark:text-purple-400"
              >
                Open Targets <ExternalLink className="h-3 w-3" />
              </a>
            </div>

            <div>
              {drug ? (
                <>
                  <div className="mb-2 flex items-baseline justify-between gap-3">
                    <h5 className="font-medium text-gray-900 dark:text-gray-100">{drug.name}</h5>
                    {drug.max_clinical_stage && (
                      <span className="text-xs text-gray-400">{drug.max_clinical_stage}</span>
                    )}
                  </div>
                  <img
                    src={`https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encodeURIComponent(drug.name)}/PNG`}
                    alt={`PubChem structure for ${drug.name}`}
                    className="mx-auto max-h-72 rounded-lg bg-white"
                  />
                  {chemLoading ? (
                    <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
                      <Loader2 className="h-4 w-4 animate-spin" /> Loading PubChem properties…
                    </div>
                  ) : chemError ? (
                    <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
                      {chemError}
                    </div>
                  ) : chem ? (
                    <>
                      <dl className="mt-3 space-y-2 text-sm">
                        <div>
                          <dt className="font-medium text-gray-900 dark:text-gray-100">Canonical SMILES</dt>
                          <dd className="break-all text-gray-600 dark:text-gray-300">{chem.smiles || 'Not available'}</dd>
                        </div>
                        <div>
                          <dt className="font-medium text-gray-900 dark:text-gray-100">IUPAC name</dt>
                          <dd className="break-words text-gray-600 dark:text-gray-300">{chem.iupac || 'Not available'}</dd>
                        </div>
                        {chem.cid && (
                          <div>
                            <dt className="font-medium text-gray-900 dark:text-gray-100">PubChem CID</dt>
                            <dd className="text-gray-600 dark:text-gray-300">{chem.cid}</dd>
                          </div>
                        )}
                      </dl>
                      {chem.source_url && (
                        <a
                          href={chem.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-3 inline-flex items-center gap-1 text-sm text-purple-600 hover:underline dark:text-purple-400"
                        >
                          PubChem <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </>
                  ) : null}
                </>
              ) : (
                <div className="flex min-h-64 items-center justify-center rounded-lg bg-gray-50 p-6 text-center text-gray-500 dark:bg-gray-900">
                  Select a drug candidate to inspect its PubChem structure and properties.
                </div>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
