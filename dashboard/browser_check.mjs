// Real Chrome/CDP integration check. No npm dependencies; Node 22+ for WebSocket.
import {spawn, execFileSync} from 'node:child_process';
import {mkdtempSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';

const out = resolve('project-state/dashboard');
const chrome = process.env.DASHBOARD_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const python = process.env.DASHBOARD_PYTHON || 'C:/Users/PC/AppData/Local/Python/pythoncore-3.14-64/python.exe';
const profile = mkdtempSync(join(tmpdir(), 'factory-dashboard-chrome-'));
const child = spawn(chrome, ['--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--remote-debugging-port=9229', '--remote-debugging-address=127.0.0.1', `--user-data-dir=${profile}`, 'about:blank'], {windowsHide:true, stdio:'ignore'});
const sleep = ms => new Promise(r=>setTimeout(r,ms));
const checks=[], errors=[];
let socket;
function check(name, passed){checks.push({name,passed:Boolean(passed)});if(!passed)throw new Error(name);}
try {
  let targets;
  for(let i=0;i<50;i++){try{targets=await (await fetch('http://127.0.0.1:9229/json')).json();break;}catch{await sleep(200);}}
  if(!targets)throw new Error('Chrome CDP did not start');
  socket=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  let id=0;const pending=new Map();
  socket.onmessage=message=>{const data=JSON.parse(message.data);if(data.method==='Runtime.exceptionThrown')errors.push(data.params.exceptionDetails.text);if(data.id){const p=pending.get(data.id);pending.delete(data.id);data.error?p.reject(new Error(JSON.stringify(data.error))):p.resolve(data.result);}};
  const call=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});socket.send(JSON.stringify({id:n,method,params}));});
  const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
  await call('Runtime.enable');
  await call('Page.enable');
  await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:'http://localhost:8787/'});
  for(let i=0;i<50;i++){if(await evaluate('document.querySelectorAll(".node").length === 7'))break;await sleep(200);}
  check('Seven real agent nodes',await evaluate('document.querySelectorAll(".node").length === 7'));
  check('Connected API',await evaluate('document.getElementById("connection").textContent.includes("conectada")'));
  await evaluate('document.getElementById("project").value="calculadora_demo";document.getElementById("project").dispatchEvent(new Event("change"))');
  check('Existing calculator selected',await evaluate('document.getElementById("project-name").textContent === "calculadora_demo"'));
  check('Calculator complete and specialties omitted',await evaluate('document.getElementById("project-status").textContent === "Terminado" && document.querySelectorAll(".node.skipped").length === 6 && document.querySelectorAll(".node.working").length === 0'));
  check('Real historical calculator command',await evaluate('document.getElementById("detail-tests").textContent.includes("node --test tests/calculator.test.js")'));
  await evaluate('document.querySelectorAll(".node")[2].click()');
  check('Backend inspector with no invented task',await evaluate('document.getElementById("detail-title").textContent === "Backend" && document.getElementById("detail-status").textContent.includes("Omitido")'));
  await evaluate('document.querySelector(".node").click()');
  let shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
  writeFileSync(join(out,'calculator-dashboard.png'),Buffer.from(shot.data,'base64'));
  await evaluate('document.getElementById("project").value="dashboard";document.getElementById("project").dispatchEvent(new Event("change"))');
  const marker=`Browser observation ${Date.now()}`;
  execFileSync(python,['-B','-S','-m','factory.activity','--project','dashboard','--type','command_executed','--message',marker,'--command','Chrome CDP: inspect dashboard nodes and historical calculator','--returncode','0'],{windowsHide:true});
  for(let i=0;i<40;i++){if(await evaluate(`document.getElementById("events").textContent.includes(${JSON.stringify(marker)})`))break;await sleep(200);}
  check('New real operational event appears without reload',await evaluate(`document.getElementById("events").textContent.includes(${JSON.stringify(marker)})`));
  shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
  writeFileSync(join(out,'dashboard-desktop.png'),Buffer.from(shot.data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  check('No mobile horizontal overflow',await evaluate('document.documentElement.scrollWidth <= 390'));
  shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
  writeFileSync(join(out,'dashboard-mobile.png'),Buffer.from(shot.data,'base64'));
  check('No JavaScript runtime errors',errors.length===0);
  check('Evidence timestamp distinct from polling timestamp',await evaluate('document.getElementById("updated").textContent.includes("Última evidencia:") && document.getElementById("updated").textContent.includes("Consultado:")'));
  // In-memory fixtures below exercise edge cases; no synthetic factory events are written.
  check('Fixture: historical run errors visible',await evaluate('drawDetails({...getProject(),runs:[{command:"fixture failure",returncode:2,timed_out:true}]});document.getElementById("detail-errors").textContent.includes("fixture failure")'));
  check('Fixture: duration uses newest execution',await evaluate('drawDuration({status:"completed",events:[{type:"project_started",timestamp:"2026-01-01T00:00:00Z"},{type:"project_finished",timestamp:"2026-01-01T00:01:00Z"},{type:"project_started",timestamp:"2026-01-02T00:00:00Z"},{type:"project_finished",timestamp:"2026-01-02T00:00:10Z"}]});document.getElementById("duration").textContent === "10.0 s"'));
  check('Fixture: empty dataset clears previous project',await evaluate('snapshot={projects:[],current_project:null};render();document.querySelectorAll(".node").length === 0 && document.getElementById("detail-tests").textContent.indexOf("fixture failure") === -1 && document.getElementById("project-name").textContent !== "dashboard"'));
  writeFileSync(join(out,'browser-check.json'),JSON.stringify({timestamp:new Date().toISOString(),browser:chrome,checks,errors,profile},null,2));
  console.log(JSON.stringify({passed:checks.length,checks},null,2));
} catch(error) {
  writeFileSync(join(out,'browser-check.json'),JSON.stringify({timestamp:new Date().toISOString(),checks,errors,error:String(error)},null,2));
  console.error(error);process.exitCode=1;
} finally {
  if(socket)socket.close();
  if(child.pid){try{execFileSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}catch{}}
}
