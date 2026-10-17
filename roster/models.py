from django.db import models
from .constants import TYPES, CATEGORIES, HEADER_IMAGE_CHOICES
from django.core.validators import FileExtensionValidator
from .images import icon_path, validate_icon


class HeaderIcon(models.Model):
    key = models.CharField('表示先', max_length=20, unique=True, choices=HEADER_IMAGE_CHOICES)
    image = models.ImageField('キャラ・タイプ画像', upload_to=icon_path,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'webp']), validate_icon],
        help_text='PNG・JPEG・WebP／2MB以下／縦横1024px以下。正方形・透過PNG推奨。')

    class Meta:
        verbose_name = 'キャラ・タイプ画像'
        verbose_name_plural = 'キャラ・タイプ画像'
        ordering = ['key']

    def __str__(self):
        return self.get_key_display()


class Member(models.Model):
    name = models.CharField('メンバー名', max_length=60, unique=True)
    notes = models.TextField('メモ', blank=True, max_length=1000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'pk']
        verbose_name = 'メンバー'

    def __str__(self):
        return self.name


class Participation(models.Model):
    class Status(models.TextChoices):
        EXCELLENT = 'excellent', '◎'
        YES = 'yes', '〇'
        CONDITIONAL = 'conditional', '△'
        NO = 'no', '×'
        UNSET = 'unset', '-'

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='participations')
    pokemon_type = models.CharField('タイプ', max_length=10, choices=TYPES)
    category = models.CharField('分類', max_length=8, choices=CATEGORIES, default='physical')
    status = models.CharField('参加可否', max_length=11, choices=Status.choices, default=Status.NO)
    condition = models.CharField('条件・メモ', max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['member', 'pokemon_type', 'category'], name='unique_member_type_category'),
            models.CheckConstraint(condition=models.Q(pokemon_type__in=[key for key, _ in TYPES]), name='valid_pokemon_type'),
            models.CheckConstraint(condition=models.Q(status__in=['excellent', 'yes', 'conditional', 'no', 'unset']), name='valid_status'),
            models.CheckConstraint(condition=models.Q(category__in=['physical', 'special']), name='valid_category'),
        ]
