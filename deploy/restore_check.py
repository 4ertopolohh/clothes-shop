"""Restore a project backup into a disposable database in that project's DB container."""
import subprocess, pathlib, sys, json

base = pathlib.Path.cwd().resolve()
name = base.name
assert str(base) == '/srv/webprojects/' + name
assert name in ['auto-shop','manicure','clothes-shop','conditioners']
backup = max((base/'backups').iterdir(), key=lambda path:path.name)
temporary = name.replace('-','_') + '_restorecheck'
def compose(*args, **kwargs):
    return subprocess.run(['docker','compose',*args], check=True, **kwargs)
hash_code = '''
import psycopg, os, json
from psycopg import sql
c=psycopg.connect(host='db',dbname=os.environ['POSTGRES_DB'],user=os.environ['POSTGRES_USER'],password=os.environ['POSTGRES_PASSWORD'])
cur=c.cursor();cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
tables=[row[0] for row in cur.fetchall()];result={}
for table in tables:
 cur.execute(sql.SQL("SELECT count(*), md5(COALESCE(string_agg(j, E'\\n' ORDER BY j), '')) FROM (SELECT row_to_json(t)::text j FROM {} t) x").format(sql.Identifier(table)))
 result[table]=cur.fetchone()
print(json.dumps(result,sort_keys=True));c.close()
'''
def fingerprint(database=None):
    args=['run','--rm','--no-deps']
    if database: args += ['-e','POSTGRES_DB='+database]
    output=compose(*args,'backend','python','-c',hash_code,capture_output=True,text=True).stdout
    return json.loads(output.strip().splitlines()[-1])
created=False
compose('stop','web','backend')
try:
    original=fingerprint()
    compose('exec','-T','db','sh','-c','createdb -U "$POSTGRES_USER" '+temporary)
    created=True
    with (backup/'database.dump').open('rb') as source:
        compose('exec','-T','db','sh','-c','pg_restore -U "$POSTGRES_USER" -d '+temporary+' --no-owner --no-acl --exit-on-error',stdin=source)
    restored=fingerprint(temporary)
    differences=[table for table in original.keys() | restored.keys() if original.get(table)!=restored.get(table)]
    result={'project':name,'backup':str(backup),'tables':len(original),'rows':sum(value[0] for value in original.values()),'differences':differences,'restored_into_disposable_database':True}
    (base/'data/restore-verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    if differences:raise RuntimeError('Backup differs from current database')
finally:
    if created:compose('exec','-T','db','sh','-c','dropdb -U "$POSTGRES_USER" '+temporary)
    compose('up','-d','backend','web')
