from django.contrib import admin
from .models import Member, Participation

class ParticipationInline(admin.TabularInline):
    model = Participation
    extra = 0

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'updated_at']
    search_fields = ['name']
    inlines = [ParticipationInline]
