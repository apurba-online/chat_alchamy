from __future__ import annotations

from urllib.parse import quote
from uuid import uuid4
from .base import BaseSource
from ..models import EvidenceItem


class PubChemSource(BaseSource):
    name = "pubchem"
    base = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    async def compound(self, name: str) -> tuple[list[EvidenceItem], float]:
        encoded = quote(name, safe="")
        url = f"{self.base}/compound/name/{encoded}/property/CanonicalSMILES,IUPACName/JSON"
        data, latency = await self._request_json("GET", url)
        props = (((data.get("PropertyTable") or {}).get("Properties")) or [])
        out = []
        for p in props[:1]:
            cid = str(p.get("CID") or "")
            out.append(EvidenceItem(id=f"pubchem-{uuid4().hex[:12]}", source=self.name, source_record_id=cid or None, source_url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else None, subject=name, canonical_subject=name, predicate="compound_properties", value={"canonical_smiles": p.get("ConnectivitySMILES") or p.get("CanonicalSMILES"), "iupac_name": p.get("IUPACName")}, identifiers={"pubchem_cid": cid}, context={"structure_png": f"{self.base}/compound/cid/{cid}/PNG" if cid else None}, raw=p))
        return out, latency
