const { src, dest, parallel } = require('gulp');

function buildIcons() {
  return src('nodes/**/*.svg')
    .pipe(dest('dist/nodes'));
}

function copyWrapper() {
  return src('bitnet-server-wrapper.js')
    .pipe(dest('dist'));
}

function copyEnvFile() {
  return src('.env.bitnet')
    .pipe(dest('dist'));
}

exports['build:icons'] = parallel(buildIcons, copyWrapper, copyEnvFile);