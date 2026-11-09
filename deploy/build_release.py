"""Package code and built frontend only. Never include local DBs, secrets or media."""
import pathlib, tarfile, sys

root=pathlib.Path(sys.argv[1]).resolve()
output=pathlib.Path(sys.argv[2]).resolve()
assert root.name in ['auto-shop','manicure','clothes-shop','conditioners']
blocked={'.venv','.local','.env','media','__pycache__','.ruff_cache'}
def filter_backend(info):
    path=pathlib.PurePosixPath(info.name)
    if any(part in blocked for part in path.parts[1:]) or path.name.startswith('db.sqlite3') or path.suffix=='.pyc':return None
    info.uid=info.gid=0;info.uname=info.gname='root'
    info.mode=0o755 if info.isdir() else 0o644
    return info
def filter_public(info):
    if info.issym() or info.islnk():return None
    info.uid=info.gid=0;info.uname=info.gname='root'
    info.mode=0o755 if info.isdir() else 0o644
    return info
with tarfile.open(output,'w:gz') as archive:
    archive.add(root/'backend',arcname='backend',filter=filter_backend)
    archive.add(root/'frontend/dist',arcname='frontend',filter=filter_public)
    for name in ['Dockerfile','compose.yaml','nginx.conf','.dockerignore','ops.sh','restore_check.py','enable_https.py']:
        archive.add(root/'deploy'/name,arcname=name)
    if root.name=='conditioners':archive.add(root/'deploy/export_demo_snapshot.py',arcname='data/export_demo_snapshot.py')
print('Prepared code-only release:',output)
