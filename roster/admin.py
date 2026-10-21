from django.contrib import admin
from .models import Member, Participation, HeaderIcon
from django.utils.html import format_html


@admin.register(HeaderIcon)
class HeaderIconAdmin(admin.ModelAdmin):
    list_display = ['key', 'preview']
    readonly_fields = ['preview']

    @admin.display(description='プレビュー')
    def preview(self, obj):
        if obj and obj.image:
            return format_html('<img src="{}" width="32" height="32" style="object-fit:contain" alt="{}">',
                               obj.image.url, obj.get_key_display())
        return '未登録'

class ParticipationInline(admin.TabularInline):
    model = Participation
    extra = 0

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'updated_at']
    search_fields = ['name']
    inlines = [ParticipationInline]
