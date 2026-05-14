import { expect, test } from '@playwright/test';

test('fiscal investigation connectors and ranking flow', async ({ page, request }) => {
  const apiBase = process.env.E2E_API_BASE_URL || process.env.REACT_APP_API_URL || 'http://127.0.0.1:18001';

  const seed = await request.post(`${apiBase}/fiscal-investigation/demo-seed`);
  expect(seed.ok()).toBeTruthy();
  const seedJson = await seed.json();
  const demoCpf = seedJson?.seed?.cpf || '11111111111';

  const donations = await request.post(`${apiBase}/fiscal-investigation/sync/donations`, {
    data: {
      ano: 2024,
      csv_url: 'http://127.0.0.1:3000/tse-doacoes-sample.csv',
      max_linhas: 1000,
    },
  });
  const donationsJson = await donations.json();
  console.log('SYNC DONATIONS RESPONSE:', donationsJson);
  expect(donations.ok()).toBeTruthy();
  expect(donationsJson?.result?.registros_doacao_upsert).toBeGreaterThan(0);

  const salarySync = await request.post(`${apiBase}/fiscal-investigation/sync/portal-transparencia`, {
    data: { mes_ano: 202501, max_servidores: 5 },
  });
  const salaryJson = await salarySync.json();
  console.log('SYNC SALARY RESPONSE:', salaryJson);
  expect(salarySync.ok()).toBeTruthy();
  expect(salaryJson?.success).toBeTruthy();
  expect(salaryJson?.result?.processados).toBeGreaterThan(0);

  const fundingSync = await request.post(`${apiBase}/fiscal-investigation/sync/public-financing`, {
    data: { ano: 2024, max_paginas: 2 },
  });
  const fundingJson = await fundingSync.json();
  console.log('SYNC PUBLIC FINANCING RESPONSE:', fundingJson);
  expect(fundingSync.ok()).toBeTruthy();
  expect(fundingJson?.success).toBeTruthy();

  const analyze = await request.post(`${apiBase}/fiscal-investigation/analyze`);
  const analyzeJson = await analyze.json();
  console.log('ANALYZE RESPONSE:', analyzeJson);
  expect(analyze.ok()).toBeTruthy();

  const ranking = await request.get(`${apiBase}/fiscal-investigation/people-ranking?limit=100`);
  const rankingJson = await ranking.json();
  console.log('RANKING SAMPLE:', rankingJson?.dados?.slice?.(0, 3));
  expect(ranking.ok()).toBeTruthy();
  expect(rankingJson.total).toBeGreaterThan(0);

  const cpfReport = await request.get(`${apiBase}/fiscal-investigation/analyze/${demoCpf}`);
  const cpfReportJson = await cpfReport.json();
  console.log('CPF REPORT SAMPLE:', cpfReportJson?.report?.summary);
  expect(cpfReport.ok()).toBeTruthy();
  expect(cpfReportJson?.report?.found).toBeTruthy();

  // UI assertions
  page.on('response', async (response) => {
    const url = response.url();
    if (url.includes('/fiscal-investigation/')) {
      const body = await response.text();
      console.log('UI RESPONSE', response.status(), url, body.slice(0, 300));
    }
  });

  await page.goto('/');
  await page.getByRole('button', { name: 'Investigação Patrimonial' }).click();
  await page.getByRole('button', { name: 'Redação ON' }).click();
  await page.locator('input[placeholder=\"000.000.000-00\"]').fill(demoCpf);
  await page.getByRole('button', { name: 'Analisar CPF' }).click();

  await expect(page.getByRole('heading', { name: 'Investigação Patrimonial' }).first()).toBeVisible();
  await expect(page.getByText(/Exposição total/i)).toBeVisible();
  await expect(page.getByText(/Linha do tempo/i)).toBeVisible();
  await expect(page.getByText(/P10|Enriquecimento ilícito/i).first()).toBeVisible();

  // ensure suspicion level badges render
  const levelCell = page.getByText(/Crítico|Alto|Médio|Baixo|MINIMO|SEM_DADOS/i).first();
  await expect(levelCell).toBeVisible();
});
