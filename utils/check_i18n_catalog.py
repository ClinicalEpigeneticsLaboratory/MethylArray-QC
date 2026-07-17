#!/usr/bin/env python3
"""Static integrity checks for the bin/i18n.py message catalog.

The pipeline's nf-tests all run in stub mode, so no test ever executes the
plot/report scripts and a defective translation (a typo'd placeholder, a key
present in one language only, an unclosed <a> tag) would reach the rendered
report unnoticed. These checks close that gap without a container or a new
dependency: the catalog is plain data, so its invariants can be verified by
importing it directly.

Checked, for every non-default language against English:

* key parity      - both catalogs define exactly the same message ids, so no
                    key silently falls back to English.
* placeholders    - each translation uses the same {placeholder} set as its
                    English counterpart, so t(key, lang, **fmt) cannot raise
                    KeyError/IndexError at report time.
* markup          - HTML tags in a translation are balanced and match the
                    English tag multiset; Jinja autoescaping is off, so catalog
                    values are trusted HTML and broken markup corrupts the page.

The supported-language list is also cross-checked against the report_language
enum in nextflow_schema.json: the schema is what rejects a bad --report_language
at launch, so a language added to one and not the other would either be
unreachable or accepted with no catalog behind it.

Run via `make i18n_check`. Exits 0 when the catalog is clean, 1 otherwise,
listing every problem found rather than stopping at the first.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "nextflow_schema.json"

# The catalog lives in bin/, which is on the container PATH at run time but not
# on sys.path here; add it so this script works from a plain checkout.
sys.path.insert(0, str(REPO_ROOT / "bin"))

# pylint's import graph cannot follow the sys.path.insert above, hence import-error.
import i18n  # noqa: E402  pylint: disable=wrong-import-position,import-error

# {placeholder} / {placeholder:spec}, ignoring the {{ }} escapes for literal braces.
PLACEHOLDER_RE = re.compile(r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)(?::[^}]*)?\}(?!\})")
# Opening/closing tags; self-closing (<br>, <br/>) carry no nesting obligation.
TAG_RE = re.compile(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9]*)[^>]*?(/?)\s*>")
VOID_TAGS = {"br", "hr", "img", "input", "meta", "link"}
# Tags whose end tag is optional in HTML5: the catalog's list markup relies on
# this (e.g. "<ul><li>a<ul>..</ul><li>b</li></ul>"), where a <li> is closed
# implicitly by the next <li> or by the parent </ul>. Treating these as strictly
# nested would flag valid, browser- and WeasyPrint-correct markup.
OPTIONAL_END_TAGS = {
    "li",
    "p",
    "dt",
    "dd",
    "td",
    "th",
    "tr",
    "option",
    "thead",
    "tbody",
}


def placeholders(text):
    """Return the multiset of {placeholder} names used in a catalog value."""
    return Counter(PLACEHOLDER_RE.findall(text))


def tags(text):
    """Return the multiset of non-void tag names used in a catalog value."""
    found = Counter()
    for closing, name, self_closing in TAG_RE.findall(text):
        name = name.lower()
        if name in VOID_TAGS or self_closing:
            continue
        found[f"{'/' if closing else ''}{name}"] += 1
    return found


def unbalanced(text):
    """Return tag nesting errors, honouring HTML5's optional end tags.

    Elements in OPTIONAL_END_TAGS are closed implicitly by a sibling of the same
    name or by their parent's end tag, so only genuinely broken nesting (a stray
    end tag, or a normal element left open) is reported.
    """
    stack, broken = [], []
    for closing, name, self_closing in TAG_RE.findall(text):
        name = name.lower()
        if name in VOID_TAGS or self_closing:
            continue
        if closing:
            # A parent's end tag implicitly closes any optional-end children.
            while stack and stack[-1] != name and stack[-1] in OPTIONAL_END_TAGS:
                stack.pop()
            if stack and stack[-1] == name:
                stack.pop()
            else:
                broken.append(f"</{name}> without a matching <{name}>")
        else:
            # A sibling of the same name implicitly closes the open one.
            if name in OPTIONAL_END_TAGS and stack and stack[-1] == name:
                stack.pop()
            stack.append(name)
    # Anything still open with a mandatory end tag is a genuine error.
    return broken + [
        f"<{name}> never closed" for name in stack if name not in OPTIONAL_END_TAGS
    ]


def check_value(key, src, dst, lang, base):
    """Compare one translated value against its English source."""
    problems = []

    src_ph, dst_ph = placeholders(src), placeholders(dst)
    if src_ph != dst_ph:
        detail = []
        missing = sorted((src_ph - dst_ph).elements())
        extra = sorted((dst_ph - src_ph).elements())
        if missing:
            detail.append(f"missing {missing}")
        if extra:
            # The dangerous direction: t() passes only the kwargs the call site
            # knows about, so an unexpected placeholder raises KeyError.
            detail.append(f"unexpected {extra}")
        problems.append(f"[{lang}] placeholder mismatch in {key}: " + ", ".join(detail))

    problems += [
        f"[{lang}] broken markup in {key}: {issue}" for issue in unbalanced(dst)
    ]

    src_tags, dst_tags = tags(src), tags(dst)
    if src_tags != dst_tags:
        problems.append(
            f"[{lang}] markup differs from {base} in {key}: "
            f"{base}={dict(src_tags)} vs {lang}={dict(dst_tags)}"
        )
    return problems


def check_language(lang, catalog, base, base_catalog):
    """Compare one language's catalog against English: keys, then each value."""
    problems = [
        f"[{lang}] missing key (would fall back to {base}): {key}"
        for key in sorted(base_catalog.keys() - catalog.keys())
    ]
    problems += [
        f"[{lang}] key not present in {base}: {key}"
        for key in sorted(catalog.keys() - base_catalog.keys())
    ]
    for key in sorted(base_catalog.keys() & catalog.keys()):
        problems += check_value(key, base_catalog[key], catalog[key], lang, base)
    return problems


