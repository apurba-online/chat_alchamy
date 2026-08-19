from __future__ import annotations
from ..models import EvidenceItem
from .base import LiveSource
class PubChemSource(LiveSource):
    name="PubChem";base_url="https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    async def compound(self,name:str)->list[EvidenceItem]:
        if not name:return[]
        props=(((await self._get(f"{self.base_url}/compound/name/{name}/property/CanonicalSMILES,IUPACName/JSON")).get("PropertyTable") or {}).get("Properties") or [])
        if not props:return[]
        p=props[0];cid=str(p.get("CID") or "");return[EvidenceItem.build(subject=name,predicate="compound_properties",value={"canonical_smiles":p.get("ConnectivitySMILES") or p.get("CanonicalSMILES"),"iupac_name":p.get("IUPACName"),"cid":cid},source=self.name,source_record_id=cid or None,source_url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else f"https://pubchem.ncbi.nlm.nih.gov/#query={name}")]
