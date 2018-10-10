'use strict';

const config = {
  assetDir: './reporter/webapp/static/',
  moduleDir: './node_modules/'
};

const gulp = require('gulp');
const fonts = [
  '/typeface-roboto/files/roboto-latin-300.woff'
];

gulp.task('fonts', () =>
  gulp.src(fonts.map(font => config.moduleDir + font))
    .pipe(gulp.dest(config.assetDir + '/fonts/'))
);
