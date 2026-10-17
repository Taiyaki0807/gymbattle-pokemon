from django import forms
from django.db import transaction
from .constants import TYPES
from .models import Member, Participation


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['name', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        existing = {p.pokemon_type: p for p in self.instance.participations.all()} if self.instance.pk else {}
        for key, label in TYPES:
            record = existing.get(key)
            self.fields[f'status_{key}'] = forms.ChoiceField(label=label, choices=Participation.Status.choices,
                initial=record.status if record else Participation.Status.NO)
            self.fields[f'condition_{key}'] = forms.CharField(label=f'{label}の条件・メモ', max_length=200,
                required=False, initial=record.condition if record else '',
                widget=forms.TextInput(attrs={'placeholder': '例：特定のバディーズ編成時'}))

    @property
    def type_fields(self):
        return [(label, self[f'status_{key}'], self[f'condition_{key}']) for key, label in TYPES]

    @transaction.atomic
    def save(self):
        member = super().save()
        for key, _ in TYPES:
            Participation.objects.update_or_create(member=member, pokemon_type=key, defaults={
                'status': self.cleaned_data[f'status_{key}'], 'condition': self.cleaned_data[f'condition_{key}']})
        return member
