'use strict';

//basic configuration object used by gulp tasks
module.exports = {
  port: 3000,
  tmp: 'var/build/tmp',
  dist: 'var/build/dist',
  base: 'client',
  source: [
    'source/**/*'
  ],
  site_source: [
    'source/themes/cloud.modera.org/jekyll/**/*'
  ],
  site_doc_theme: [
    'source/themes/cloud.modera.org/docs_theme/**/*'
  ],
  banner: ['/**',
    ' * <%= pkg.name %> - <%= pkg.description %>',
    ' * @version v<%= pkg.version %>',
    ' * @link <%= pkg.homepage %>',
    ' * @license <%= pkg.license %>',
    ' */',
    ''
  ].join('\n')
};
