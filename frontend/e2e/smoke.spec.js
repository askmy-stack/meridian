import { test, expect } from '@playwright/test';

test.describe('Meridian smoke', () => {
  test('home page loads', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: /Risk Intelligence/i })).toBeVisible();
  });

  test('nav includes copilot and sectors', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('link', { name: 'Copilot' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Sectors' })).toBeVisible();
  });
});
