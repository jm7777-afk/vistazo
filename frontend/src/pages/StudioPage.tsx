import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BookMarked, Flame, Image, Layers, Sparkles, Wand2 } from 'lucide-react';
import { BlueprintTab } from '../components/studio/BlueprintTab';
import { ChallengesExamTab } from '../components/studio/ChallengesExamTab';
import { CoursesNodesTab } from '../components/studio/CoursesNodesTab';
import { DynamicVisualsTab } from '../components/studio/DynamicVisualsTab';
import { GuidesPensumTab } from '../components/studio/GuidesPensumTab';
import type { StudioScope } from '../components/studio/studioHelpers';
import { EmptyState } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';

type TabId = 'blueprint' | 'courses' | 'guides' | 'challenges' | 'visuals';

export function StudioPage() {
  const { user, activeOrg } = useAppState();
  const [tab, setTab] = useState<TabId>('blueprint');
  const [adminScopeChoice, setAdminScopeChoice] = useState<'global' | string>('global');
  const [selectedCourseId, setSelectedCourseId] = useState('');
  const [selectedLessonId, setSelectedLessonId] = useState('');
  const [selectedLvId, setSelectedLvId] = useState('');

  const adminOrgsQuery = useQuery({
    queryKey: ['studio-admin-orgs'],
    queryFn: () => apiRequest<{ id: string; name: string; slug: string }[]>('/admin/organizations'),
    enabled: Boolean(user?.is_super_admin),
  });

  if (!user) {
    return (
      <EmptyState
        title="Inicia sesión para abrir el Estudio Pedagógico"
        description="Disponible para Educadores, Instructores, Coordinadores y SuperAdministradores."
      />
    );
  }

  const canAuthor =
    user.is_super_admin ||
    user.account_type === 'educator' ||
    Boolean(activeOrg && ['instructor', 'coordinator'].includes(activeOrg.role_code));

  if (!canAuthor) {
    return (
      <EmptyState
        title="Estudio restringido a cuentas docentes"
        description="Tu cuenta actual es de Estudiante. Crea una cuenta de Educador o solicita asignación de instructor."
      />
    );
  }

  let scope: StudioScope | null = null;
  if (user.is_super_admin) {
    if (adminScopeChoice === 'global') {
      scope = { mode: 'global', label: 'Catálogo Público Global' };
    } else {
      const found = (adminOrgsQuery.data ?? []).find((o) => o.id === adminScopeChoice);
      scope = {
        mode: 'org',
        orgId: adminScopeChoice,
        label: found ? found.name : activeOrg?.organization_name || 'Organización',
      };
    }
  } else if (activeOrg) {
    scope = { mode: 'org', orgId: activeOrg.organization_id, label: activeOrg.organization_name };
  }

  if (!scope) {
    return (
      <EmptyState
        title="Selecciona un espacio docente activo"
        description="Elige tu espacio docente u organización en el selector superior derecho."
      />
    );
  }

  const tabs: { id: TabId; label: string; icon: typeof Sparkles }[] = [
    { id: 'blueprint', label: 'Arquitecto IA & Carga', icon: Wand2 },
    { id: 'courses', label: 'Materias y Nodos', icon: Layers },
    { id: 'guides', label: 'Guías, Temarios y Pensum', icon: BookMarked },
    { id: 'challenges', label: 'Retos y Pruebas Fuertes', icon: Flame },
    { id: 'visuals', label: 'Imágenes Dinámicas', icon: Image },
  ];

  return (
    <div className="space-y-6">
      <div className="surface-card p-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--bg-accent-soft)] px-3 py-1 text-xs font-bold text-[var(--brand-primary)]">
            <Sparkles className="h-3.5 w-3.5" /> Estudio Pedagógico {user.is_super_admin ? 'SuperAdmin' : 'Educador'}
          </span>
          <h1 className="mt-2 text-2xl font-bold">Creación Manual o Asistida por IA — {scope.label}</h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            CRUD completo de materias, módulos, nodos, temarios, metodología, guías, pruebas fuertes e imágenes dinámicas.
          </p>
        </div>

        {user.is_super_admin && (
          <label className="block text-xs font-bold">
            Ámbito de publicación SuperAdmin
            <select
              value={adminScopeChoice}
              onChange={(e) => {
                setAdminScopeChoice(e.target.value);
                setSelectedCourseId('');
                setSelectedLessonId('');
                setSelectedLvId('');
              }}
              className="mt-1 w-full md:w-64 rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm font-medium"
            >
              <option value="global">Catálogo Público Global (Estudio Libre)</option>
              {(adminOrgsQuery.data ?? []).map((o) => (
                <option key={o.id} value={o.id}>
                  Institución: {o.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {/* Navegación de pestañas */}
      <div className="flex flex-wrap gap-2">
        {tabs.map((item) => {
          const Icon = item.icon;
          const active = tab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={`inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-xs font-bold transition ${
                active
                  ? 'border-[var(--brand-primary)] bg-[var(--brand-primary)] text-white shadow-sm'
                  : 'border-[var(--border-subtle)] bg-white text-[var(--text-primary)] hover:bg-slate-50'
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </button>
          );
        })}
      </div>

      {tab === 'blueprint' && (
        <BlueprintTab
          scope={scope}
          onCourseCreated={(cid) => {
            setSelectedCourseId(cid);
            setTab('courses');
          }}
        />
      )}

      {tab === 'courses' && (
        <CoursesNodesTab
          scope={scope}
          selectedCourseId={selectedCourseId}
          onSelectCourse={setSelectedCourseId}
          onJumpToChallenges={(cid, lid) => {
            setSelectedCourseId(cid);
            setSelectedLessonId(lid);
            setTab('challenges');
          }}
        />
      )}

      {tab === 'guides' && <GuidesPensumTab scope={scope} selectedCourseId={selectedCourseId} />}

      {tab === 'challenges' && (
        <ChallengesExamTab
          scope={scope}
          selectedCourseId={selectedCourseId}
          selectedLessonId={selectedLessonId}
          onSelectCourse={setSelectedCourseId}
          onSelectLesson={setSelectedLessonId}
          onVersionSelected={setSelectedLvId}
        />
      )}

      {tab === 'visuals' && <DynamicVisualsTab scope={scope} selectedLessonVersionId={selectedLvId} />}
    </div>
  );
}
