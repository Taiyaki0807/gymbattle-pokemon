from django.db import models
from .constants import TYPES


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
        YES = 'yes', '可'
        CONDITIONAL = 'conditional', '条件付き'
        NO = 'no', '不可'

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='participations')
    pokemon_type = models.CharField('タイプ', max_length=10, choices=TYPES)
    status = models.CharField('参加可否', max_length=11, choices=Status.choices, default=Status.NO)
    condition = models.CharField('条件・メモ', max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['member', 'pokemon_type'], name='unique_member_type'),
            models.CheckConstraint(condition=models.Q(pokemon_type__in=[key for key, _ in TYPES]), name='valid_pokemon_type'),
            models.CheckConstraint(condition=models.Q(status__in=['yes', 'conditional', 'no']), name='valid_status'),
        ]
