"""Own captured-format private review fields; capacities are technical, never legal rules."""
from typing import Annotated,Literal
from pydantic import BaseModel,ConfigDict,Field,AfterValidator

def text(value):
 if any(not(c=='\n' or 32<=ord(c)<=55295 or 57344<=ord(c)<=65533 or 65536<=ord(c)<=1114111) for c in value):raise ValueError('Unsupported XML/text control')
 return value.strip()
def bounded(n):return Annotated[str,Field(strict=True,max_length=n),AfterValidator(text)]
class OwnBase(BaseModel):model_config=ConfigDict(extra='forbid',strict=True)
class Application(OwnBase):
 applicantName:bounded(180)=''
 agentName:bounded(180)=''
 respondentName:bounded(180)=''
 requests:list[bounded(360)]=Field(default_factory=lambda:[''],max_length=3)
 factsReason:bounded(2400)=''
class EvidenceItem(OwnBase):
 name:bounded(60)=''
 pageCount:Annotated[str,Field(strict=True,max_length=4,pattern=r'^$|^[1-9][0-9]{0,3}$'),AfterValidator(text)]=''
 originalType:Literal['','原件','复印件']=''
 purpose:bounded(80)=''
 pageRange:bounded(32)=''
class Evidence(OwnBase):evidenceList:list[EvidenceItem]=Field(default_factory=lambda:[EvidenceItem()],max_length=9)

# Standard route-facing aliases; same own strict data models.
HuianQuangangApplicationRequest=Application
HuianQuangangEvidenceRequest=Evidence
