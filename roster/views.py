from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .constants import TYPES
from .forms import MemberForm
from .models import Member, Participation


@login_required
def member_list(request):
    query = request.GET.get('q', '').strip()
    selected_type = request.GET.get('type', '')
    selected_status = request.GET.get('status', '')
    if selected_type not in dict(TYPES):
        selected_type = ''
    if selected_status not in Participation.Status.values:
        selected_status = ''
    members = Member.objects.all()
    if query:
        members = members.filter(name__icontains=query)
    if selected_type or selected_status:
        filters = {}
        if selected_type:
            filters['pokemon_type'] = selected_type
        if selected_status:
            filters['status'] = selected_status
        members = members.filter(pk__in=Participation.objects.filter(**filters).values('member_id'))
    rows = []
    for member in members.prefetch_related('participations'):
        mapping = {p.pokemon_type: p for p in member.participations.all()}
        cells = [mapping.get(key) for key, _ in TYPES]
        rows.append({'member': member, 'cells': cells, 'available': sum(p.status == 'yes' for p in mapping.values())})
    return render(request, 'roster/list.html', {'rows': rows, 'types': TYPES, 'statuses': Participation.Status.choices,
        'q': query, 'selected_type': selected_type, 'selected_status': selected_status, 'total': Member.objects.count()})


@login_required
@require_http_methods(['GET', 'POST'])
def member_edit(request, pk=None):
    member = get_object_or_404(Member, pk=pk) if pk is not None else None
    form = MemberForm(request.POST if request.method == 'POST' else None, instance=member)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'メンバー情報を保存しました。')
        return redirect('roster:list')
    return render(request, 'roster/form.html', {'form': form, 'member': member})


@login_required
@require_http_methods(['GET', 'POST'])
def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        member.delete()
        messages.success(request, 'メンバーを削除しました。')
        return redirect('roster:list')
    return render(request, 'roster/delete.html', {'member': member})
