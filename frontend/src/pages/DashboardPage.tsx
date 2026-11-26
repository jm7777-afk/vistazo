import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Award, Battery, BookOpen, Flame, GraduationCap, Medal, Trophy } from 'lucide-react';
import { EmptyState, ErrorBanner, LoadingState } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type {
  ClassroomOut,
  CourseSummary,
  GamificationProfile,
  LeaderboardEntry,
  LessonProgressOut,
  StudentCompetencyOut,
} from '../types/api';

export function DashboardPage() {
  const { user, activeOrg } = useAppState();

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

  if (!user) {
    return (
      <EmptyState
        title="Inicia sesión para ver tu panel"
        description="También puedes explorar cursos públicos gratuitos en el Catálogo Libre."
      />
    );
  }

  return (
    <div className="space-y-6">
      <section className="surface-card p-6">
        <h1 className="text-2xl font-bold">Hola, {user.full_name}</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          {activeOrg
            ? `Contexto institucional: ${activeOrg.organization_name} (${activeOrg.role_name})`
            : 'Contexto actual: Modo Estudio Libre'}
        </p>

        {gamificationQuery.data && (
          <div className="mt-4 grid grid-cols-3 gap-3">
            <div className="rounded-xl bg-[var(--bg-accent-soft)] p-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-[var(--brand-primary)]">
                <Trophy className="h-4 w-4" /> XP Total
              </div>
              <p className="mt-1 text-xl font-extrabold">{gamificationQuery.data.total_xp}</p>
            </div>
            <div className="rounded-xl bg-amber-50 p-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-800">
                <Flame className="h-4 w-4" /> Racha
              </div>
              <p className="mt-1 text-xl font-extrabold">{gamificationQuery.data.current_streak_days} días</p>
            </div>
            <div className="rounded-xl bg-emerald-50 p-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-800">
                <Battery className="h-4 w-4" /> Energía
              </div>
              <p className="mt-1 text-xl font-extrabold">
                {gamificationQuery.data.current_energy}/{gamificationQuery.data.max_energy}
              </p>
            </div>
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
