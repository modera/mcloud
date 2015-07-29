'use strict';

var config = require('./build.config.js');
var gulp = require('gulp');
var $ = require('gulp-load-plugins')();
var runSequence = require('run-sequence');
var browserSync = require('browser-sync');
var reload = browserSync.reload;
var pkg = require('./package');
var del = require('del');
var _ = require('lodash');
/* jshint camelcase:false*/
var exec = require('child_process').exec;


//build files for development
gulp.task('build', [], function(cb) {

    exec('make html', function(err) {
        if (err) return cb(err); // return error
        cb(); // finished task
    });

});
//build files for development
gulp.task('build_site', [], function(cb) {

    exec('jekyll build', {cwd: 'source/themes/cloud.modera.org/jekyll'}, function(err) {
        if (err) return cb(err); // return error
        cb(); // finished task
    });

});

//default task
gulp.task('default', ['serve']); //

//gulp.task('python_server', bg("./.env/bin/cratis", ["runserver", '0.0.0.0:8000']));

gulp.task('serve', ['build'], function() {
  browserSync({
    notify: false,
    ghostMode: false,
    logPrefix: pkg.name,
    server: [
//        'build/html',
        'source/themes/cloud.modera.org/public'
    ]
  });

  gulp.watch(config.source, ['build', reload]);
  gulp.watch(config.site_doc_theme, ['build', reload]);
  gulp.watch(config.site_source, ['build_site', reload]);
});
