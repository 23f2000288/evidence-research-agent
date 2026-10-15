/* Capture an actual rendered local browser tour. No fabricated run events.
   Optional: npm install --save-dev playwright && npx playwright install chromium
   Run node demo/record_demo.cjs after starting python demo_server.py.
   Override PLAYWRIGHT_MODULE to reuse an existing Playwright installation. */
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
(async()=>{
  const directory=__dirname;
  const browser=await chromium.launch({headless:true,
    ...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{})});
  const context=await browser.newContext({viewport:{width:1600,height:900},
    recordVideo:{dir:directory,size:{width:1600,height:900}}});
  const page=await context.newPage();
  const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.goto('http://127.0.0.1:8765/?tour=1');
  console.log('Recording a fresh 2:42 browser tour, with 3 seconds of lead-in.');
  const video=page.video();
  // The application performs its own timed tour and starts a real Python run.
  // This script records the rendered viewport without simulating run output.
  await new Promise(resolve=>setTimeout(resolve,166000));
  await context.close();
  const file=await video.path();
  const target=path.join(directory,'screen-recording.webm');
  fs.renameSync(file,target);
  fs.writeFileSync(path.join(directory,'recording-log.json'),JSON.stringify({
    type:'scripted browser screen capture',viewport:'1600x900',seconds:166,
    captions:true,synthetic_narration:false,errors
  },null,2));
  await browser.close();
  console.log('Saved '+target);
})().catch(error=>{console.error(error);process.exitCode=1});
