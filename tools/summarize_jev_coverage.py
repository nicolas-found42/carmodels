#!/usr/bin/env python3
"""Index unique persisted Jev results; this is evidence coverage, not billing."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TOOLS={'jev_'+x for x in 'verify screen find rerank classify decide compare extract audit review gate noul'.split()}
def judgments(node):
    if isinstance(node,dict):
        if node.get('tool') in TOOLS:
            yield node;return
        for key,value in node.items():
            if key not in ['args','request','evidence','diff','files','claims','tests','source']:
                yield from judgments(value)
    elif isinstance(node,list):
        for child in node:yield from judgments(child)
    elif isinstance(node,str) and node.lstrip().startswith('{'):
        try:parsed=json.loads(node)
        except ValueError:return
        yield from judgments(parsed)

def main():
    rows=[];seen=set()
    for path in sorted((ROOT/'research/evidence').rglob('*.json')):
        if path.name=='jev-capability-coverage.json':continue
        try:node=json.loads(path.read_text())
        except (ValueError,UnicodeDecodeError):continue
        for result in judgments(node):
            digest=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
            if digest in seen:continue
            seen.add(digest)
            rows.append({'receipt':str(path.relative_to(ROOT)),'tool':result['tool'],'result_sha256':digest,'usage':result.get('usage'),'action':result.get('action',result.get('recommendation',{}).get('action')),'summary':result.get('summary'),'receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    counts=Counter(x['tool'] for x in rows)
    usage={k:sum((x['usage'] or {}).get(k,0) for x in rows) for k in ['input_tokens','output_tokens']}
    result={'counts':dict(counts),'all_12_present':TOOLS<=counts.keys(),'unique_results':len(rows),'persisted_usage':usage,'receipts':rows,'limits':['Unique persisted model results deduplicated by exact structured-result hash; not an API request or invoice count.','All12 present establishes exercised capabilities, not correctness or final recovery completion.','Invalid argument/API failures and non-JSON output are operational failures; not counted as accepted model results.']}
    output=ROOT/'research/evidence/continuation/jev-capability-coverage.json'
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['counts','all_12_present','unique_results','persisted_usage']}))

if __name__=='__main__':main()
