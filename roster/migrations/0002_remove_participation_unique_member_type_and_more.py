from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('roster', '0001_initial')]
    operations = [
        migrations.RemoveConstraint(model_name='participation', name='unique_member_type'),
        migrations.RemoveConstraint(model_name='participation', name='valid_status'),
        migrations.AddField(model_name='participation', name='category',
            field=models.CharField(choices=[('physical', '物理'), ('special', '特殊')], default='physical', max_length=8, verbose_name='分類')),
        migrations.AlterField(model_name='participation', name='status',
            field=models.CharField(choices=[('excellent', '◎'), ('yes', '〇'), ('conditional', '△'), ('no', '×')], default='no', max_length=11, verbose_name='参加可否')),
        migrations.AlterField(model_name='participation', name='pokemon_type',
            field=models.CharField(choices=[('fire', 'ほのお'), ('water', 'みず'), ('electric', 'でんき'),
                ('grass', 'くさ'), ('ice', 'こおり'), ('fighting', 'かくとう'), ('poison', 'どく'),
                ('ground', 'じめん'), ('flying', 'ひこう'), ('psychic', 'エスパー'), ('bug', 'むし'),
                ('rock', 'いわ'), ('ghost', 'ゴースト'), ('dragon', 'ドラゴン'), ('dark', 'あく'),
                ('steel', 'はがね'), ('fairy', 'フェアリー'), ('normal', 'ノーマル')], max_length=10, verbose_name='タイプ')),
        migrations.AddConstraint(model_name='participation', constraint=models.UniqueConstraint(
            fields=['member', 'pokemon_type', 'category'], name='unique_member_type_category')),
        migrations.AddConstraint(model_name='participation', constraint=models.CheckConstraint(
            condition=models.Q(status__in=['excellent', 'yes', 'conditional', 'no']), name='valid_status')),
        migrations.AddConstraint(model_name='participation', constraint=models.CheckConstraint(
            condition=models.Q(category__in=['physical', 'special']), name='valid_category')),
    ]
