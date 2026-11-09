import pathlib, subprocess, sys, shutil

name = sys.argv[1]
names = ['auto-shop', 'manicure', 'clothes-shop', 'conditioners']
if name not in names: raise SystemExit('Unknown project')
base = pathlib.Path('/srv/webprojects') / name
domain = name + '.nemida-studio.com'
port = 18100 + names.index(name)
subprocess.run(['certbot', 'certonly', '--webroot', '-w', str(base/'acme'), '-d', domain, '--cert-name', domain, '--non-interactive', '--agree-tos', '--register-unsafely-without-email', '--deploy-hook', 'nginx -t && systemctl reload nginx'], check=True)
config = pathlib.Path('/etc/nginx/sites-available') / domain
previous = config.read_text()
(base/'host-nginx.pre-https.conf').write_text(previous)
config.write_text(f'''server {{
 listen 80;
 server_name {domain};
 location ^~ /.well-known/acme-challenge/ {{ root {base}/acme; }}
 location / {{ return 301 https://$host$request_uri; }}
}}
server {{
 listen 443 ssl http2;
 server_name {domain};
 ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
 ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
 ssl_protocols TLSv1.2 TLSv1.3;
 client_max_body_size 40m;
 location / {{
  proxy_pass http://127.0.0.1:{port};
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
 }}
}}
''')
if subprocess.run(['nginx','-t']).returncode:
    config.write_text(previous)
    raise SystemExit('Invalid Nginx configuration restored; no reload performed')
subprocess.run(['systemctl','reload','nginx'], check=True)
env = base/'.env'
env.write_text(env.read_text().replace('HTTPS_ENABLED=0', 'HTTPS_ENABLED=1'))
env.chmod(0o600)
print('HTTPS configured for', domain)

