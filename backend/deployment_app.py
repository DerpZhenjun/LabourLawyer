"""Same-origin web/API deployment factory; no service starts during import."""
import os
from pathlib import Path

from fastapi import Depends, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Match

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_LOOPBACK_ORIGIN = r'\Ahttp://127\.0\.0\.1:(?:[1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])\Z'


def configure_desktop_cors(application):
    """Allow Electron's ephemeral HTTP loopback origin before the stack is built."""
    if application.middleware_stack is not None:
        raise RuntimeError('Deployment CORS must be configured before application startup')
    for middleware in application.user_middleware:
        if middleware.cls is CORSMiddleware:
            middleware.kwargs['allow_origin_regex'] = DESKTOP_LOOPBACK_ORIGIN
            return
    raise RuntimeError('Deployment requires the existing application CORS middleware')


class FrontendRoute(APIRoute):
    def matches(self, scope):
        path = scope.get('path', '')
        if path == '/api' or path.startswith('/api/') or path == '/health' or path.startswith('/health/'):
            return Match.NONE, {}
        return super().matches(scope)


def defer_collection_routes(application):
    """Windows acquisition jobs lack a persistent Linux runtime in this release."""
    from auth_dependencies import require_admin
    async def unavailable():
        raise HTTPException(503, '此部署尚未配置持久化采集运行环境，暂不能启动采集任务。')
    for index, route in enumerate(application.router.routes):
        path = getattr(route, 'path', '')
        if (path == '/api/portal-reports' or path.startswith('/api/portal-reports/')) and 'POST' in getattr(route, 'methods', set()):
            application.router.routes[index] = APIRoute(path, unavailable, methods=['POST'], dependencies=[Depends(require_admin)], dependency_overrides_provider=application, include_in_schema=False)


def attach_frontend(application, directory):
    directory = Path(directory).resolve()
    if not (directory / 'index.html').is_file():
        raise ValueError('A verified frontend build with index.html is required')
    # The development root status response becomes the deployed website.
    application.router.routes[:] = [route for route in application.router.routes if getattr(route, 'path', None) != '/']

    async def frontend(resource: str, request: Request):
        parts = resource.split('/')
        if (resource == 'api' or resource.startswith('api/') or resource == 'health'
                or resource.startswith('health/') or any(part.startswith('.') for part in parts)):
            raise HTTPException(404, 'Not Found')
        candidate = (directory / resource).resolve()
        if not candidate.is_relative_to(directory):
            raise HTTPException(404, 'Not Found')
        if candidate.is_file():
            response = FileResponse(candidate)
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable' if resource.startswith('assets/') else 'no-cache'
            return response
        # Missing compiled assets and API paths must never become successful HTML.
        if resource and (Path(resource).suffix or 'text/html' not in request.headers.get('accept', '')):
            raise HTTPException(404, 'Not Found')
        return FileResponse(directory / 'index.html', headers={'Cache-Control': 'no-cache'})
    # API routes never match this fallback, preserving the router's original
    # 404 for unknown paths and 405 for wrong methods on existing endpoints.
    application.router.routes.append(FrontendRoute('/{resource:path}', frontend, methods=['GET', 'HEAD'], include_in_schema=False))
    return application


def create_app():
    raw = os.environ.get('LABOURLAWYER_DEPLOY_DATA')
    if not raw:
        raise RuntimeError('LABOURLAWYER_DEPLOY_DATA must name the application-owned persistent directory')
    data = Path(raw).expanduser().resolve()
    if data == ROOT or data.is_relative_to(ROOT):
        raise ValueError('Persistent data must be outside the immutable release directory')
    data.mkdir(parents=True, exist_ok=True)
    os.environ.update({
        'LABOURLAWYER_DATA_DIR': str(data / 'private'),
        'LABOURLAWYER_AUTH_DB': str(data / 'private/auth.sqlite3'),
        'LABOURLAWYER_REGIONAL_DB': str(data / 'public/regional-guides.sqlite'),
        'LABOURLAWYER_DIRECTORY_DB': str(data / 'public/regional-directory.sqlite'),
        'PYTHONDONTWRITEBYTECODE': '1',
    })
    # Import only after every database destination has been configured.
    from public_seed import bootstrap_public_data
    bootstrap_public_data(ROOT, data_dir=data / 'public')
    from app import app
    configure_desktop_cors(app)
    defer_collection_routes(app)
    return attach_frontend(app, ROOT / 'frontend/dist')
