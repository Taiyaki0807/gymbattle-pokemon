from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from .constants import TYPES, CATEGORIES
from .forms import MemberForm, ParticipationForm
from .models import Member, Participation, HeaderIcon


def wants_json(request):
    return 'application/json' in request.headers.get('Accept', '')


def saved(request, member, text):
    if wants_json(request):
        return JsonResponse({'message': text, 'id': member.pk, 'name': member.name})
    messages.success(request, text)
    return redirect(reverse('roster:list') + f'#member-{member.pk}')


def invalid(request, form):
    if wants_json(request):
        return JsonResponse({'errors': form.errors}, status=400)
    messages.error(request, '保存できませんでした。' + ' '.join(str(error) for errors in form.errors.values() for error in errors))
    return redirect('roster:list')


@login_required
def member_list(request):
    query = request.GET.get('q', '').strip()
    selected_types = set(request.GET.getlist('type')) & set(dict(TYPES))
    visible_types = tuple((key, label) for key, label in TYPES if not selected_types or key in selected_types)
    selected_status = request.GET.get('status', '')
    selected_category = request.GET.get('category', '')
    selected_status = selected_status if selected_status in Participation.Status.values else ''
    selected_category = selected_category if selected_category in dict(CATEGORIES) else ''
    members = Member.objects.all()
    if query:
        members = members.filter(name__icontains=query)
    filters = {key: value for key, value in [('status', selected_status),
                                           ('category', selected_category)] if value}
    if filters:
        if selected_types:
            filters['pokemon_type__in'] = selected_types
        members = members.filter(pk__in=Participation.objects.filter(**filters).values('member_id'))
    rows = []
    icon_urls = {icon.key: icon.image.url for icon in HeaderIcon.objects.all() if icon.image}
    type_headers = [{'key': key, 'label': label, 'icon_url': icon_urls.get(key, ''),
                     'categories': [{'key': category, 'label': category_label,
                                     'icon_url': icon_urls.get(f'{key}_{category}', icon_urls.get(category, ''))}
                                    for category, category_label in CATEGORIES]}
                    for key, label in visible_types]
    for member in members.prefetch_related('participations'):
        mapping = {(p.pokemon_type, p.category): p for p in member.participations.all()}
        cells = []
        for key, label in visible_types:
            for category, category_label in CATEGORIES:
                record = mapping.get((key, category))
                cells.append({'key': key, 'label': label, 'category': category, 'category_label': category_label,
                              'status': record.status if record else 'no', 'condition': record.condition if record else ''})
        rows.append({'member': member, 'cells': cells})
    return render(request, 'roster/list.html', {'rows': rows, 'types': visible_types, 'all_types': TYPES,
        'categories': CATEGORIES, 'table_colspan': len(visible_types) * 2 + 2,
        'type_headers': type_headers,
        'statuses': Participation.Status.choices, 'q': query, 'selected_types': selected_types,
        'selected_status': selected_status, 'selected_category': selected_category, 'total': Member.objects.count()})


@login_required
@require_http_methods(['GET', 'POST'])
def member_create(request):
    if request.method == 'GET':
        return redirect('roster:list')
    try:
        with transaction.atomic():
            number = (Member.objects.aggregate(value=Max('pk'))['value'] or 0) + 1
            while Member.objects.filter(name=f'メンバー{number}').exists():
                number += 1
            member = Member.objects.create(name=f'メンバー{number}')
            Participation.objects.bulk_create([Participation(member=member, pokemon_type=key, category=category)
                for key, _ in TYPES for category, _ in CATEGORIES])
    except IntegrityError:
        return JsonResponse({'errors': {'name': ['追加が重なりました。もう一度＋を押してください。']}}, status=409)
    return saved(request, member, 'メンバーを追加しました。表の名前と記号を編集してください。')


@login_required
@require_http_methods(['GET', 'POST'])
def member_edit(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == 'GET':
        return redirect(reverse('roster:list') + f'#member-{member.pk}')
    form = MemberForm(request.POST, instance=member)
    if not form.is_valid():
        return invalid(request, form)
    try:
        with transaction.atomic():
            member = form.save()
    except IntegrityError:
        form.add_error('name', '同じ名前のメンバーがいます。')
        return invalid(request, form)
    return saved(request, member, 'メンバー情報を保存しました。')


@login_required
@require_POST
def participation_edit(request, pk, pokemon_type, category):
    if pokemon_type not in dict(TYPES) or category not in dict(CATEGORIES):
        raise Http404
    member = get_object_or_404(Member, pk=pk)
    form = ParticipationForm(request.POST)
    if not form.is_valid():
        return invalid(request, form)
    with transaction.atomic():
        Participation.objects.update_or_create(member=member, pokemon_type=pokemon_type, category=category,
            defaults=form.cleaned_data)
    return saved(request, member, '記号とメモを保存しました。')


@login_required
@require_http_methods(['GET', 'POST'])
def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        member.delete()
        messages.success(request, 'メンバーを削除しました。')
        return redirect('roster:list')
    return render(request, 'roster/delete.html', {'member': member})
