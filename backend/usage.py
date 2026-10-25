"""Provider-reported token counts only; never retain prompts or API secrets."""
from contextvars import ContextVar
from datetime import datetime, timezone
import uuid
from . import db

scope = ContextVar('ai_usage_scope', default=None)


def start(operation, repair, connection):
    current = scope.get()
    if current is None:
        return None  # Isolated validation tools are not attributed to a real learner.
    owner, generation_id = current
    if generation_id:
        job = db.one('SELECT candidate FROM generations WHERE id=? AND owner=?', (generation_id, owner))
        repair = repair or bool(job and job['candidate'] > 1)
    call_id = uuid.uuid4().hex
    model = connection['model']
    with db.connect(write=True) as c:
        c.execute('''INSERT INTO ai_usage
            (id,owner,generation_id,operation,model,repair,input_tokens,output_tokens,state,created_at,settings_version,provider_url)
            VALUES (?,?,?,?,?,?,NULL,NULL,?,?,?,?)''',
            (call_id, owner, generation_id, operation, model, int(repair), 'started', datetime.now(timezone.utc).isoformat(),
             connection['revision'], connection['provider_url']))
        if generation_id:
            for table in ('interpretations', 'worksheets', 'knowledge_proposals', 'material_proposals', 'insight_jobs'):
                c.execute(f'UPDATE {table} SET model=? WHERE owner=? AND id=?', (model, owner, generation_id))
    return call_id


def finish(call_id, provider_usage, state):
    if not call_id:
        return
    def count(name):
        value = provider_usage.get(name) if isinstance(provider_usage, dict) else None
        return value if type(value) is int and value >= 0 else None
    db.execute('UPDATE ai_usage SET input_tokens=?,output_tokens=?,state=? WHERE id=?',
               (count('prompt_tokens'), count('completion_tokens'), state, call_id))


def summary(owner):
    rows = db.all('''SELECT u.generation_id,u.operation,u.model,u.settings_version,u.provider_url,g.context_id,g.unit_id,
        json_extract(c.data,'$.title') AS context_title,
        COUNT(*) AS calls,SUM(u.repair) AS repair_calls,
        SUM(COALESCE(u.input_tokens,0)) AS input_tokens,SUM(COALESCE(u.output_tokens,0)) AS output_tokens,
        SUM(u.input_tokens IS NULL OR u.output_tokens IS NULL) AS unknown_usage_calls,
        SUM(u.state='error') AS failed_calls,MAX(u.created_at) AS last_used_at
        FROM ai_usage u LEFT JOIN generations g ON g.id=u.generation_id AND g.owner=u.owner
        LEFT JOIN contexts c ON c.id=g.context_id AND c.owner=u.owner
        WHERE u.owner=? GROUP BY u.generation_id,u.operation,u.model,u.settings_version,u.provider_url ORDER BY last_used_at DESC''', (owner,))
    return {'items': rows, 'totals': {key: sum(r[key] for r in rows) for key in
            ('calls', 'repair_calls', 'input_tokens', 'output_tokens', 'unknown_usage_calls', 'failed_calls')}}
