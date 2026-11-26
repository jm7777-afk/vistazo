import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Award, BookOpen, GraduationCap } from 'lucide-react';
import { EmptyState, ErrorBanner, LoadingState } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { ClassroomOut, CourseSummary, LessonProgressOut, StudentCompetencyOut } from '../types/api';

export function DashboardPage() {
  const { user, activeOrg } = useAppState();

  const classroomsQuery = useQuery({
    queryKey: ['my-classrooms', activeOrg?.organization_id],
    queryFn: () => apiRequest<ClassroomOut[]>(`/orgs/${activeOrg!.organization_id}/classrooms`),
    enabled: Boolean(user && activeOrg),
  });

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

      {activeOrg && (
        <section className="space-y-3">
          <h2 className="text-lg font-bold">Aulas y cursos de {activeOrg.organization_name}</h2>
          {classroomsQuery.isLoading || orgCoursesQuery.isLoading ? (
            <LoadingState label="Cargando aulas institucionales..." />
          ) : classroomsQuery.error ? (
            <ErrorBanner message={(classroomsQuery.error as Error).message} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {(orgCoursesQuery.data ?? []).map((course) => {
                const classroomId = classroomsQuery.data?.[0]?.id;
                return (
                  <div key={course.id} className="surface-card flex flex-col justify-between p-5">
                    <div>
                      <span className="rounded-full bg-[var(--bg-accent-soft)] px-2.5 py-0.5 text-xs font-semibold text-[var(--brand-primary)]">
                        {course.education_level}
                      </span>
                      <h3 className="mt-2 text-base font-bold">{course.title}</h3>
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">{course.description}</p>
                    </div>
                    <Link
                      to={`/courses/${course.id}${classroomId ? `?classroomId=${classroomId}` : ''}`}
                      className="btn-primary mt-4 inline-flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-semibold"
                    >
                      <BookOpen className="h-4 w-4" /> Entrar al curso
                    </Link>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
