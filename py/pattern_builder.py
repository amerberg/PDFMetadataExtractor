class PatternBuilder(object):
    """Class for building and caching patterns"""
    def __init__(self, substitutions):
        """Store allowed substitutions and initialize the cache.

        :param substitutions: A dict of lists. Each key is a character, and
        each value is a list of strings which might be substituted for that
        character.
        """
        self._substitutions = substitutions
        self._char_patterns = {}
        self._string_patterns = {}
        self._list_patterns = {}

    def character_pattern(self, character):
        """Get a pattern to match a given character."""
        try:
            return self._char_patterns[character]
        except KeyError:
            substitutions = self._substitutions[character]
            strings = [str(c) for c in (substitutions + [character])]
            self._char_patterns[character] = "(?:" + "|".join(
                [s if len(s) == 1 else "(?:" + s + ")" for s in strings]) + ")"
            return self._char_patterns[character]

    def string_pattern(self, string):
        """Get a pattern to match a given string."""
        try:
            return self._string_patterns[string]
        except KeyError:
            substitutions = self._substitutions
            self._string_patterns[string] = "\s*".join([c if c not in substitutions
                    else self.character_pattern(c)
                    for c in string])
            return self._string_patterns[string]

    def list_pattern(self, strings):
        """Get a pattern to match one string in a list"""
        try:
            # TODO: not the best way to hash a list of strings, but it works for now
            key = "$".join(strings)
            return self._list_patterns[key]
        except KeyError:
            strings = set(strings + [string.upper() for string in strings])
            self._list_patterns[key] = "|".join(["(?:" + self.string_pattern(string) + ")"
                for string in strings])
            return self._list_patterns[key]
