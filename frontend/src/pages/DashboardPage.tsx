import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Award, Battery, Bell, BookOpen, Brain, Compass, Flame, GraduationCap, HeartHandshake, Medal, Radio, School, Timer, Trophy, Wand2 } from 'lucide-react';
import { AnimatedNumber, AnimatedProgressBar } from '../components/ui/MotionPrimitives';
import { EmptyState, ErrorBanner, LoadingState } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type {
  ClassroomOut,
  CourseSummary,
  DueReviewItem,
  GamificationProfile,
  LeaderboardEntry,
  LessonProgressOut,
  NotificationsSummaryOut,
  StudentCompetencyOut,
} from '../types/api';

export function DashboardPage() {
  const { user, activeOrg } = useAppState();
  const [pushStatus, setPushStatus] = useState<string | null>(null);

  const notificationsQuery = useQuery({
    queryKey: ['my-notifications', user?.id],
    queryFn: () => apiRequest<NotificationsSummaryOut>('/notifications/me'),
    enabled: Boolean(user),
  });

  const classroomsQuery = useQuery({
    queryKey: ['my-classrooms', activeOrg?.organization_id],
    queryFn: () => apiRequest<ClassroomOut[]>(`/orgs/${activeOrg!.organization_id}/classrooms`),
    enabled: Boolean(user && activeOrg),
  });

  const firstClassroomId = classroomsQuery.data?.[0]?.id;

  const orgCoursesQuery = useQuery({
    queryKey: ['org-courses', activeOrg?.organization_id],
    queryFn: () => apiRequest<CourseSummary[]>(`/orgs/${activeOrg!.organization_id}/courses`),
    enabled: Boolean(user && activeOrg),
  });

  const progressQuery = useQuery({
    queryKey: ['my-progress', activeOrg?.organization_id],
    queryFn: () =>
      apiRequest<{ lessons: LessonProgressOut[]; competencies: StudentCompetencyOut[] }>(
        `/progress/me${activeOrg ? `?organization_id=${activeOrg.organization_id}` : ''}`
      ),
    enabled: Boolean(user),
  });

  const gamificationQuery = useQuery({
    queryKey: ['gamification-me', activeOrg?.organization_id],
    queryFn: () =>
      apiRequest<GamificationProfile>(
        `/gamification/me${activeOrg ? `?organization_id=${activeOrg.organization_id}` : ''}`
      ),
    enabled: Boolean(user),
  });

  const leaderboardQuery = useQuery({
    queryKey: ['classroom-leaderboard', activeOrg?.organization_id, firstClassroomId],
    queryFn: () =>
      apiRequest<LeaderboardEntry[]>(
        `/orgs/${activeOrg!.organization_id}/classrooms/${firstClassroomId}/leaderboard`
      ),
    enabled: Boolean(user && activeOrg && firstClassroomId),
  });

  const dueReviewsQuery = useQuery({
    queryKey: ['due-reviews-count', activeOrg?.organization_id],
    queryFn: () =>
      apiRequest<DueReviewItem[]>(
        `/reviews/due${activeOrg ? `?organization_id=${activeOrg.organization_id}` : ''}`
      ),
    enabled: Boolean(user),
  });

  if (!user) {
    return (
      <EmptyState
        title="Inicia sesión para ver tu panel"
        description="También puedes explorar cursos públicos gratuitos en el Catálogo Libre."
      />
    );
  }

  const totalLessonsCount = progressQuery.data?.lessons.length ?? 0;
  const completedLessonsCount = progressQuery.data?.lessons.filter((l) => l.status === 'completed').length ?? 0;
  const completionPct = totalLessonsCount > 0 ? Math.round((completedLessonsCount / totalLessonsCount) * 100) : 0;
  const canAuthor = Boolean(
    user.is_super_admin ||
      user.account_type === 'educator' ||
      (activeOrg && ['instructor', 'coordinator'].includes(activeOrg.role_code))
  );
  const totalXp = gamificationQuery.data?.total_xp ?? 0;
  const currentLevel = Math.floor(totalXp / 100) + 1;
  const levelProgressPct = totalXp % 100;

  return (
    <div className="space-y-6">
      <section className="surface-card relative overflow-hidden bg-gradient-to-r from-[var(--bg-surface)] via-[var(--bg-surface)] to-[var(--bg-accent-soft)] p-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-[var(--brand-primary)]">
            <Timer className="h-4 w-4" /> Tu próxima misión ({user.daily_goal_minutes ?? 5} min)
          </p>
          <h2 className="mt-1 text-lg font-extrabold">
            {(dueReviewsQuery.data?.length ?? 0) > 0
              ? `Tienes ${dueReviewsQuery.data?.length} retos listos para repaso inteligente SM-2 hoy`
              : 'Mantén tu racha completando una microlección hoy'}
          </h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            Nivel {currentLevel} • {100 - levelProgressPct} XP para subir de nivel
          </p>
        </div>
        <Link
          to={(dueReviewsQuery.data?.length ?? 0) > 0 ? '/reviews' : '/catalog'}
          className="btn-primary inline-flex shrink-0 items-center justify-center gap-1.5 px-5 py-2.5 text-xs font-bold"
        >
          <Brain className="h-4 w-4" />
          {(dueReviewsQuery.data?.length ?? 0) > 0 ? 'Repasar ahora' : 'Explorar lección'}
        </Link>
      </section>

      {/* Centro de accesos rápidos claro y visual */}
      <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
        <Link
          to="/catalog"
          className="surface-card interactive-card flex items-center gap-3 p-3.5 text-xs"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--bg-accent-soft)] text-[var(--brand-primary)]">
            <Compass className="h-4 w-4" />
          </span>
          <div>
            <p className="font-bold">Catálogo Libre</p>
            <p className="text-[11px] text-[var(--text-secondary)]">Explorar cursos abiertos</p>
          </div>
        </Link>
        <Link
          to="/unirse"
          className="surface-card interactive-card flex items-center gap-3 p-3.5 text-xs"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
            <School className="h-4 w-4" />
          </span>
          <div>
            <p className="font-bold">Unirme por Código</p>
            <p className="text-[11px] text-[var(--text-secondary)]">Ingresar a aula con QR o VZT</p>
          </div>
        </Link>
        <Link
          to="/vivo"
          className="surface-card interactive-card flex items-center gap-3 p-3.5 text-xs"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700">
            <Radio className="h-4 w-4" />
          </span>
          <div>
            <p className="font-bold">Clase en Vivo</p>
            <p className="text-[11px] text-[var(--text-secondary)]">Quiz interactivo en sala</p>
          </div>
        </Link>
        {canAuthor ? (
          <Link
            to="/studio"
            className="surface-card interactive-card flex items-center gap-3 p-3.5 text-xs"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-700">
              <Wand2 className="h-4 w-4" />
            </span>
            <div>
              <p className="font-bold">Estudio Docente IA</p>
              <p className="text-[11px] text-[var(--text-secondary)]">Crear materias y retos</p>
            </div>
          </Link>
        ) : (
          <Link
            to="/familia"
            className="surface-card interactive-card flex items-center gap-3 p-3.5 text-xs"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-rose-50 text-rose-700">
              <HeartHandshake className="h-4 w-4" />
            </span>
            <div>
              <p className="font-bold">Código Familiar</p>
              <p className="text-[11px] text-[var(--text-secondary)]">Compartir progreso con tutor</p>
            </div>
          </Link>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => {
            void (async () => {
              if (typeof Notification !== 'undefined') {
                await Notification.requestPermission();
              }
              await apiRequest('/notifications/subscribe', {
                method: 'POST',
                body: JSON.stringify({ endpoint: `device://${navigator.userAgent.slice(0, 80)}`, device_label: 'Web PWA' }),
              });
              setPushStatus('Recordatorios activados en este dispositivo.');
            })();
          }}
          className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--border-subtle)] bg-white px-3.5 py-2 text-xs font-semibold transition hover:bg-slate-50"
        >
          <Bell className="h-4 w-4 text-amber-600" /> {pushStatus || 'Activar avisos de repaso'}
        </button>
      </div>

      {notificationsQuery.data && notificationsQuery.data.reminders.length > 0 && (
        <section className="surface-card p-4 space-y-2">
          <p className="text-xs font-bold uppercase text-[var(--text-secondary)]">Alertas Inteligentes</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {notificationsQuery.data.reminders.map((r) => (
              <Link
                key={r.id}
                to={r.action_url}
                className="rounded-lg border border-[var(--border-subtle)] bg-slate-50 px-3 py-2 text-xs hover:bg-[var(--bg-accent-soft)]"
              >
                <p className="font-bold text-[var(--brand-primary)]">{r.title}</p>
                <p className="text-[var(--text-secondary)]">{r.body}</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="surface-card p-6">
        <h1 className="text-2xl font-bold">Hola, {user.full_name}</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          {activeOrg
            ? `Contexto institucional: ${activeOrg.organization_name} (${activeOrg.role_name})`
            : 'Contexto actual: Modo Estudio Libre'}
        </p>

        {gamificationQuery.data && (
          <div className="mt-4 space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-xl bg-[var(--bg-accent-soft)] p-3.5 transition hover:scale-[1.02]">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-[var(--brand-primary)]">
                  <Trophy className="h-4 w-4" /> XP Total (Nv. {currentLevel})
                </div>
                <p className="mt-1 text-2xl font-extrabold">
                  <AnimatedNumber value={gamificationQuery.data.total_xp} />
                </p>
              </div>
              <div className="rounded-xl bg-amber-50 p-3.5 transition hover:scale-[1.02]">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-800">
                  <Flame className="h-4 w-4" /> Racha
                </div>
                <p className="mt-1 text-2xl font-extrabold">
                  <AnimatedNumber value={gamificationQuery.data.current_streak_days} suffix=" días" />
                </p>
              </div>
              <div className="rounded-xl bg-emerald-50 p-3.5 transition hover:scale-[1.02]">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-800">
                  <Battery className="h-4 w-4" /> Energía
                </div>
                <p className="mt-1 text-2xl font-extrabold">
                  {gamificationQuery.data.current_energy}/{gamificationQuery.data.max_energy}
                </p>
              </div>
            </div>
            <AnimatedProgressBar
              percent={completionPct}
              label={`Avance de lecciones (${completedLessonsCount}/${totalLessonsCount})`}
              tone="emerald"
            />
          </div>
        )}
      </section>

      {progressQuery.isLoading ? (
        <LoadingState label="Cargando avance..." />
      ) : progressQuery.error ? (
        <ErrorBanner message={(progressQuery.error as Error).message} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="surface-card p-5">
            <div className="flex items-center gap-2 font-bold text-sm text-[var(--brand-primary)]">
              <GraduationCap className="h-4 w-4" /> Lecciones registradas
            </div>
            <p className="mt-2 text-3xl font-extrabold">{progressQuery.data?.lessons.length ?? 0}</p>
            <p className="text-xs text-[var(--text-secondary)]">
              Completadas: {progressQuery.data?.lessons.filter((l) => l.status === 'completed').length ?? 0}
            </p>
          </div>
          <div className="surface-card p-5">
            <div className="flex items-center gap-2 font-bold text-sm text-[var(--brand-primary)]">
              <Award className="h-4 w-4" /> Competencias evaluadas
            </div>
            <p className="mt-2 text-3xl font-extrabold">{progressQuery.data?.competencies.length ?? 0}</p>
            <p className="text-xs text-[var(--text-secondary)]">
              Logradas (≥ 80%):{' '}
              {progressQuery.data?.competencies.filter((c) => c.mastery_status === 'achieved').length ?? 0}
            </p>
          </div>
        </div>
      )}

      {gamificationQuery.data && gamificationQuery.data.badges.length > 0 && (
        <section className="surface-card p-5">
          <h2 className="flex items-center gap-2 text-base font-bold">
            <Medal className="h-4 w-4 text-[var(--brand-secondary)]" /> Insignias desbloqueadas
          </h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {gamificationQuery.data.badges.map((b) => (
              <span
                key={b.code}
                className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-950"
              >
                {b.name}
              </span>
            ))}
          </div>
        </section>
      )}

      {activeOrg && (
        <section className="space-y-3">
          <h2 className="text-lg font-bold">Aulas y cursos de {activeOrg.organization_name}</h2>
          {classroomsQuery.isLoading || orgCoursesQuery.isLoading ? (
            <LoadingState label="Cargando aulas institucionales..." />
          ) : classroomsQuery.error ? (
            <ErrorBanner message={(classroomsQuery.error as Error).message} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {(orgCoursesQuery.data ?? []).map((course) => (
                <div key={course.id} className="surface-card flex flex-col justify-between p-5">
                  <div>
                    <span className="rounded-full bg-[var(--bg-accent-soft)] px-2.5 py-0.5 text-xs font-semibold text-[var(--brand-primary)]">
                      {course.education_level}
                    </span>
                    <h3 className="mt-2 text-base font-bold">{course.title}</h3>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">{course.description}</p>
                  </div>
                  <Link
                    to={`/courses/${course.id}${firstClassroomId ? `?classroomId=${firstClassroomId}` : ''}`}
                    className="btn-primary mt-4 inline-flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-semibold"
                  >
                    <BookOpen className="h-4 w-4" /> Entrar al curso
                  </Link>
                </div>
              ))}
            </div>
          )}

          {leaderboardQuery.data && leaderboardQuery.data.length > 0 && (
            <div className="surface-card p-5">
              <h3 className="text-base font-bold">Ranking del aula</h3>
              <ul className="mt-3 space-y-2">
                {leaderboardQuery.data.map((entry) => (
                  <li
                    key={`${entry.rank}-${entry.display_name}`}
                    className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm ${
                      entry.is_me ? 'bg-[var(--bg-accent-soft)] font-bold' : 'bg-slate-50'
                    }`}
                  >
                    <span>
                      #{entry.rank} {entry.display_name}
                    </span>
                    <span>{entry.xp_in_classroom} XP</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
