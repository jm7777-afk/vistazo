import { expect, test } from '@playwright/test';

test.describe('Vistazo LMS — Smoke E2E', () => {
  test('landing page and catalog render without errors', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('body')).toContainText(/Vistazo/i);

    await page.goto('/catalog');
    await expect(page).toHaveURL(/\/catalog/);
  });

  test('registration form asks educator vs student role', async ({ page }) => {
    await page.goto('/register');
    await expect(page.getByText(/educador/i).first()).toBeVisible();
    await expect(page.getByText(/estudiante/i).first()).toBeVisible();
  });

  test('public routes /familia, /unirse, and /planes load cleanly on direct refresh', async ({ page }) => {
    await page.goto('/familia');
    await expect(page.getByText(/Portal de Familias/i)).toBeVisible();

    await page.goto('/unirse');
    await expect(page).toHaveURL(/\/unirse/);

    await page.goto('/planes');
    await expect(page.getByText(/Planes SaaS/i)).toBeVisible();
  });
});
