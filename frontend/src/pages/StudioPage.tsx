import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, BookMarked, Database, Flame, Image, Layers, Sparkles, Wand2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { AnalyticsInvitesTab } from '../components/studio/AnalyticsInvitesTab';
import { BankAndGradingTab } from '../components/studio/BankAndGradingTab';
import { BlueprintTab } from '../components/studio/BlueprintTab';
import { ChallengesExamTab } from '../components/studio/ChallengesExamTab';
import { CoursesNodesTab } from '../components/studio/CoursesNodesTab';
import { DynamicVisualsTab } from '../components/studio/DynamicVisualsTab';
import { GuidesPensumTab } from '../components/studio/GuidesPensumTab';
import type { StudioScope } from '../components/studio/studioHelpers';
import { EmptyState } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';

type TabId = 'blueprint' | 'courses' | 'guides' | 'challenges' | 'bank' | 'visuals' | 'analytics';

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

  const tabs: { id: TabId; num: string; label: string; tip: string; icon: typeof Sparkles }[] = [
    {
      id: 'blueprint',
      num: '1',
      label: 'Arquitecto IA & Carga',
      tip: 'Sube PDF/DOCX o describe tu materia y deja que la IA estructure módulos y guías.',
      icon: Wand2,
    },
    {
      id: 'courses',
      num: '2',
      label: 'Materias y Nodos',
      tip: 'Edita cursos, organiza módulos, configura notas mínimas y exámenes aleatorios.',
      icon: Layers,
    },
    {
      id: 'guides',
      num: '3',
      label: 'Guías, Temarios y Pensum',
      tip: 'Redacta o genera metodologías de estudio, pensums oficiales y expórtalos en PDF.',
      icon: BookMarked,
    },
    {
      id: 'challenges',
      num: '4',
      label: 'Retos y Pruebas Fuertes',
      tip: 'Crea retos de 7 tipos (visuales, simulación o respuesta abierta), publica o lanza Clase en Vivo.',
      icon: Flame,
    },
    {
      id: 'bank',
      num: '5',
      label: 'Banco y Calificación',
      tip: 'Guarda preguntas reutilizables por tema, inyéctalas en exámenes y califica respuestas abiertas.',
      icon: Database,
    },
    {
      id: 'visuals',
      num: '6',
      label: 'Imágenes Dinámicas',
      tip: 'Genera diagramas SVG interactivos, ilustraciones IA o sube clips de audio y archivos.',
      icon: Image,
    },
    {
      id: 'analytics',
      num: '7',
      label: 'Analíticas, QR y Vivo',
      tip: 'Crea aulas, descarga códigos QR de invitación y monitorea el rendimiento del grupo.',
      icon: BarChart3,
    },
  ];
  const activeTabInfo = tabs.find((t) => t.id === tab);

  return (
    <div className="space-y-6">
      <div className="surface-card p-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--bg-accent-soft)] px-3 py-1 text-xs font-bold text-[var(--brand-primary)]">
              <Sparkles className="h-3.5 w-3.5" /> Estudio Pedagógico {user.is_super_admin ? 'SuperAdmin' : 'Educador'}
            </span>
            <Link
              to="/planes"
              className="rounded-full border border-[var(--border-subtle)] bg-white px-3 py-1 text-xs font-semibold text-[var(--text-secondary)] hover:border-[var(--brand-primary)]"
            >
              Ver Planes SaaS y Cupos
            </Link>
          </div>
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

      {/* Navegación paso a paso del Estudio */}
      <div className="space-y-2.5">
        <div className="flex flex-wrap gap-2">
          {tabs.map((item) => {
            const Icon = item.icon;
            const active = tab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setTab(item.id)}
                className={`inline-flex items-center gap-2 rounded-xl border px-3.5 py-2.5 text-xs font-bold transition-all duration-150 ${
                  active
                    ? 'border-[var(--brand-primary)] bg-[var(--brand-primary)] text-white shadow-sm scale-[1.02]'
                    : 'border-[var(--border-subtle)] bg-white text-[var(--text-primary)] hover:border-[var(--brand-primary)]/40 hover:bg-slate-50'
                }`}
              >
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-extrabold ${
                    active ? 'bg-white/20 text-white' : 'bg-[var(--bg-accent-soft)] text-[var(--brand-primary)]'
                  }`}
                >
                  {item.num}
                </span>
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </div>
        {activeTabInfo && (
          <div className="vzt-fade-up rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-accent-soft)]/55 px-4 py-2.5 text-xs text-[var(--text-secondary)]">
            <strong className="text-[var(--brand-primary)]">Paso {activeTabInfo.num} — {activeTabInfo.label}:</strong>{' '}
            {activeTabInfo.tip}
          </div>
        )}
      </div>

      <div key={tab} className="vzt-fade-up">

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

      {tab === 'bank' && <BankAndGradingTab scope={scope} selectedLessonVersionId={selectedLvId} />}

      {tab === 'visuals' && <DynamicVisualsTab scope={scope} selectedLessonVersionId={selectedLvId} />}

      {tab === 'analytics' && <AnalyticsInvitesTab scope={scope} />}
      </div>
    </div>
  );
}
