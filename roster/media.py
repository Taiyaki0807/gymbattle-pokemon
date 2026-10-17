import mimetypes
from pathlib import Path
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


@never_cache
@login_required
@require_safe
def member_image(request, path):
    root = Path(settings.MEDIA_ROOT).resolve()
    try:
        image = (root / path).resolve()
        if not image.is_relative_to(root) or not image.is_file():
            raise Http404
        stream = image.open('rb')
    except (OSError, ValueError, RuntimeError):
        raise Http404
    return FileResponse(stream, content_type=mimetypes.guess_type(image.name)[0] or 'application/octet-stream')
