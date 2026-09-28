// QA script for the AASTMT website
export default async function run(page, ui) {
  const result = {
    title: await page.title(),
    heroH1: await page.evaluate(() => {
      const h1 = document.querySelector('.hero h1');
      return h1 ? h1.innerText.trim() : null;
    }),
    collegeCount: await page.evaluate(() => document.querySelectorAll('.college').length),
    navLinkCount: await page.evaluate(() => document.querySelectorAll('.nav-links a').length),
    terminalLines: await page.evaluate(() => document.querySelectorAll('#termBody > div').length),
    compareRows: await page.evaluate(() => document.querySelectorAll('.compare-row').length),
    formFields: await page.evaluate(() => document.querySelectorAll('#applyForm input, #applyForm select, #applyForm textarea').length),
    bodyChars: (await page.content()).length,
    primaryBtn: await page.evaluate(() => {
      const b = document.querySelector('.btn.btn-primary');
      return b ? b.innerText.trim() : null;
    }),
  };

  // Test the admission form flow
  await page.locator('#firstName').fill('Test');
  await page.locator('#lastName').fill('User');
  await page.locator('#email').fill('test@aastmt.edu');
  await page.locator('#phone').fill('+20 100 000 0000');
  await page.locator('#country').selectOption('Egypt');
  // Wait for colleges to populate
  await page.waitForFunction(() => {
    const sel = document.getElementById('college');
    return sel && sel.options.length > 1;
  });
  await page.locator('#college').selectOption({ index: 1 });
  await page.locator('#message').fill('Automated QA submission');
  await page.locator('button[type="submit"]').click();

  // Wait for status to appear
  await page.waitForSelector('.form-status.ok', { timeout: 10000 });
  const statusText = await page.locator('.form-status.ok').innerText();
  result.formSubmitStatus = statusText;

  // Try scrolling to admission section
  await page.evaluate(() => document.getElementById('admission').scrollIntoView());
  await page.waitForTimeout(300);

  return result;
}
