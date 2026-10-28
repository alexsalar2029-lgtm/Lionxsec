"""Local administrator uploads and multilingual learning/download content."""
import os
import re
import secrets
import time
from urllib.parse import urlsplit
import json

LANGS = ('fa', 'en', 'ar', 'es')
LIMITS = {'logo': 3 * 1024**2, 'video': 250 * 1024**2}


class ContentError(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status


def translations(value, limit=250, required=True):
    if not isinstance(value, dict) or set(value) != set(LANGS):
        raise ContentError('translations_required')
    if any(not isinstance(v, str) or len(v.strip()) > limit or (required and not v.strip()) for v in value.values()):
        raise ContentError('invalid_translation')
    return {lang: value[lang].strip() for lang in LANGS}


def download_url(value):
    if not isinstance(value, str) or len(value) > 2000 or any(c.isspace() or ord(c) < 32 for c in value):
        raise ContentError('invalid_download_url')
    try:
        url = urlsplit(value)
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.port not in (None, 443):
            raise ValueError
    except ValueError:
        raise ContentError('invalid_download_url') from None
    return value


def sniff(header, kind):
    if kind == 'logo':
        if header.startswith(b'\x89PNG\r\n\x1a\n') and header[12:16] == b'IHDR':
            return 'image/png', '.png'
        if header.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg', '.jpg'
        if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
            return 'image/webp', '.webp'
    if kind == 'video':
        if len(header) >= 12 and header[4:8] == b'ftyp' and header[8:12] in (
                b'isom', b'iso2', b'iso4', b'iso5', b'iso6', b'mp41', b'mp42', b'avc1', b'M4V ', b'dash'):
            return 'video/mp4', '.mp4'
        if header.startswith(b'\x1aE\xdf\xa3') and b'webm' in header:
            return 'video/webm', '.webm'
    raise ContentError('unsupported_upload', 415)


class ResourceStoreMixin:
    def init_content(self):
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS media (id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                mime TEXT NOT NULL, filename TEXT NOT NULL, original_name TEXT NOT NULL,
                size INTEGER NOT NULL, created INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS resources (id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                value TEXT NOT NULL);
            ''')

    @property
    def media_dir(self):
        return self.path.parent / 'media'

    @staticmethod
    def media_public(row):
        return {'id':row['id'], 'url':'/media/'+row['id'], 'kind':row['kind'], 'mime':row['mime'],
                'name':row['original_name'], 'size':row['size'], 'created':row['created']}

    def media_record(self, mid, kind=None, db=None):
        if not isinstance(mid, str) or not re.fullmatch(r'[0-9a-f]{32}', mid):
            raise ContentError('media_not_found', 404)
        if db is None:
            with self.db() as connection:
                return self.media_record(mid, kind, connection)
        row = db.execute('SELECT * FROM media WHERE id=?', (mid,)).fetchone()
        if not row or (kind is not None and row['kind'] != kind):
            raise ContentError('media_not_found', 404)
        return row

    def upload(self, stream, kind, length, original_name):
        if kind not in LIMITS:
            raise ContentError('invalid_upload_kind')
        if not 1 <= length <= LIMITS[kind]:
            raise ContentError('upload_too_large', 413)
        self.media_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        mid = secrets.token_hex(16)
        temporary = self.media_dir / (mid+'.part')
        target = None
        try:
            # A MIME declaration or file extension alone is never trusted.
            header = stream.read(min(length, 128))
            mime, ext = sniff(header, kind)
            with temporary.open('xb') as file:
                file.write(header)
                remaining = length - len(header)
                while remaining:
                    chunk = stream.read(min(65536, remaining))
                    if not chunk:
                        raise ContentError('incomplete_upload')
                    file.write(chunk)
                    remaining -= len(chunk)
            temporary.chmod(0o600)
            target = self.media_dir / (mid+ext)
            os.replace(temporary, target)
            original_name = str(original_name).replace('\\', '/').split('/')[-1]
            original_name = ''.join(c for c in original_name if ord(c) >= 32)[:180] or ('upload'+ext)
            with self.db() as db:
                db.execute('INSERT INTO media VALUES(?,?,?,?,?,?,?)', (
                    mid, kind, mime, mid+ext, original_name, length, int(time.time())))
                self.log(db, 'upload_'+kind, mid)
            return self.media_public(self.media_record(mid))
        except Exception:
            if target is not None:
                target.unlink(missing_ok=True)
            raise
        finally:
            temporary.unlink(missing_ok=True)

    def media_list(self):
        with self.db() as db:
            return [self.media_public(r) for r in db.execute('SELECT * FROM media ORDER BY created DESC,rowid DESC LIMIT 500')]

    def delete_media(self, mid):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self.media_record(mid, db=db)
            products = [json.loads(r[0]) for r in db.execute('SELECT value FROM products')]
            resources = [json.loads(r[0]) for r in db.execute('SELECT value FROM resources')]
            if any(p.get('logo_id') == mid for p in products) or any(
                    r.get('video_id') == mid or r.get('logo_id') == mid for r in resources):
                raise ContentError('media_in_use', 409)
            (self.media_dir / row['filename']).unlink(missing_ok=True)
            db.execute('DELETE FROM media WHERE id=?', (mid,))
            self.log(db, 'upload_deleted', mid)

    def resources(self, admin=False):
        with self.db() as db:
            out = []
            for row in db.execute('SELECT value FROM resources ORDER BY rowid DESC'):
                item = json.loads(row[0])
                if not admin and not item['published']:
                    continue
                if item.get('video_id'):
                    media = self.media_record(item['video_id'], 'video', db)
                    item['video_url'], item['video_mime'] = '/media/'+media['id'], media['mime']
                if item.get('logo_id'):
                    item['logo_url'] = '/media/'+item['logo_id']
                out.append(item)
            return out

    def save_resource(self, data, rid=None):
        kind = data.get('kind')
        if kind not in ('tutorial', 'tool') or type(data.get('published', True)) is not bool:
            raise ContentError('invalid_resource')
        item = {'id':rid or secrets.token_hex(8), 'kind':kind,
                'title':translations(data.get('title')), 'description':translations(data.get('description'),1000,False),
                'published':data.get('published', True), 'video_id':data.get('video_id') or None,
                'logo_id':data.get('logo_id') or None, 'download_url':'', 'updated':int(time.time())}
        if kind == 'tool':
            item['download_url'] = download_url(data.get('download_url'))
            item['video_id'] = None
        elif not item['video_id']:
            raise ContentError('video_required')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if rid:
                old = db.execute('SELECT kind FROM resources WHERE id=?', (rid,)).fetchone()
                if not old or old['kind'] != kind:
                    raise ContentError('not_found', 404)
            if item['video_id']:
                self.media_record(item['video_id'], 'video', db)
            if item['logo_id']:
                self.media_record(item['logo_id'], 'logo', db)
            if rid:
                db.execute('UPDATE resources SET value=? WHERE id=?', (json.dumps(item),rid))
            else:
                db.execute('INSERT INTO resources VALUES(?,?,?)', (item['id'],kind,json.dumps(item)))
            self.log(db, 'resource_saved', item['id'])
        return item

    def delete_resource(self, rid):
        with self.db() as db:
            if not db.execute('DELETE FROM resources WHERE id=?', (rid,)).rowcount:
                raise ContentError('not_found',404)
            self.log(db, 'resource_deleted',rid)
