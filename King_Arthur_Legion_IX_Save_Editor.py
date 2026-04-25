#!/usr/bin/env python3
"""King Arthur: Legion IX - Save Editor"""

import struct, glob, os, re

# ── Morality events ──────────────────────────────────────────────────────────

EVENTS = {
    'human': [
        (b'ProtectorofNovaRoma_Human',  b'ProtectorofNovaRoma'),
        (b'PlutoniusNerva_Human',       b'PlutoniusNerva'),
        (b'ExtremePrejudice_Human',     b'ExtremePrejudice'),
        (b'BloodontheSands_Human',      b'BloodontheSands'),
        (b'PanemetCircenses_Human',     b'PanemetCircenses'),
        (b'DemonicHunger_Human',        b'DemonicHunger'),
        (b'AllConsumingMadness_Human',  b'AllConsumingMadness'),
        (b'PledgetoSulla_Human',        b'PledgetoSulla'),
        (b'TheEyeofBalor_Human',        b'TheEyeofBalor'),
        (b'TheSleepingGod_Human',       b'TheSleepingGod'),
    ],
    'demonic': [
        (b'ProtectorofNovaRoma_Demonic', b'ProtectorofNovaRoma'),
        (b'PlutoniusNerva_Demonic',      b'PlutoniusNerva'),
        (b'ExtremePrejudice_Demonic',    b'ExtremePrejudice'),
        (b'BloodontheSands_Demonic',     b'BloodontheSands'),
        (b'PanemetCircenses_Demonic',    b'PanemetCircenses'),
        (b'DemonicHunger_Demonic',       b'DemonicHunger'),
        (b'AllConsumingMadness_Demonic', b'AllConsumingMadness'),
        (b'TheFlaminasConcerns_Demonic', b'TheFlaminasConcerns'),
        (b'TheEyeofBalor_Demonic',       b'TheEyeofBalor'),
        (b'TheSleepingGod_Demonic',      b'TheSleepingGod'),
    ],
}

# ── Save file ────────────────────────────────────────────────────────────────

class SaveFile:
    SECTION = b'\nAdventure.cfg'

    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.data = f.read()

    def backup(self):
        with open(self.path + '.bak', 'wb') as f:
            f.write(self.data)
        print(f'  Backup: {self.path}.bak')

    def write(self):
        with open(self.path, 'wb') as f:
            f.write(self.data)
        print(f'  Saved:  {self.path}')

    def get(self, pattern):
        m = re.search(pattern, self.data)
        return m.group(1).decode() if m else None

    def apply(self, replacements):
        """Apply list of (old, new) byte pairs, updating section length."""
        delta = sum(len(n) - len(o) for o, n in replacements)
        if delta:
            idx     = self.data.find(self.SECTION)
            ls      = idx - 4
            old_len = struct.unpack('<I', self.data[ls:idx])[0]
            self.data = (self.data[:ls]
                         + struct.pack('<I', old_len + delta)
                         + self.data[idx:])
        for old, new in replacements:
            if old in self.data:
                self.data = self.data.replace(old, new, 1)
                print(f'  ✓ {old[:50].decode()} → {new[:50].decode()}')
            else:
                print(f'  ✗ NOT FOUND: {old[:50].decode()}')


# ── Editor ───────────────────────────────────────────────────────────────────

