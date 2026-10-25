"""A small, attributable graph neighborhood; a generated link never becomes an assertion."""
import hashlib
import json
from . import db, service


def source_view(row):
    metadata=json.loads(row['metadata'])
    return {**{k:row[k] for k in ('id','kind','origin_id','version','title')},
            'authorship':metadata.get('authorship') or ('ai' if row['kind']=='learning' else 'user'),
            'review_id':metadata.get('review_id')}


def evidence_view(row):
    return {**{k:row[k] for k in ('id','concept_id','assertion_id','source_id','basis')},'quote':row['quote'][:1000]}


def build(owner):
    sources={r['id']:r for r in db.all("SELECT * FROM knowledge_sources WHERE owner=? AND state='active' ORDER BY created_at DESC,id",(owner,))}
    proofs=[r for r in db.all("SELECT * FROM knowledge_evidence WHERE owner=? AND basis!='question' ORDER BY id",(owner,)) if r['source_id'] in sources]
    supported=[r for r in proofs if r['disposition']=='supports']
    concepts={r['id']:{k:r[k] for k in ('id','pref_label','definition','scope')} for r in db.all('SELECT * FROM knowledge_concepts WHERE owner=?',(owner,))}
    valid=[]
    for edge in db.all("SELECT id,subject,kind,object,text,scope FROM knowledge_assertions WHERE owner=? AND kind!='CLAIM' ORDER BY created_at DESC,id",(owner,)):
        if any(e['assertion_id']==edge['id'] and e['disposition']=='refutes' for e in proofs):continue
        required=[]
        for key,value in [('assertion_id',edge['id']),('concept_id',edge['subject']),('concept_id',edge['object'])]:
            proof=next((e for e in supported if e[key]==value),None)
            if proof:required.append(proof)
        if len(required)==3:valid.append((edge,required))
    context=dict(concepts=[],assertions=[],evidence=[],sources=[])
    if not valid:return context
    # Most recent supported source selects an anchor; only its immediate relations enter the prompt.
    anchor=next((e['concept_id'] for source in sources for e in supported if e['source_id']==source and e['concept_id']
                 and any(e['concept_id'] in (a['subject'],a['object']) for a,_ in valid)),valid[0][0]['subject'])
    selected_proofs={};selected_concepts=set();selected_sources=set()
    for edge,required in valid:
        if anchor not in (edge['subject'],edge['object']):continue
        next_sources=selected_sources|{e['source_id'] for e in required}
        next_concepts=selected_concepts|{edge['subject'],edge['object']}
        if len(next_sources)>8 or len(next_concepts)>12:continue
        context['assertions'].append(edge);selected_sources=next_sources;selected_concepts=next_concepts
        selected_proofs.update((e['id'],e) for e in required)
        if len(context['assertions'])==6:break
    context['concepts']=[concepts[k] for k in sorted(selected_concepts)]
    context['evidence']=[evidence_view(e) for _,e in sorted(selected_proofs.items())][:32]
    context['sources']=[source_view(sources[k]) for k in sorted(selected_sources)]
    return context


def fingerprint(context):
    return hashlib.sha256(service.dump(context).encode()).hexdigest()


def valid(owner,context):
    for source in context['sources']:
        current=db.one("SELECT * FROM knowledge_sources WHERE owner=? AND id=? AND state='active'",(owner,source['id']))
        if not current or source_view(current)!=source:return False
    for concept in context['concepts']:
        current=db.one('SELECT id,pref_label,definition,scope FROM knowledge_concepts WHERE owner=? AND id=?',(owner,concept['id']))
        if current!=concept:return False
    for edge in context['assertions']:
        current=db.one('SELECT id,subject,kind,object,text,scope FROM knowledge_assertions WHERE owner=? AND id=?',(owner,edge['id']))
        if current!=edge:return False
        if db.one("""SELECT 1 FROM knowledge_evidence e JOIN knowledge_sources s ON s.owner=e.owner AND s.id=e.source_id
            WHERE e.owner=? AND e.assertion_id=? AND e.disposition='refutes' AND e.basis!='question' AND s.state='active'""",(owner,edge['id'])):return False
    for evidence in context['evidence']:
        current=db.one("SELECT * FROM knowledge_evidence WHERE owner=? AND id=? AND disposition='supports' AND basis!='question'",(owner,evidence['id']))
        if not current or evidence_view(current)!=evidence:return False
    return True


def validate(context,bundle):
    concepts={c['id'] for c in context['concepts']};edges={a['id']:a for a in context['assertions']};proofs={e['id']:e for e in context['evidence']}
    for item in bundle.suggestions:
        ids=set(item.concept_ids)
        if not ids<=concepts or not set(item.assertion_ids)<=edges.keys() or not set(item.evidence_ids)<=proofs.keys():
            raise service.Error('제안의 개념·근거가 요청한 그래프와 일치하지 않습니다.',422)
        if any(not {edges[k]['subject'],edges[k]['object']}<=ids for k in item.assertion_ids):
            raise service.Error('제안의 연결 양끝 개념이 일치하지 않습니다.',422)
        for edge in item.assertion_ids:
            if not any(proofs[e]['assertion_id']==edge for e in item.evidence_ids):raise service.Error('제안에 관계의 근거가 빠져 있습니다.',422)
        if any(proofs[e]['concept_id'] not in ids and proofs[e]['assertion_id'] not in item.assertion_ids for e in item.evidence_ids):
            raise service.Error('제안과 무관한 근거가 포함되어 있습니다.',422)
        if any('```' in value for value in (item.title,item.why,item.question,item.reading_guide,item.practice_guide,item.expected_output)):
            raise service.Error('완성 코드 대신 직접 탐구할 가이드가 필요합니다.',422)
