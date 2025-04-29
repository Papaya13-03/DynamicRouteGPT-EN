def load_prompt(file_path, **kwargs):
    with open(file_path, 'r', encoding='utf-8') as f:
        template = f.read()
    return template.format(**kwargs)