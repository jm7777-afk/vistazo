export type StudioScope =
  | { mode: 'global'; label: string }
  | { mode: 'org'; orgId: string; label: string };

export function scopePrefix(scope: StudioScope): string {
  return scope.mode === 'global' ? '/admin' : `/orgs/${scope.orgId}`;
}

export function slugifyText(value: string): string {
  const clean = value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return clean || `item-${Date.now()}`;
}

export async function readTextDocument(file: File): Promise<string> {
  const text = await file.text();
  return text.slice(0, 10000);
}
