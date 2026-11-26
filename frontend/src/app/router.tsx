import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { LoginPage, RegisterPage } from '../pages/AuthPages';
import { CatalogPage } from '../pages/CatalogPage';
import { MyCertificatesPage, VerifyCertificatePage } from '../pages/CertificatesPage';
import { CourseDetailPage } from '../pages/CourseDetailPage';
import { DashboardPage } from '../pages/DashboardPage';
import { LessonPlayerPage } from '../pages/LessonPlayerPage';
import { CoordinatorPage, InstructorPage, ProfilePage, SuperAdminPage } from '../pages/RoleDashboards';
import { SpacedReviewPage } from '../pages/SpacedReviewPage';
import { VisualLibraryPage } from '../pages/VisualLibraryPage';

export function AppRouter() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Navigate to="/catalog" replace />} />
          <Route path="/catalog" element={<CatalogPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/reviews" element={<SpacedReviewPage />} />
          <Route path="/library" element={<VisualLibraryPage />} />
          <Route path="/certificates" element={<MyCertificatesPage />} />
          <Route path="/verificar-certificado/:hash" element={<VerifyCertificatePage />} />
          <Route path="/courses/:courseId" element={<CourseDetailPage />} />
          <Route path="/lessons/:lessonVersionId" element={<LessonPlayerPage />} />
          <Route path="/instructor" element={<InstructorPage />} />
          <Route path="/coordinator" element={<CoordinatorPage />} />
          <Route path="/admin" element={<SuperAdminPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
