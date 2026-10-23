"""Independent raw identities; imported snapshots and references to existing notes."""
import uuid
from datetime import datetime, timezone


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS resources (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id),
        kind TEXT NOT NULL CHECK(kind IN ('source','note')), origin_id TEXT NOT NULL,
        note_id TEXT, created_at TEXT NOT NULL,
        UNIQUE(owner,kind,origin_id), UNIQUE(owner,id),
        CHECK((kind='source' AND note_id IS NULL) OR
              (kind='note' AND note_id IS NOT NULL AND note_id=origin_id)),
        FOREIGN KEY(owner,note_id) REFERENCES reference_notes(owner,id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS resource_versions (
        owner TEXT NOT NULL, resource_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
        kind TEXT NOT NULL, name TEXT NOT NULL, url TEXT, content TEXT, created_at TEXT NOT NULL,
        PRIMARY KEY(owner,resource_id,revision),
        FOREIGN KEY(owner,resource_id) REFERENCES resources(owner,id))''')


def migrate(c, context_id=None):
    """Caller owns the write transaction, including any subsequent legacy deletion."""
    query = '''SELECT d.*,g.owner,g.created_at FROM source_documents d
               JOIN generations g ON g.id=d.id'''
    params = ()
    if context_id is not None:
        query += ' WHERE d.context_id=? OR g.context_id=?'
        params = (context_id, context_id)
    # shortcut: legacy writers snapshot at startup/deletion; switch to live writes with P2 registration.
    for source in c.execute(query, params):
        c.execute('''INSERT INTO resources(id,owner,kind,origin_id,created_at) VALUES (?,?,'source',?,?)
                     ON CONFLICT(owner,kind,origin_id) DO NOTHING''',
                  (uuid.uuid4().hex, source['owner'], source['id'], source['created_at']))
        resource_id = c.execute("SELECT id FROM resources WHERE owner=? AND kind='source' AND origin_id=?",
                                (source['owner'], source['id'])).fetchone()['id']
        previous = c.execute('''SELECT * FROM resource_versions WHERE owner=? AND resource_id=?
                                ORDER BY revision DESC LIMIT 1''', (source['owner'], resource_id)).fetchone()
        fields = ('kind', 'name', 'url', 'content')
        values = tuple(source[field] for field in fields)
        if previous and tuple(previous[field] for field in fields) == values:
            continue
        c.execute('''INSERT INTO resource_versions(owner,resource_id,revision,kind,name,url,content,created_at)
                     VALUES (?,?,?,?,?,?,?,?)''',
                  (source['owner'], resource_id, previous['revision'] + 1 if previous else 1,
                   *values, datetime.now(timezone.utc).isoformat()))
    if context_id is None:
        for note in c.execute('SELECT id,owner,created_at FROM reference_notes'):
            c.execute('''INSERT INTO resources(id,owner,kind,origin_id,note_id,created_at)
                         VALUES (?,?,'note',?,?,?) ON CONFLICT(owner,kind,origin_id) DO NOTHING''',
                      (uuid.uuid4().hex, note['owner'], note['id'], note['id'], note['created_at']))
