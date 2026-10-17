TYPES = (
    ('fire', 'ほのお'), ('water', 'みず'), ('electric', 'でんき'),
    ('grass', 'くさ'), ('ice', 'こおり'), ('fighting', 'かくとう'), ('poison', 'どく'),
    ('ground', 'じめん'), ('flying', 'ひこう'), ('psychic', 'エスパー'), ('bug', 'むし'),
    ('rock', 'いわ'), ('ghost', 'ゴースト'), ('dragon', 'ドラゴン'), ('dark', 'あく'),
    ('steel', 'はがね'), ('fairy', 'フェアリー'), ('normal', 'ノーマル'),
)

CATEGORIES = (('physical', '物理'), ('special', '特殊'))

HEADER_IMAGE_CHOICES = (
    ('タイプ名の横', TYPES),
    ('タイプ別・物理／特殊のキャラ', tuple(
        (f'{key}_{category}', f'{label}・{category_label}')
        for key, label in TYPES for category, category_label in CATEGORIES)),
    ('以前の共通画像（個別画像がない場合）', (
        ('physical', '共通の物理'), ('special', '共通の特殊'))),
)
