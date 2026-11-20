"""Portable owner records, separate from the operator's complete SQLite backup."""
import base64
import io
import json
import zipfile
from . import db, service

# Explicit allowlist: credentials, sessions and integration secrets never enter an archive.
TABLES = '''reference_packages reference_package_versions technical_references technical_reference_versions technical_reference_saves technical_reference_jobs study_policy study_locations study_choices study_recommendations contexts generations progress attempts reports generation_reports learning_summaries
feed_choices assistance review_schedule review_sessions ai_usage foundation_progress foundation_reviews
foundation_attempts resources resource_versions resource_registrations resource_requests resource_feed_posts
interpretations interpretation_requests interpretation_retries worksheets worksheet_requests
practice_record_versions practice_record_requests material_reviews material_proposals material_proposal_requests
spaced_reviews spaced_review_responses reference_notes reference_note_versions reference_images
knowledge_sources knowledge_concepts knowledge_aliases knowledge_assertions knowledge_evidence
knowledge_proposals knowledge_registrations reference_reviews learning_observations question_memos
question_guides daily_question_recommendations brain_sources brain_records brain_record_versions brain_links
brain_drafts wiki_documents wiki_document_versions wiki_pages wiki_page_versions wiki_jobs
insight_jobs insight_requests insight_bundles explorations insight_skips manual_problems
manual_books manual_problem_attempts manual_problem_reviews'''.split()
CHILDREN = {
    'manual_problem_versions': 'problem_id IN (SELECT id FROM manual_problems WHERE owner=?)',
    'manual_book_items': 'book_id IN (SELECT id FROM manual_books WHERE owner=?)',
    'sets': 'context_id IN (SELECT id FROM contexts WHERE owner=?)',
    'exercises': 'set_id IN (SELECT s.id FROM sets s JOIN contexts c ON c.id=s.context_id WHERE c.owner=?)',
    'generation_drafts': 'context_id IN (SELECT id FROM contexts WHERE owner=?)',
    'source_documents': 'id IN (SELECT id FROM generations WHERE owner=?)',
    'attempt_learning': 'attempt_id IN (SELECT id FROM attempts WHERE owner=?)',
}


def export(owner):
    buffer = io.BytesIO()
    counts = {}
    with db.connect() as c, zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        c.execute('BEGIN')
        for table in TABLES + list(CHILDREN):
            condition = CHILDREN.get(table, 'owner=?')
            records = [dict(row) for row in c.execute(f'SELECT * FROM {table} WHERE {condition}', (owner,))]
            for row in records:
                for key, value in row.items():
                    if isinstance(value, bytes):
                        row[key] = {'encoding': 'base64', 'data': base64.b64encode(value).decode('ascii')}
            counts[table] = len(records)
            archive.writestr(f'records/{table}.json', json.dumps(records, ensure_ascii=False))
        archive.writestr('manifest.json', json.dumps({'format': 'code-trainer-records-v1', 'created_at': service.now(),
            'tables': counts, 'binary_encoding': 'base64',
            'excluded': ['credentials', 'sessions', 'integration secrets', 'other owners', 'shared feed configuration'],
            'restore': 'This is a portable record archive, not an automatic database import. Use the operator SQLite backup for full restoration.'}, ensure_ascii=False, indent=2))
        archive.writestr('README.md', '# Code Trainer records\n\nUTF-8 JSON records retain original IDs, source versions, drafts and history.\n'
            'Images use base64. Keep this private. For full restoration use scripts/backup.py and the operations guide.\n')
    return buffer.getvalue()
