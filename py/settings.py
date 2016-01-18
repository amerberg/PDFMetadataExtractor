from yaml import load
from os import path


def default_settings_file():
    return path.abspath("../settings.yml")


def load_settings(filename=None):
    if filename is None:
        filename = default_settings_file()

    with open(filename, "r") as f:
        return load(f)
