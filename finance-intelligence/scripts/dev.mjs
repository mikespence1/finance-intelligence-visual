import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const localPython = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.PYTHON || (existsSync(localPython) ? localPython : 'python');
const jobs = [
  spawn(python, ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000', '--reload'], { cwd: root, stdio: 'inherit' }),
  spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1'], { cwd: path.join(root, 'frontend'), stdio: 'inherit' }),
];
let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const job of jobs) {
    if (!job.pid) continue;
    if (process.platform === 'win32') {
      spawn('taskkill', ['/PID', String(job.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
    } else job.kill('SIGTERM');
  }
  process.exitCode = code;
}
for (const job of jobs) {
  job.on('error', error => { console.error(error.message); stop(1); });
  job.on('exit', code => { if (!stopping) stop(code || 0); });
}
process.on('SIGINT', () => stop());
process.on('SIGTERM', () => stop());
