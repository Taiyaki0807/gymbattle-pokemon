from pathlib import Path
from uuid import uuid4
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


def icon_path(instance, filename):
    return f'icons/{uuid4().hex}{Path(filename).suffix.lower()}'


def validate_icon(value):
    if value.size > 2 * 1024 * 1024:
        raise ValidationError('画像は2MB以下にしてください。')
    try:
        value.seek(0)
        with Image.open(value) as image:
            if image.format not in {'PNG', 'JPEG', 'WEBP'}:
                raise ValidationError('PNG・JPEG・WebPの画像を指定してください。')
            if image.width > 1024 or image.height > 1024:
                raise ValidationError('縦・横ともに1024ピクセル以下にしてください。')
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValidationError('画像を読み込めません。別の画像を選択してください。')
    finally:
        value.seek(0)
