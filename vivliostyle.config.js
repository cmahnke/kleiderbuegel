module.exports = {
  title: 'Kleiderbügel', 
  author: 'Christian Mahnke',
  language: 'de',
  //image: 'ghcr.io/vivliostyle/cli:latest',
  entry: ['docs/print.html'],
  static: {
    '/__vivliostyle-viewer/js/': 'docs/js/',
    '/__vivliostyle-viewer/images/': 'docs/images/',
    '/vivliostyle/docs/': 'docs/',
    '/catalogue/': 'docs/catalogue/',
  },
};