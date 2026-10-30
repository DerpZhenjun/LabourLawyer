"""Public deployment configuration only; never probes a service or starts a model."""
import ipaddress
import os
import re
from typing import Literal
from fastapi import APIRouter,Response
from pydantic import BaseModel,ConfigDict

router=APIRouter()
class DigitalService(BaseModel):
 model_config=ConfigDict(extra='forbid')
 status:Literal['configured','not_configured','invalid_configuration']
 url:str|None=None
class ServiceCapabilities(BaseModel):
 model_config=ConfigDict(extra='forbid')
 digital:DigitalService

def service_origin(value):
 if not isinstance(value,str):raise ValueError('Invalid configured service')
 match=re.fullmatch(r'(https?)://(\[::1\]|[a-z0-9.-]+)(?::([0-9]{1,5}))?/?',value.strip(),re.I)
 if not match:raise ValueError('Invalid configured service')
 scheme,host,port=match.groups();scheme=scheme.lower();host=host.lower()
 if port and (not re.fullmatch(r'[1-9][0-9]*',port) or int(port)>65535):raise ValueError('Invalid port')
 private=host in {'localhost','[::1]'}
 if re.fullmatch(r'[0-9.]+',host):
  address=ipaddress.IPv4Address(host)
  private=address.is_loopback or any(address in ipaddress.ip_network(n) for n in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'])
 elif host!='[::1]' and (len(host)>253 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',label) for label in host.split('.'))):raise ValueError('Invalid host')
 if scheme=='http' and not private:raise ValueError('Public services require HTTPS')
 return f'{scheme}://{host}'+(':'+port if port else '')

def capabilities():
 raw=os.environ.get('LABOURLAWYER_DIGITAL_URL','')
 if not raw.strip():return ServiceCapabilities(digital=DigitalService(status='not_configured'))
 try:return ServiceCapabilities(digital=DigitalService(status='configured',url=service_origin(raw)))
 except (ValueError,TypeError):return ServiceCapabilities(digital=DigitalService(status='invalid_configuration'))

@router.get('/api/services',response_model=ServiceCapabilities)
def services(response:Response):
 response.headers['Cache-Control']='no-store'
 return capabilities()
