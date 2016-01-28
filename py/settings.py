import yaml, pickle
import os


def default_settings_file():
    return os.path.abspath("../settings.yml")


def load_settings(filename=None):
    if filename is None:
        filename = default_settings_file()

    with open(filename, "r") as f:
        settings=yaml.load(f)

    for name in settings['fields']:
        if 'model_file' in settings['fields'][name]:
            fn = os.path.join(resolve_path(settings['model_directory'], filename),
                              settings['fields'][name]['model_file'])
            with open(fn, 'rb') as f:
                settings['fields'][name]['model'] = pickle.load(f)

    return settings

def load_dictionary(settings):
    try:
        with open(settings['dictionary'], "r") as f:
            words = f.readlines()
            return [w.strip() for w in words if w.islower()]
    except Exception:
        return []


def load_labels(filename):
    with open(filename, "r") as f:
        return yaml.load(f)

def resolve_path(filename, settings_filename):
    if not os.path.isabs(filename):
        return os.path.join(os.path.split(settings_filename)[0],
                               filename)
    else:
        return filename

