""" Common configuration constants
"""

PROJECTNAME = "atreal.usersinout"

CSV_HEADER = [
    'username',
    'password',
    'roles',
    'email',
    'fullname',
    'cpf',
    'occupation',
    'state',
    'uf',
    'city',
    'groups',
    'datanascimento',
    'sexo',
    'cor_raca',
    'rg',
    'orgaoexpedidor',
    'fonecelular',
    'contato_emergencia',
    'modalidade',
    'categoria',
    'estadovivencia',
    'regiao_vivencia',
    'curso_graduacao',
    'universidade',
    'cidade_universitaria',
    'semestre',
    'enfase_residencia',
    'escolaridade',
    # 'location',
    # 'description',
    # 'home_page',
    # 'wysiwyg_editor',
    # 'ext_editor',
    # 'listed',
]

MEMBER_PROPERTIES = [
    'username',
    'password',
    'roles',
    'email',
    'fullname',
    'cpf',
    'occupation',
    'state',
    'city',
    'groups',
    # 'location',
    # 'description',
    # 'home_page',
    # 'wysiwyg_editor',
    # 'ext_editor',
    # 'listed',
]

VERSUS_CADASTRO = [
    ('title', 'fullname'),
    ('datanascimento', 'datanascimento'),
    ('sexo', 'sexo'),
    ('cor_raca', 'cor_raca'),
    ('rg', 'rg'),
    ('orgaoexpedidor', 'orgaoexpedidor'),
    ('cpf', 'cpf'),
    ('versus_uf', 'uf'),
    ('versus_cidade', 'city'),
    ('fonecelular', 'fonecelular'),
    ('contato_emergencia', 'contato_emergencia'),
]

VERSUS_FORM_VIVENCIA = [
    ('categoria', 'categoria'),
    ('enfase_residencia', 'enfase_residencia'),
    ('cursograduacao', 'curso_graduacao'),
    ('universidade_drop_down', 'universidade'),
    ('cidadeuniversitaria', 'cidade_universitaria'),
    ('semestre', 'semestre'),
    ('escolaridade', 'escolaridade'),
]

