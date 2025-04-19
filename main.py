from typing import Dict,List, TypedDict, Tuple
import logging
import os
import requests
import json

logging.basicConfig()
logging.root.setLevel(logging.INFO)

logger = logging.getLogger("convert")

class Record(TypedDict):
    content: str
    comment: str
    disabled: False

class RRSET(TypedDict):
    name: str
    type: str
    ttl: int
    changetype: str
    records: List[Record]
    

path:str = input("Enter path to cloudlfare export (domain.txt): ")
ignore_domain: str = input("Enter your base domain (ex: 'example.com.'): ")

cloudflare_records: List[str] = []

with open(path,"r") as f:
    cloudflare_records = f.readlines()
    
seen_record_names: Dict[str,str] = {}
converted_records: Dict[str, RRSET] = {}
    
def process_record(record: str) -> Tuple[str,RRSET] | None:
    """The format for records goes as:
    
    record_name     TTL     "IN"        Type        "Content" ; comment
    
    """
    print("")
    if record.startswith(";;"): return
    if len(record) < 3: return

    parts: List[str] = record.split("\t")
    record_name: str = parts[0].strip()
    ttl: int = int(parts[1])
    record_type = parts[3].strip()
    
    if record_name == ignore_domain:
        return
    
    if record_type == "SOA":
        logger.info(f"Ignoring SOA record {record_name}")
        return
    
    if record_type == "TXT":
        logging.info(f"Running record {record_name} through TXT comment seperation")
        record_value = '"' + parts[4].split('"')[1].strip() + '"'
        try:
            record_comment = ''.join(parts[4].split('"')[2:]).split(";")[1].strip()
        except IndexError:
            logger.info(f"No comment found for record {record_name}")
            record_comment = ""
    else:
        logger.info(f"Running record {record_name} through normal comment seperation")
        value_parts = parts[4].split(";")
        record_value = parts[4].split(";")[0].strip()
        
        record_comment: str = ""
        
        if len(value_parts) > 1: 
            record_comment = value_parts[1]
        else:
            logger.info(f"No comment found for record {record_name}")
    
    if record_name in seen_record_names:
        logger.warning(f"Duplicate record found for {record_name}. Using importance strategy")
        if record_value in ["0.0.0.0", "example.com"]:
            logger.warning(f"Record {record_name}:{record_value} is not deemed important enough for replacement... Using {seen_record_names[record_name]}")
            return None
        
        elif seen_record_names[record_name] in ["0.0.0.0", "example.com"]:
            logger.warning(f"Replaced {record_name} with content {record_value}")
            pass
        
        else:
            logger.warning("Both records are important... Using newer one")
            pass
    
    seen_record_names[record_name] = record_value
        
    return (record_name, {
        "name": record_name,
        "type": record_type,
        "ttl": ttl,
        "changetype": "REPLACE",
        "records": [{
            "content": record_value,
            "disabled": False,
            "comment": record_comment
            }]
        })



for record in cloudflare_records:
    process_result: Tuple[str,RRSET] | None = process_record(record)
    if process_result is not None:
        record_name = process_result[0]
        converted_records[record_name] = process_result[1]
        
with open("conv.json","w") as f:
    json.dump(converted_records,f)
    
rrsets = []
    
for record in converted_records.values():
    rrsets.append(record)

with open("result.json","w") as f:
    json.dump({"rrsets": rrsets},f)
    
logger.info("Saved to results.json")