const fs = require('fs');
const { execSync } = require('child_process');

console.log('Build script started in:', process.cwd());

if (fs.existsSync('frontend') && fs.statSync('frontend').isDirectory()) {
  console.log('Found frontend/ directory. Building frontend...');
  execSync('npm install', { cwd: 'frontend', stdio: 'inherit' });
  execSync('npm run build', { cwd: 'frontend', stdio: 'inherit' });
  if (fs.existsSync('frontend/dist')) {
    fs.cpSync('frontend/dist', 'dist', { recursive: true });
    console.log('Copied frontend/dist to ./dist successfully.');
  }
} else {
  console.log('Building from current directory...');
  execSync('npm run build', { stdio: 'inherit' });
}
