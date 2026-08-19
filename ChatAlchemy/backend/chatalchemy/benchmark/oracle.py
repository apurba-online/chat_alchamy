from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from .generator import BenchmarkCase


@dataclass
class OracleResult:
    kind: str
    value: Any
    source_records: list[dict[str, Any]]


class LiveOracle:
    """Independent query-time oracle using direct public API calls only."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=25,
            follow_redirects=True,
            headers={
                "User-Agent": "LiveBioEvidenceBench/1.0 (+https://github.com/apurba-online/chat_alchamy)",
                "Accept": "application/json",
                "Cache-Control": "no-cache",
            },
        )

    async def close(self):
        await self.client.aclose()

    async def _get(self, url: str, params: dict[str, Any] | None = None, attempts: int = 3) -> dict[str, Any]:
        last: Exception | None = None
        for attempt in range(attempts):
            try:
                response = await self.client.get(url, params=params)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < attempts - 1:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last = exc
                if attempt < attempts - 1:
                    await asyncio.sleep(0.3 * (2**attempt))
        assert last is not None
        raise last

    async def _post(self, url: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        response = await self.client.post(url, json={"query": query, "variables": variables})
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(str(payload["errors"]))
        return payload

    @staticmethod
    def _record(source: str, record: Any) -> dict[str, Any]:
        return {
            "source": source,
            "record": str(record) if record is not None else None,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _identity(self, drug: str):
        base = "https://rxnav.nlm.nih.gov/REST"
        ids: list[str] = []
        try:
            data = await self._get(f"{base}/rxcui.json", {"name": drug, "search": 2}, attempts=1)
            ids = [str(x) for x in (data.get("idGroup") or {}).get("rxnormId", []) or []]
        except Exception:
            pass
        if not ids:
            data = await self._get(f"{base}/approximateTerm.json", {"term": drug, "maxEntries": 8, "option": 1})
            ids = [str(c.get("rxcui")) for c in (data.get("approximateGroup") or {}).get("candidate", []) or [] if c.get("rxcui")]
        ranked: list[tuple[int, dict[str, Any]]] = []
        for rid in ids[:8]:
            try:
                props = (await self._get(f"{base}/rxcui/{rid}/properties.json")).get("properties") or {}
            except Exception:
                continue
            if props:
                ranked.append(({"IN": 0, "PIN": 1, "MIN": 2}.get(props.get("tty", ""), 9), props))
        if not ranked:
            return None, []
        ranked.sort(key=lambda item: item[0])
        best = ranked[0][1]
        if ranked[0][0] >= 9:
            for tty in ("IN", "PIN", "MIN"):
                try:
                    related = await self._get(f"{base}/rxcui/{best['rxcui']}/related.json", {"tty": tty}, attempts=1)
                except Exception:
                    continue
                concepts = [cp for group in (related.get("relatedGroup") or {}).get("conceptGroup", []) or [] for cp in group.get("conceptProperties") or []]
                if concepts:
                    best = concepts[0]
                    break
        rid = best.get("rxcui")
        return str(best.get("name") or drug).lower(), [self._record("RxNorm", rid)]

    async def _labels(self, drug: str, limit: int = 20):
        data = await self._get("https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json", {"drug_name": drug, "pagesize": limit})
        rows = data.get("data") or []
        ids = sorted({str(row.get("setid") or row.get("set_id")) for row in rows if row.get("setid") or row.get("set_id")})
        return ids, [self._record("DailyMed", record) for record in ids]

    async def _approvals(self, drug: str, limit: int = 20):
        endpoint = "https://api.fda.gov/drug/drugsfda.json"
        payload = None
        for search in [f'openfda.generic_name:"{drug}"', f'openfda.brand_name:"{drug}"', f'products.active_ingredients.name:"{drug}"']:
            try:
                candidate = await self._get(endpoint, {"search": search, "limit": min(limit, 100)}, attempts=1)
                if candidate.get("results"):
                    payload = candidate
                    break
            except Exception:
                continue
        rows = (payload or {}).get("results") or []
        apps = sorted({str(row.get("application_number")) for row in rows if row.get("application_number")})
        return apps, [self._record("Drugs@FDA/openFDA", record) for record in apps]

    async def _trials(self, drug: str | None, condition: str | None, phase: str | None, status: str | None, limit: int = 20):
        params: dict[str, Any] = {"pageSize": min(limit * 3, 100)}
        if drug:
            params["query.intr"] = drug
        if condition:
            params["query.cond"] = condition
        data = await self._get("https://clinicaltrials.gov/api/v2/studies", params)
        ids: list[str] = []
        for study in data.get("studies") or []:
            protocol = study.get("protocolSection") or {}
            ident = protocol.get("identificationModule") or {}
            design = protocol.get("designModule") or {}
            status_mod = protocol.get("statusModule") or {}
            phases = design.get("phases") or []
            overall = status_mod.get("overallStatus")
            if phase and phase not in phases:
                continue
            if status and status != overall:
                continue
            if ident.get("nctId"):
                ids.append(str(ident["nctId"]))
            if len(ids) >= limit:
                break
        ids = sorted(set(ids))
        return ids, [self._record("ClinicalTrials.gov", record) for record in ids]

    async def _target_drugs(self, target: str, limit: int = 20):
        base = "https://www.ebi.ac.uk/chembl/api/data"
        targets = (await self._get(f"{base}/target/search.json", {"q": target, "limit": 10})).get("targets") or []

        def score(row):
            text = " ".join(str(row.get(key, "")) for key in ["pref_name", "target_chembl_id", "organism", "target_type"]).upper()
            return (10 if target.upper() in text else 0) + (5 if row.get("organism") == "Homo sapiens" else 0) + (3 if row.get("target_type") == "SINGLE PROTEIN" else 0)

        mechanisms: list[dict[str, Any]] = []
        for item in sorted(targets, key=score, reverse=True)[:6]:
            target_id = item.get("target_chembl_id")
            if not target_id:
                continue
            try:
                payload = await self._get(f"{base}/mechanism.json", {"target_chembl_id": target_id, "limit": 50}, attempts=1)
            except Exception:
                continue
            mechanisms.extend(payload.get("mechanisms") or [])
        molecule_ids = list(dict.fromkeys(str(m.get("molecule_chembl_id")) for m in mechanisms if m.get("molecule_chembl_id")))[:limit]

        async def fetch(mid: str):
            try:
                return mid, await self._get(f"{base}/molecule/{mid}.json", attempts=1)
            except Exception:
                return mid, {}

        molecules = dict(await asyncio.gather(*(fetch(mid) for mid in molecule_ids))) if molecule_ids else {}
        names = [str((molecules.get(mid) or {}).get("pref_name") or mid).lower() for mid in molecule_ids]
        return sorted(set(names)), [self._record("ChEMBL", mid) for mid in molecule_ids]

    async def _ot_search_id(self, query_text: str, entity: str) -> str | None:
        endpoint = "https://api.platform.opentargets.org/api/v4/graphql"
        query = '''query Search($q: String!, $entities: [String!]) { search(queryString: $q, entityNames: $entities, page: {index: 0, size: 5}) { hits { id entity name description } } }'''
        payload = await self._post(endpoint, query, {"q": query_text, "entities": [entity]})
        hits = (((payload.get("data") or {}).get("search") or {}).get("hits") or [])
        return str(hits[0].get("id")) if hits and hits[0].get("id") else None

    async def _ot_drug_name(self, chembl_id: str) -> str:
        endpoint = "https://api.platform.opentargets.org/api/v4/graphql"
        query = '''query Drug($id: String!) { drug(chemblId: $id) { id name } }'''
        try:
            payload = await self._post(endpoint, query, {"id": chembl_id})
            return str(((payload.get("data") or {}).get("drug") or {}).get("name") or chembl_id)
        except Exception:
            return chembl_id

    async def _gene(self, gene: str, limit: int = 20):
        endpoint = "https://api.platform.opentargets.org/api/v4/graphql"
        target_id = await self._ot_search_id(gene, "target")
        if not target_id:
            return [], []
        query = '''
        query Target($id: String!) {
          target(ensemblId: $id) {
            id
            approvedSymbol
            associatedDiseases(page: {index: 0, size: 20}) {
              rows { disease { id name } score }
            }
            drugAndClinicalCandidates {
              rows { id drugId targetId maxClinicalStage diseases { diseaseId diseaseFromSource } }
            }
          }
        }
        '''
        obj = ((await self._post(endpoint, query, {"id": target_id})).get("data") or {}).get("target") or {}
        values: list[str] = []
        records = [self._record("Open Targets", target_id)]
        for row in ((obj.get("associatedDiseases") or {}).get("rows") or [])[:limit]:
            disease = row.get("disease") or {}
            if disease.get("name"):
                values.append(f"gene_disease_association:{str(disease['name']).lower()}")
            records.append(self._record("Open Targets", disease.get("id")))
        clinical_rows = ((obj.get("drugAndClinicalCandidates") or {}).get("rows") or [])[:limit]
        drug_ids = list(dict.fromkeys(str(row.get("drugId")) for row in clinical_rows if row.get("drugId")))
        names = dict(await asyncio.gather(*((self._ot_name_pair(drug_id)) for drug_id in drug_ids))) if drug_ids else {}
        for drug_id in drug_ids:
            values.append(f"known_drug:{names.get(drug_id, drug_id).lower()}")
            records.append(self._record("Open Targets", drug_id))
        return sorted(set(values)), records

    async def _ot_name_pair(self, drug_id: str) -> tuple[str, str]:
        return drug_id, await self._ot_drug_name(drug_id)

    async def _compound(self, compound: str):
        endpoint = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{compound}/property/CanonicalSMILES,IUPACName/JSON"
        props = (((await self._get(endpoint)).get("PropertyTable") or {}).get("Properties") or [])
        if not props:
            return {}, []
        p = props[0]
        cid = str(p.get("CID") or "")
        value = {
            "canonical_smiles": p.get("ConnectivitySMILES") or p.get("CanonicalSMILES"),
            "iupac_name": p.get("IUPACName"),
            "cid": cid,
        }
        return value, [self._record("PubChem", cid)]

    async def execute(self, case: BenchmarkCase) -> OracleResult:
        params = case.params
        family = case.family
        if family == "identity":
            value, records = await self._identity(params["drug"])
            return OracleResult("scalar", value, records)
        if family == "label":
            value, records = await self._labels(params["drug"])
            return OracleResult("set", value, records)
        if family == "approval":
            value, records = await self._approvals(params["drug"])
            return OracleResult("set", value, records)
        if family == "trials":
            value, records = await self._trials(params["drug"], params["condition"], params["phase"], None)
            return OracleResult("set", value, records)
        if family == "target":
            value, records = await self._target_drugs(params["target"])
            return OracleResult("set", value, records)
        if family == "gene":
            value, records = await self._gene(params["gene"])
            return OracleResult("set", value, records)
        if family == "compound":
            value, records = await self._compound(params["compound"])
            return OracleResult("record", value, records)
        if family == "cross":
            candidates, chembl_records = await self._target_drugs(params["target"], 15)

            async def check(name: str):
                approvals, trials = await asyncio.gather(
                    self._approvals(name, 3),
                    self._trials(name, params["condition"], params["phase"], params["status"], 10),
                )
                return name, approvals, trials

            checked = await asyncio.gather(*(check(name) for name in candidates[:10])) if candidates else []
            accepted = sorted({name for name, (apps, _), (trials, _) in checked if apps and trials})
            records = list(chembl_records)
            for _, (_, app_records), (_, trial_records) in checked:
                records.extend(app_records)
                records.extend(trial_records)
            return OracleResult("set", accepted, records)
        if family == "user_approval":
            checked = await asyncio.gather(*(self._approvals(name, 3) for name in params["candidates"]))
            accepted = sorted(name.lower() for name, (apps, _) in zip(params["candidates"], checked) if apps)
            records = [record for _, item_records in checked for record in item_records]
            return OracleResult("set", accepted, records)
        if family == "user_trials":
            checked = await asyncio.gather(*(self._trials(name, params["condition"], params["phase"], params["status"], 10) for name in params["candidates"]))
            accepted = sorted(name.lower() for name, (trials, _) in zip(params["candidates"], checked) if trials)
            records = [record for _, item_records in checked for record in item_records]
            return OracleResult("set", accepted, records)
        if family == "user_target":
            target_drugs, records = await self._target_drugs(params["target"], 50)
            live = set(target_drugs)
            accepted = sorted(name.lower() for name in params["candidates"] if name.lower() in live)
            return OracleResult("set", accepted, records)
        raise ValueError(f"Unknown family {family}")
