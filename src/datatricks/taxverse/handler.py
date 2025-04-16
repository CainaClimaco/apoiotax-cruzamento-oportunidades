import requests
import json

base_url = "http://api.taxverse.com.br/"

request_status = [
    "Em.Fila",
    "EM.Processamento",
    "Falha.Reprocessar", 
    "Sucesso",
    "Falha.Alteryx",
    "Falha.Sistema", 
    "Falha.Formato", 
    "Falha.Arquivo",
    "Falha.ArqEntradaNEncontrado",
    "Falha.ArqSaidaNEncontrado",
    "Falha.Rpa.Timeout"
  ]

def exemplo(url):
    return "teste"

def get_file(accesskey, requestId ):
    
    url = base_url + "toolAnswer/robot/getFile"
    payload = json.dumps({
    "requestId": str(requestId)
    })
    return requests.request("POST",url, headers=get_header(accesskey=accesskey), data=payload).text


def getAll(accesskey, requestId, status, robotName):
  if status not in request_status:
    raise ValueError("Status not allowed")
  
  url =base_url + "toolAnswer/robot/getAll"

  if requestId == None:
    payload = json.dumps({
      "status": str(status),
      "robotName": str(robotName) 
    })
  else:
    payload = json.dumps({
      "requestId": str(requestId),
      "status": str(status),
      "robotName": str(robotName) 
    })
     
  return requests.request("POST", url, headers=get_header(accesskey=accesskey), data=payload).json()


def update_filesize(accesskey, requestId,  filesize):
  
  url = base_url + "toolAnswer/robot/update"
  payload = json.dumps({
    "requestId": str(requestId),
    "processedFileSize": str(filesize)
  })

  return requests.request("POST", url, headers=get_header(accesskey=accesskey), data=payload).json()



def update_competence(accesskey=None, requestId=0 ,competences=0 ):

  url = base_url + "toolAnswer/robot/update/competence"
  
  payload = json.dumps({
    "requestId": str(requestId),
    "competence": str(competences)
  })
  return requests.post(url, headers=get_header(accesskey=accesskey), data=payload).json()



def get_header(accesskey):
  return {
    'robotAccessKey':  str(accesskey),
    'Content-Type': 'application/json'
  }

