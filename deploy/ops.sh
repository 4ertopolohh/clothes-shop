#!/usr/bin/env bash
set -Eeuo pipefail
base=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
name=${base##*/}
case "$name" in auto-shop|manicure|clothes-shop|conditioners) ;; *) echo 'Unexpected project directory'; exit 1;; esac
[[ "$base" == "/srv/webprojects/$name" ]] || { echo 'Unexpected absolute path'; exit 1; }
cd "$base"
compose() { docker compose --project-name "$name" --project-directory "$base" "$@"; }
backup() {
  mkdir -p "$base/backups"
  local destination
  destination=$(mktemp -d "$base/backups/$(date -u +%Y%m%dT%H%M%SZ).XXXXXX")
   chmod 700 "$base/backups" "$destination"
  compose stop web backend
  trap 'compose up -d backend web' EXIT
  compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl' > "$destination/database.dump"
  tar --exclude='data/source*' -czf "$destination/project.tar.gz" .env compose.yaml Dockerfile .dockerignore nginx.conf backend frontend data ops.sh restore_check.py enable_https.py
  cp "/etc/nginx/sites-available/$name.nemida-studio.com" "$destination/host-nginx.conf"
  chmod 600 "$destination/database.dump" "$destination/project.tar.gz" "$destination/host-nginx.conf"
  sha256sum "$destination/database.dump" "$destination/project.tar.gz" > "$destination/SHA256SUMS"
  compose up -d backend web
  trap - EXIT
  echo "$destination"
}
case "${1:-help}" in
  start) compose up -d ;;
  stop) compose stop ;;
  status) compose ps ;;
  check-backup) python3 "$base/restore_check.py" ;;
  logs) compose logs --tail=200 -f ;;
  backup) backup ;;
  update)
    backup
    compose build backend
    compose run --rm backend python manage.py migrate --noinput
    compose run --rm backend python manage.py collectstatic --noinput
    compose up -d --force-recreate backend web
    ;;
  restore)
    snapshot=$(realpath -e -- "${2:?Supply the absolute backup directory}")
    [[ "$snapshot" == "$base/backups/"* ]] || { echo 'Backup must belong to this project'; exit 1; }
    [[ "${3:-}" == "--confirm=$name" ]] || { echo "Requires --confirm=$name"; exit 1; }
    sha256sum -c "$snapshot/SHA256SUMS"
    backup
    compose stop web backend
    tar -xzf "$snapshot/project.tar.gz" -C "$base"
    compose up -d db
    compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-acl --exit-on-error' < "$snapshot/database.dump"
    compose up -d --build backend web
    echo 'Restored application and database. Host Nginx backup is supplied separately for reviewed restoration.'
    ;;
  remove)
    echo "Resources: directory $base; Compose project $name; volume ${name}_postgres; networks ${name}_default and ${name}_ingress; Nginx $name.nemida-studio.com; image $name-backend:latest"
    [[ "${2:-}" == "--confirm=$name" ]] || { echo "Requires --confirm=$name"; exit 1; }
    for volume in $(docker volume ls -q --filter "label=com.docker.compose.project=$name"); do
      [[ "$volume" == "${name}_postgres" ]] || { echo 'Unexpected volume; aborting'; exit 1; }
    done
    available="/etc/nginx/sites-available/$name.nemida-studio.com"
    enabled="/etc/nginx/sites-enabled/$name.nemida-studio.com"
    if [[ -L "$enabled" ]]; then
      unlink "$enabled"
      if ! nginx -t; then ln -s "$available" "$enabled"; exit 1; fi
      systemctl reload nginx
    fi
    compose down --volumes --remove-orphans
    if docker image inspect "$name-backend:latest" >/dev/null 2>&1; then docker image rm "$name-backend:latest"; fi
    if [[ -f "/etc/letsencrypt/renewal/$name.nemida-studio.com.conf" ]]; then certbot delete --non-interactive --cert-name "$name.nemida-studio.com"; fi
    rm -f -- "$available"
    cd /srv/webprojects
    [[ ! -L "$base" && "$(realpath -e -- "$base")" == "/srv/webprojects/$name" ]] || exit 1
    rm -rf --one-file-system -- "$base"
    ;;
  *) echo "Usage: $0 {start|stop|status|logs|backup|update|restore BACKUP --confirm=$name|remove --confirm=$name}" ;;
esac
