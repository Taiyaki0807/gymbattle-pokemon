from django import forms
from .models import Member, Participation


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['name', 'notes']


class ParticipationForm(forms.ModelForm):
    class Meta:
        model = Participation
        fields = ['status', 'condition']
