import React, { useState } from 'react';
import { Crosshair, Plus, Trash2 } from 'lucide-react';
import { resolveAssetUrl } from '../../services/apiClient';

export interface EditableZone {
  id: string;
  shape: 'circle';
  x: number;
  y: number;
  r: number;
  label: string;
}

interface Props {
  imageUrl?: string | null;
  zones: EditableZone[];
  correctZoneId: string;
  onChangeZones: (zones: EditableZone[]) => void;
  onChangeCorrectZoneId: (id: string) => void;
}

export function VisualZoneEditor({
  imageUrl,
  zones,
  correctZoneId,
  onChangeZones,
  onChangeCorrectZoneId,
}: Props) {
  const [nextLabel, setNextLabel] = useState('');

  const handleSvgClick = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.max(0.05, Math.min(0.95, Number(((e.clientX - rect.left) / rect.width).toFixed(3))));
    const y = Math.max(0.05, Math.min(0.95, Number(((e.clientY - rect.top) / rect.height).toFixed(3))));
    const id = `z${Date.now().toString().slice(-4)}`;
    const label = nextLabel.trim() || `Zona ${zones.length + 1}`;
    const updated: EditableZone[] = [...zones, { id, shape: 'circle', x, y, r: 0.08, label }];
    onChangeZones(updated);
    if (!correctZoneId) {
      onChangeCorrectZoneId(id);
    }
    setNextLabel('');
  };

  return (
    <div className="space-y-2.5 rounded-xl border border-[var(--border-subtle)] bg-slate-50 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-xs font-bold text-[var(--brand-primary)]">
          <Crosshair className="h-4 w-4" /> Editor Visual de Zonas (clic directo sobre la imagen)
        </span>
        <input
          type="text"
          placeholder="Etiqueta próxima zona (ej. Válvula)"
          value={nextLabel}
          onChange={(e) => setNextLabel(e.target.value)}
          className="rounded border border-[var(--border-subtle)] bg-white px-2.5 py-1 text-xs"
        />
      </div>

      <div className="relative overflow-hidden rounded-lg border border-slate-300 bg-white">
        {imageUrl && (
          <img src={resolveAssetUrl(imageUrl)} alt="Lienzo zonas" className="block aspect-[16/9] w-full object-contain" />
        )}
        <svg
          viewBox="0 0 100 56"
          onClick={handleSvgClick}
          className={`${imageUrl ? 'absolute inset-0 h-full w-full' : 'block aspect-[16/9] w-full'} cursor-crosshair`}
        >
          {!imageUrl && <rect width="100" height="56" fill="#f1f5f9" />}
          {zones.map((z) => {
            const isCorrect = z.id === correctZoneId;
            return (
              <g key={z.id}>
                <circle
                  cx={z.x * 100}
                  cy={z.y * 56}
                  r={z.r * 56}
                  fill={isCorrect ? 'rgba(5, 150, 105, 0.35)' : 'rgba(217, 119, 6, 0.25)'}
                  stroke={isCorrect ? '#059669' : '#d97706'}
                  strokeWidth="1"
                />
                <text
                  x={z.x * 100}
                  y={z.y * 56 + 1.5}
                  fontSize="3"
                  fontWeight="700"
                  textAnchor="middle"
                  fill="#0f172a"
                >
                  {z.label.slice(0, 16)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {zones.length > 0 ? (
        <div className="space-y-1">
          {zones.map((z) => (
            <div key={z.id} className="flex items-center justify-between gap-2 rounded bg-white px-2.5 py-1 text-xs">
              <label className="flex items-center gap-2 font-medium">
                <input
                  type="radio"
                  name="correct_zone"
                  checked={correctZoneId === z.id}
                  onChange={() => onChangeCorrectZoneId(z.id)}
                />
                <span>
                  {z.label} <span className="text-[10px] text-slate-500">({z.x}, {z.y})</span>
                </span>
              </label>
              <button
                type="button"
                onClick={() => {
                  const filtered = zones.filter((x) => x.id !== z.id);
                  onChangeZones(filtered);
                  if (correctZoneId === z.id) {
                    onChangeCorrectZoneId(filtered[0]?.id ?? '');
                  }
                }}
                className="text-red-700 hover:underline"
                aria-label="Quitar zona"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="flex items-center gap-1 text-[11px] text-[var(--text-secondary)]">
          <Plus className="h-3.5 w-3.5" /> Haz clic en al menos 2 puntos sobre el esquema para crear zonas interactivas.
        </p>
      )}
    </div>
  );
}
