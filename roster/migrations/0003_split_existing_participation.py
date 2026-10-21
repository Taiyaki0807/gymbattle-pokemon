from django.db import migrations


def split_existing(apps, schema_editor):
    Member = apps.get_model('roster', 'Member')
    Participation = apps.get_model('roster', 'Participation')
    alias = schema_editor.connection.alias
    keys = ['fire', 'water', 'electric', 'grass', 'ice', 'fighting', 'poison', 'ground', 'flying',
            'psychic', 'bug', 'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy', 'normal']
    for member in Member.objects.using(alias).all().iterator():
        for key in keys:
            physical, _ = Participation.objects.using(alias).get_or_create(
                member_id=member.pk, pokemon_type=key, category='physical',
                defaults={'status': 'no', 'condition': ''})
            Participation.objects.using(alias).get_or_create(
                member_id=member.pk, pokemon_type=key, category='special',
                defaults={'status': physical.status, 'condition': physical.condition})


class Migration(migrations.Migration):
    dependencies = [('roster', '0002_remove_participation_unique_member_type_and_more')]
    # Forward only: merging physical/special would discard independently edited data.
    operations = [migrations.RunPython(split_existing)]
