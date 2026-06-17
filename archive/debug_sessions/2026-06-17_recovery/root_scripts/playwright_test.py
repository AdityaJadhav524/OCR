import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('http://localhost:5173/')
        
        file_path = r'z:\CA\validation_lab\backend\temp\test_password.pdf'
        print(f"Uploading {file_path}...")
        
        # In modern Playwright, we can just locate the input and set_input_files
        await page.locator('#pdf-upload').set_input_files(file_path)
        
        print("Waiting for password modal...")
        await page.wait_for_selector('text=Password Protected PDF', timeout=10000)
        
        # Take screenshot of the password modal
        await page.screenshot(path=r'z:\CA\validation_lab\backend\temp\modal_appeared.png', full_page=True)
        print("Captured modal_appeared.png")
        
        print("Typing wrong password...")
        password_input = page.locator('input[type="password"]')
        await password_input.fill('wrongpassword')
        
        print("Clicking Unlock & Process...")
        await page.locator('button:has-text("Unlock & Process")').click()
        
        print("Waiting for error message...")
        await page.wait_for_selector('text=Incorrect PDF password', timeout=10000)
        await page.screenshot(path=r'z:\CA\validation_lab\backend\temp\incorrect_password.png', full_page=True)
        print("Captured incorrect_password.png")
        
        print("Clearing and typing correct password...")
        await password_input.fill('')
        await password_input.fill('secret123')
        
        # Verify show/hide eye icon works (just click it and check type changes to text, then back to password)
        await page.locator('button:has(svg.lucide-eye)').click()
        # Verify it changed to eye-off
        await page.wait_for_selector('button:has(svg.lucide-eye-off)', timeout=2000)
        # Verify Caps Lock warning simulation (optional)
        
        await page.locator('button:has-text("Unlock & Process")').click()
        
        print("Waiting for pipeline to finish...")
        await page.wait_for_selector('text=Processing Summary', timeout=60000)
        await page.screenshot(path=r'z:\CA\validation_lab\backend\temp\pipeline_finished.png', full_page=True)
        print("Captured pipeline_finished.png")
        
        # Also let's run a normal PDF test just to be sure
        await page.goto('http://localhost:5173/')
        await page.locator('#pdf-upload').set_input_files(r'z:\CA\validation_lab\backend\temp\test_normal.pdf')
        await page.wait_for_selector('text=Processing Summary', timeout=60000)
        await page.screenshot(path=r'z:\CA\validation_lab\backend\temp\pipeline_normal.png', full_page=True)
        print("Captured pipeline_normal.png")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
