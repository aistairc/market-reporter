'use strict';

const gulp = require('gulp');
const googleWebFonts = require('gulp-google-webfonts');
const googleWebFontsOptions = {};

const config = {
  assetDir: '../reporter/webapp/static/',
  moduleDir: './node_modules/'
};
const styles = []

gulp.task('fonts', () =>
  gulp.src('./fonts.list')
    .pipe(googleWebFonts(googleWebFontsOptions))
    .pipe(gulp.dest(config.assetDir + '/fonts'))
);

gulp.task('styles', () =>
  gulp.src(styles.map(style => config.moduleDir + style))
    .pipe(gulp.dest(config.assetDir + '/css/'))
);

gulp.task('default', ['fonts', 'styles']);
