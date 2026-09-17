"""Extract declared ASCII word forms from CoNLL-U reference texts."""

import re
import unicodedata
import hashlib
import json
from pathlib import Path


def normalize_word(form):
    """Fold case and accents; reject a complete nonalphabetic surface form."""
    value = ''.join(c for c in unicodedata.normalize('NFKD', form).casefold()
                    if not unicodedata.combining(c))
    return value if re.fullmatch('[a-z]+', value) else None


def parse_conllu(text):
    """Keep orthographic multiword forms; skip their syntactic components."""
    sentences = []
    document = None
    sentence_id = None
    reference = None
    words = []
    covered = set()
    has_rows = False
    stats = dict(surface_tokens=0, accepted_words=0, excluded_surface_tokens=0,
                 multiword_tokens=0, skipped_component_rows=0, empty_nodes=0)

    def finish():
        nonlocal sentence_id, reference, words, covered, has_rows
        if has_rows:
            sentences.append({'id': sentence_id, 'document': document,
                              'reference': reference, 'words': words})
        sentence_id, reference, words, covered, has_rows = None, None, [], set(), False

    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            finish()
            continue
        if line.startswith('#'):
            if line.startswith('# newdoc'):
                document = line.split('=', 1)[1].strip() if '=' in line else f'document-line-{number}'
            elif line.startswith('# sent_id ='):
                sentence_id = line.split('=', 1)[1].strip()
            elif line.startswith('# reference ='):
                reference = line.split('=', 1)[1].strip()
            continue
        columns = line.split('\t')
        if len(columns) != 10:
            raise ValueError(f'Expected 10 CoNLL-U columns at line {number}.')
        identifier, form = columns[:2]
        has_rows = True
        if re.fullmatch(r'\d+\.\d+', identifier):
            stats['empty_nodes'] += 1
            continue
        if re.fullmatch(r'\d+-\d+', identifier):
            first, last = map(int, identifier.split('-'))
            if first >= last or covered.intersection(range(first, last + 1)):
                raise ValueError(f'Invalid multiword range at line {number}.')
            covered.update(range(first, last + 1))
            stats['multiword_tokens'] += 1
        elif re.fullmatch(r'\d+', identifier):
            if int(identifier) in covered:
                stats['skipped_component_rows'] += 1
                continue
        else:
            raise ValueError(f'Invalid CoNLL-U identifier at line {number}.')
        stats['surface_tokens'] += 1
        normalized = normalize_word(form)
        if normalized is None:
            stats['excluded_surface_tokens'] += 1
        else:
            words.append(normalized)
            stats['accepted_words'] += 1
    finish()
    stats['sentences'] = len(sentences)
    stats['explicit_documents'] = len({s['document'] for s in sentences if s['document'] is not None})
    return {'sentences': sentences, 'stats': stats,
            'normalization': 'NFKD casefold; remove combining marks; accept whole ASCII a-z forms only; preserve MWT surface forms; exclude empty nodes.'}


def reference_document(corpus_id, sentence):
    if corpus_id == 'latin_llct':
        match = re.search(r"document_id='([^']+)'", sentence['reference'] or '')
    elif corpus_id == 'italian_old':
        match = re.fullmatch(r'OldItalian_Dante_(Inferno|Purgatorio|Paradiso)-\d+',
                             sentence['id'] or '')
    else:
        raise ValueError(f'No document rule for corpus: {corpus_id}')
    if match is None:
        raise ValueError(f'Missing document identifier for corpus: {corpus_id}')
    return match[1]


def remove_cross_partition_duplicates(partitions):
    """Remove exact normalized sentences from each later partition."""
    earlier = set()
    cleaned, excluded = {}, {}
    for split in ['train', 'validation', 'test']:
        sentences = partitions[split]
        cleaned[split] = [s for s in sentences if s['words'] and tuple(s['words']) not in earlier]
        excluded[split] = {
            'sentences': len(sentences) - len(cleaned[split]),
            'words': sum(len(s['words']) for s in sentences) - sum(len(s['words']) for s in cleaned[split]),
        }
        earlier.update(tuple(s['words']) for s in sentences)
    return cleaned, excluded


def load_reference_partitions(project_root):
    """Read pinned inputs and create whole-charter or canticle partitions."""
    root = Path(project_root)
    manifest_path = root / 'data/reference_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    output = {}
    for corpus in manifest['corpora']:
        corpus_id = corpus['id']
        partitions = {s: [] for s in ['train', 'validation', 'test']}
        document_split, files = {}, {}
        for file in corpus['files']:
            if file['role'] != 'conllu':
                continue
            path = root / manifest['raw_output_dir'] / corpus_id / file['name']
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if digest != file['sha256']:
                raise ValueError(f'Reference hash mismatch: {corpus_id}/{file["name"]}')
            parsed = parse_conllu(content.decode('utf-8'))
            files[file['name']] = {'sha256': digest, 'extraction': parsed['stats']}
            for sentence in parsed['sentences']:
                document = reference_document(corpus_id, sentence)
                if corpus_id == 'latin_llct':
                    split = {'train': 'train', 'dev': 'validation', 'test': 'test'}[file['split']]
                else:
                    split = {'Inferno': 'train', 'Purgatorio': 'validation', 'Paradiso': 'test'}[document]
                if document in document_split and document_split[document] != split:
                    raise ValueError(f'A reference document crosses partitions: {document}')
                document_split[document] = split
                partitions[split].append(sentence)
        cleaned, excluded = remove_cross_partition_duplicates(partitions)
        words = {s: [w for row in rows for w in row['words']] for s, rows in cleaned.items()}
        output[corpus_id] = {
            'words': words,
            'metadata': {
                'reference_manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                'source_files': files,
                'normalization': parsed['normalization'],
                'document_split': dict(sorted(document_split.items())),
                'split_counts': {s: {'sentences': len(cleaned[s]), 'words': len(words[s]),
                                    'documents': sum(v == s for v in document_split.values())}
                                 for s in partitions},
                'duplicate_or_empty_exclusions': excluded,
                'limit': 'Exact normalized duplicate sentences are removed across partitions. Near duplicates remain. Dante partitions are canticles of one work by one author.',
            },
        }
    return output
