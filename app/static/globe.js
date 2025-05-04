// static/globe.js
(async () => {
    const globe = Globe()  
      (document.getElementById('globeViz'))

      .globeImageUrl(null)

      .bumpImageUrl('https://unpkg.com/three-globe/example/img/earth-topology.png')
  
      .globeTileEngineUrl((x, y, z) =>
        `https://api.mapbox.com/v4/mapbox.satellite/${z}/${x}/${y}@2x.png?access_token=${window.MAPBOX_KEY}`
      )
  
      .width(window.innerWidth)
      .height(window.innerHeight);
  
    window.addEventListener('resize', () => {
      globe
        .width(window.innerWidth)
        .height(window.innerHeight);
    });
  })();
  