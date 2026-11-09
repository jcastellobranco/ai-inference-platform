import { readdirSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../src', import.meta.url));
const allowed = new Set([
  'components/ui/Button.tsx',
  'components/ui/Input.tsx',
  'components/ui/Textarea.tsx',
  'components/ui/Select.tsx',
  'components/ui/Table.tsx',
  'components/ui/Field.tsx',
  'components/ui/FileInput.tsx',
  'components/ui/Tabs.tsx',
]);
const restricted = /<(button|input|select|textarea|table|label)\b/g;
const violations = [];

function scan(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const file = join(dir, entry.name);
    if (entry.isDirectory()) { scan(file); continue; }
    if (!entry.name.endsWith('.tsx') || entry.name.includes('.test.')) continue;
    const name = relative(root, file).replaceAll('\\', '/');
    if (allowed.has(name)) continue;
    const source = readFileSync(file, 'utf8');
    for (const match of source.matchAll(restricted)) {
      const line = source.slice(0, match.index).split('\n').length;
      violations.push(`${name}:${line} <${match[1]}>`);
    }
  }
}
scan(root);
if (violations.length) {
  console.error('Use ATLAS UI primitives instead of raw interactive tags:\n' + violations.join('\n'));
  process.exitCode = 1;
} else {
  console.log('ATLAS UI primitive audit passed.');
}