class Editor:
    CURRENCY_FIELDS = ['RelicDust', 'Gold', 'BuildingResource']

    def __init__(self, save: SaveFile):
        self.save = save

    # ── Display ──────────────────────────────────────────────────────────────

    def show(self):
        s = self.save
        print('\n─── Current Values ───────────────────────────────')
        for f in self.CURRENCY_FIELDS:
            v = s.get(f.encode() + rb'=(\d+)')
            print(f'  {f:<20}: {v}')

        rel = s.get(rb'Religin=(-?\d+)')
        if rel:
            val  = int(rel)
            side = 'Humanity' if val > 0 else 'Demonic' if val < 0 else 'Neutral'
            print(f'  {"Alignment":<20}: {val:+d} ({side})')
            print(f'  {"Scale":<20}: -10 Full Demonic .. 0 Neutral .. +10 Full Humanity')

        impacts = s.get(rb'MoralityImpacts=([^\n]+)')
        if impacts:
            entries = [e for e in impacts.split(',') if e]
            print(f'  {"MoralityImpacts":<20}: {len(entries)} entries')
        print('──────────────────────────────────────────────────\n')

    # ── Currencies ───────────────────────────────────────────────────────────

    def edit_currencies(self):
        replacements = []
        for field in self.CURRENCY_FIELDS:
            val = input(f'  {field} (blank=skip): ').strip()
            if not val:
                continue
            cur = self.save.get(field.encode() + rb'=(\d+)')
            replacements.append((
                f'{field}={cur}\n'.encode(),
                f'{field}={val}\n'.encode(),
            ))
        return replacements

    # ── Alignment ────────────────────────────────────────────────────────────

    def edit_alignment(self):
        print('\n  [1] Full Humanity  (+10)')
        print('  [2] Neutral         (0) ')
        print('  [3] Full Demonic   (-10)')
        print('  [4] Custom score        ')
        print('  [blank] Skip            ')

        choice = input('\n  Choose: ').strip()
        if not choice:
            return []

        presets = {'1': (10, 'human'), '2': (0, None), '3': (-10, 'demonic')}

        if choice in presets:
            score, side = presets[choice]
        elif choice == '4':
            try:
                score = int(input('  Religin value [-10..10]: '))
                side  = None
            except ValueError:
                print('  Invalid, skipping.')
                return []
        else:
            print('  Invalid choice, skipping.')
            return []

        s         = self.save
        rel_m     = re.search(rb'Religin=(-?\d+)(\n\tReceivedNewDecreeNotification)', s.data)
        rellast_m = re.search(rb'ReligionLast=(-?\d+)(\n\tOrderCooldowns)', s.data)
        impacts_m = re.search(rb'MoralityImpacts=[^\n]+', s.data)

        if not all([rel_m, rellast_m, impacts_m]):
            print('  ERROR: alignment fields not found!')
            return []

        score_b      = str(score).encode()
        replacements = [
            (rel_m.group(0),     b'Religin='      + score_b + rel_m.group(2)),
            (rellast_m.group(0), b'ReligionLast='  + score_b + rellast_m.group(2)),
        ]

        if side:
            new_impacts = b'MoralityImpacts=' + b','.join(
                e[0] + b';' + e[1] + b';1' for e in EVENTS[side]
            )
            replacements.append((impacts_m.group(0), new_impacts))
        elif choice == '2':
            replacements.append((impacts_m.group(0), b'MoralityImpacts='))

        return replacements

    # ── Run ──────────────────────────────────────────────────────────────────

    def run(self):
        self.show()

        print('─── Currencies ───────────────────────────────────')
        currency_changes  = self.edit_currencies()

        print('\n─── Alignment ────────────────────────────────────')
        alignment_changes = self.edit_alignment()

        all_changes = currency_changes + alignment_changes
        if not all_changes:
            print('\nNothing to change.')
            return

        self.save.backup()
        print('\n─── Applying ─────────────────────────────────────')
        self.save.apply(all_changes)
        self.save.write()
        print('\nDone! Load your save and enjoy!')


# ── Entry point ──────────────────────────────────────────────────────────────

def pick_save():
    saves = [f for f in glob.glob(os.path.join(os.getcwd(), '*.sav'))
             if not f.endswith('.bak')]
    if not saves:
        print(f'No .sav files found in {os.getcwd()}')
        return None
    print('─── Save Files ───────────────────────────────────')
    for i, p in enumerate(saves):
        print(f'  [{i}] {os.path.basename(p)}')
    idx = int(input('\nSelect [0]: ') or 0)
    return saves[idx]


if __name__ == '__main__':
    print('══════════════════════════════════════════════════')
    print('    King Arthur: Legion IX  —  Save Editor       ')
    print('══════════════════════════════════════════════════')
    path = pick_save()
    if path:
        Editor(SaveFile(path)).run()
