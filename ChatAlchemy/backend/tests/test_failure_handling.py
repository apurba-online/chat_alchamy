import pytest
from chatalchemy.reasoning.engine import ReasoningEngine
class Broken:
    async def resolve(self,*a,**k): raise RuntimeError('timeout')
@pytest.mark.asyncio
async def test_source_failure_becomes_warning_not_hallucination():
    r=await ReasoningEngine({'rxnorm':Broken()}).answer('What is the generic identity of Tylenol?'); assert not r.evidence and r.warnings and 'No supporting records' in r.answer