def check_declarations(base, declared, present):
    """Verify LANGUAGES, CATALOG and DEFAULT_LANGUAGE agree with each other."""
    problems = [
        f"[{lang}] declared in LANGUAGES but absent from CATALOG"
        for lang in sorted(declared - present)
    ]
    problems += [
        f"[{lang}] present in CATALOG but not declared in LANGUAGES"
        for lang in sorted(present - declared)
    ]
    if base not in present:
        problems.append(f"[{base}] DEFAULT_LANGUAGE has no catalog")
    return problems


def find_property(node, name):
    """Return the first JSON-Schema property `name` found anywhere in the tree."""
    if isinstance(node, dict):
        found = node.get("properties", {}).get(name)
        if isinstance(found, dict):
            return found
        for value in node.values():
            found = find_property(value, name)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = find_property(value, name)
            if found is not None:
                return found
    return None


def check_schema(base, declared):
    """Cross-check nextflow_schema.json's report_language against i18n.py.

    The schema enum is the launch-time gate, so it must list exactly the
    languages the catalog implements; its default must be DEFAULT_LANGUAGE.
    """
    if not SCHEMA_PATH.exists():
        return [f"[schema] {SCHEMA_PATH.name} not found"]

    prop = find_property(
        json.loads(SCHEMA_PATH.read_text(encoding="utf-8")), "report_language"
    )
    if prop is None:
        return ["[schema] no report_language property found"]

    problems = []
    enum = set(prop.get("enum", []))
    if enum != declared:
        problems.append(
            f"[schema] report_language enum {sorted(enum)} != "
            f"i18n.LANGUAGES {sorted(declared)}"
        )
    if prop.get("default") != base:
        problems.append(
            f"[schema] report_language default {prop.get('default')!r} != "
            f"i18n.DEFAULT_LANGUAGE {base!r}"
        )
    return problems


def main():
    """Validate every language against English; report all problems found."""
    base = i18n.DEFAULT_LANGUAGE
    base_catalog = i18n.CATALOG[base]
    declared, present = set(i18n.LANGUAGES), set(i18n.CATALOG)

    problems = check_declarations(base, declared, present)
    problems += check_schema(base, declared)
    for lang in sorted(present - {base}):
        problems += check_language(lang, i18n.CATALOG[lang], base, base_catalog)

    if problems:
        print(f"i18n catalog check FAILED ({len(problems)} problem(s)):")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    langs = ", ".join(sorted(present))
    print(
        f"i18n catalog OK: {len(base_catalog)} keys x {len(present)} languages ({langs})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
