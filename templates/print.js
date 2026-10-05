/* ==========================================================================
   templates/print.js · Paginador del informe

   PORTADO de ~/propuestas/print.js, que ya funciona. Lo que cambia:
   - lee el esquema de config unificado (meta / hallazgos / modulos / nextSteps)
     en vez del esquema viejo (hero / modules / pricingContext)
   - el config y los fragmentos de marca llegan ya inyectados por generate.py
     (window.CLIENT_CONFIG y window.BRAND_PARTS), así funciona desde file://
     sin fetch y el informe queda en un solo archivo
   - usa las clases de brand.css (.finding, .price-table, .callout, .base-card,
     .scope, .brand-header, .brand-footer). No inventa estilos de marca.

   NO cambiar el paginador: cada hoja es un <div class="page"> de 210x296mm con
   membrete y pie ADENTRO, y el contenido se reparte midiendo el desborde real.
   ========================================================================== */

(function () {
  'use strict';

  var params = new URLSearchParams(location.search);
  var cfg = window.CLIENT_CONFIG || null;
  var BRAND = window.BRAND_PARTS || { header: '', footer: '' };

  var docEl = function () { return document.getElementById('doc'); };
  var money = function (n) { return 'USD ' + Number(n || 0).toLocaleString('es-AR'); };
  var esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  // Sin no-print: si el documento falla, el PDF tiene que decirlo.
  function banner(msg) {
    var d = el('div', 'banner', 'Error al armar el documento: ' + esc(msg));
    document.body.appendChild(d);
  }

  // ---------------- Importes (calculados, nunca escritos a mano) ----------------

  function priceOf(m) { return Number(m.price || 0); }

  function totals() {
    var base = Number((cfg.base || {}).precio || 0);
    var mods = cfg.modulos || [];
    var sum = mods.reduce(function (a, m) { return a + priceOf(m); }, 0);
    var pack = Math.round((base + sum) * 0.85 / 5) * 5;
    var p = mods.map(priceOf);
    var combo2 = base + (p[0] || 0) + (p[1] || 0);
    var combo3 = combo2 + (p[2] || 0);
    return { base: base, sum: sum, total: base + sum, pack: pack, combo2: combo2, combo3: combo3 };
  }

  // ---------------- Paginador ----------------

  var sheets = [];
  var body = null;
  var contLabel = '';

  function emptySheet() {
    var p = el('div', 'page');
    p.innerHTML = (BRAND.header || '') +
      '<div class="page__body"></div>' +
      (BRAND.footer || '');
    docEl().appendChild(p);
    sheets.push(p);
    p.id = 'hoja-' + sheets.length;
    return p;
  }

  function openSheet(label) {
    contLabel = label || '';
    var p = emptySheet();
    body = p.querySelector('.page__body');
    if (contLabel) body.appendChild(el('div', 'cont-label', esc(contLabel)));
    return body;
  }

  /**
   * ¿El cuerpo de la hoja se desborda?
   * scrollHeight > clientHeight no alcanza: no incluye el margen inferior del
   * último hijo y subestima con grillas. Se mide además la caja real de cada
   * hijo, y se exige el margen de seguridad (la media de impresión no coincide
   * con la de pantalla, así que algo que "entra raspando" sale cortado).
   */
  function overflows(clear) {
    if (!body) return false;
    if (body.scrollHeight > body.clientHeight + 1) return true;
    var limit = body.getBoundingClientRect().bottom - (clear || 0);
    for (var i = 0; i < body.children.length; i++) {
      if (body.children[i].getBoundingClientRect().bottom > limit + 1) return true;
    }
    return false;
  }

  // 14mm: umbral medido entre 8 y 12. Ajustable con ?clear=<mm> para calibrar.
  var CLEARANCE_PX = Number(params.get('clear') || 14) * 3.7795;

  function tryFit(node) {
    if (!body) openSheet();
    body.appendChild(node);
    if (overflows(CLEARANCE_PX)) { body.removeChild(node); return false; }
    return true;
  }

  function place(node, label) {
    if (!tryFit(node)) { openSheet(label || contLabel); tryFit(node); }
  }

  function flow(nodes, label) {
    nodes.forEach(function (n) { place(n, label); contLabel = label; });
  }

  // ---------------- Bloques ----------------

  function secHead(num, title) {
    return el('div', 'sec-head',
      '<span class="sec-num">' + esc(num) + '</span><h2 class="sec-title">' + esc(title) + '</h2>');
  }

  function findingCard(h) {
    var tipo = String(h.tipo || '[MEDIDO]');
    var cls = tipo.indexOf('INFERIBLE') >= 0 ? 'tag-inferible' : 'tag-medido';
    var prio = String(h.prioridad || '').toLowerCase();
    var prioTag = prio
      ? '<span class="tag tag-prio-' + esc(prio) + '">Prioridad ' + esc(prio) + '</span>'
      : '';
    return el('div', 'finding',
      '<div class="finding-head">' +
        '<span class="tag ' + cls + '">' + esc(tipo) + '</span>' +
        prioTag +
        '<span class="finding-title">' + esc(h.titulo) + '</span>' +
      '</div>' +
      '<p>' + esc(h.descripcion) + '</p>' +
      '<div class="finding-meta">' +
        '<span>Impacto estimado: <strong>' + esc(h.impacto) + '</strong></span>' +
        '<span class="tag">[INFERIBLE]</span>' +
      '</div>');
  }

  function callout(label, paragraphs) {
    return el('div', 'callout',
      '<div class="callout-label">' + esc(label) + '</div>' +
      paragraphs.map(function (p) { return '<p class="callout-note">' + esc(p) + '</p>'; }).join(''));
  }

  // ---------------- Portada ----------------

  function buildCover() {
    var m = cfg.meta || {};
    var author = (cfg.author || {}).nombre || 'Lisandro Cacciatore';
    var email = (cfg.author || {}).email || '';
    var t = totals();
    var sheet = el('div', 'page page--cover',
      '<div class="cover">' +
        '<div class="cover__eyebrow">Informe de Valor</div>' +
        '<h1 class="cover__title">' + esc(m.nombre) + '</h1>' +
        '<p class="cover__subtitle">' + esc(m.profesion || '') + '</p>' +
        '<div class="cover__client">' +
          '<div class="cover__client-label">Preparado para</div>' +
          '<div class="cover__client-name">' + esc(m.nombre) + '</div>' +
          '<div class="cover__client-sub">' + esc(m.matricula || '') +
            (m.rubro ? ' · ' + esc(m.rubro) : '') + '</div>' +
          (m.url ? '<div class="cover__client-sub">' + esc(m.url) + '</div>' : '') +
        '</div>' +
        '<div class="cover__meta">' +
          '<div><strong>Fecha</strong>' + esc(m.fecha || '') + '</div>' +
          '<div><strong>Válido hasta</strong>' + esc(m.validez || '') + '</div>' +
          '<div><strong>Preparado por</strong>' + esc(author) +
            (email ? '<br>' + esc(email) : '') + '</div>' +
        '</div>' +
      '</div>');
    docEl().appendChild(sheet);
    sheets.push(sheet);
    sheet.id = 'hoja-' + sheets.length;
    return sheet;
  }

  // ---------------- Documento ----------------

  /* Secciones del informe.
     Las marcadas como `optional` sólo entran si la config trae su dato: así el
     mismo paginador sirve para un informe corto y para uno con comparativo
     verificado, sin numerar huecos. La numeración se asigna después de filtrar. */
  var ALL_SECTIONS = [
    { id: 'resumen',     title: 'Resumen Ejecutivo' },
    { id: 'diagnostico', title: 'Diagnóstico' },
    { id: 'comparativo', title: 'Comparativo verificado', optional: true },
    { id: 'alcance',     title: 'Alcance de esta revisión' },
    { id: 'cierre',      title: 'Qué propongo hacer con esto' }
  ];

  function resolveSections() {
    var comp = cfg.comparativo || {};
    // La tabla puede ser de pares medidos (va al informe) o un comparativo de mercado
    // orientativo (sólo tiene sentido en la propuesta, no bajo el título "verificado").
    var tieneComparativo = (comp.filas || []).length > 0 && comp.mostrarEnInforme !== false;
    return ALL_SECTIONS.filter(function (s) {
      return !s.optional || tieneComparativo;
    }).map(function (s, i) {
      return { id: s.id, num: ('0' + (i + 1)).slice(-2), title: s.title };
    });
  }

  function compareTable(comp) {
    var cols = comp.columnas || [];
    var head = '<thead><tr>' + cols.map(function (c) { return '<th>' + esc(c) + '</th>'; }).join('') + '</tr></thead>';
    var rows = (comp.filas || []).map(function (f) {
      var celdas = (f.celdas || []).map(function (c, i) {
        var txt = String(c);
        var cls = '';
        if (i > 0) {
          if (/^(200|✓)/.test(txt)) cls = 'ok';
          else if (/✗|404|0$|no resuelve|bloqueó/.test(txt)) cls = 'bad';
          else if (txt === '—') cls = 'meh';
        }
        return '<td class="' + cls + '">' + esc(txt) + '</td>';
      }).join('');
      return '<tr class="' + (f.cliente ? 'row-client' : '') + '">' + celdas + '</tr>';
    }).join('');
    return '<table class="compare-table">' + head + '<tbody>' + rows + '</tbody></table>';
  }

  function kpiRow(kpis) {
    // §4.1 del spec editorial: máximo 4 números en el cuadro.
    kpis = (kpis || []).slice(0, 4);
    if (!(kpis || []).length) return null;
    return el('div', 'kpi-row', kpis.map(function (k) {
      return '<div class="kpi"><span class="kpi__value">' + esc(k.valor) +
             '</span><span class="kpi__label">' + esc(k.label) + '</span></div>';
    }).join(''));
  }

  function buildDocument() {
    try {
      var m = cfg.meta || {};
      var hallazgos = cfg.hallazgos || [];
      var modulos = cfg.modulos || [];
      var pasos = cfg.nextSteps || [];
      var t = totals();

      var SECTIONS = resolveSections();
      var NUM = {};
      SECTIONS.forEach(function (s) { NUM[s.id] = s.num; });

      docEl().innerHTML = '';
      sheets.length = 0;

      buildCover();

      // Índice: se crea ahora para fijar su lugar, se llena al final.
      var tocSheet = emptySheet();
      var tocBody = tocSheet.querySelector('.page__body');
      tocBody.appendChild(secHead('', 'Índice del informe'));

      var startOf = {};

      // --- 01 Resumen Ejecutivo
      openSheet();
      startOf.resumen = sheets.length;
      body.appendChild(secHead(NUM.resumen, 'Resumen Ejecutivo'));
      var resumenLead = 'Sobre ' + esc(m.url || 'su presencia online') + ' se midieron <strong>' +
        hallazgos.length + ' hallazgos</strong> que están costando oportunidades. ';
      // §7.1: la tarifa del profesional se nombra UNA sola vez, en la sección de costo.
      // Acá va sin monto: la cuenta está abajo, a la vista.
      resumenLead += cfg.costoMensual
        ? 'La cuenta de lo que eso cuesta por mes está en la sección de costo, con el cálculo a la vista.'
        : 'No declaro un impacto en pesos porque no tengo acceso a tus números: ' +
          'lo que sigue es lo medido, con la cuenta a la vista.';
      body.appendChild(el('p', 'sec-lead', resumenLead));
      place(el('ul', '', hallazgos.map(function (h) {
        return '<li><strong>' + esc(h.titulo) + '</strong> — ' + esc(h.impacto) + '</li>';
      }).join('')));

      // Los indicadores van acá, en el resumen: es lo que se lee si sólo se lee una hoja.
      var kpisResumen = kpiRow((cfg.comparativo || {}).kpis || []);
      if (kpisResumen) place(kpisResumen);
      place(el('div', 'scope',
        '<div class="scope-label">Cómo leer este informe</div>' +
        '<ul>' +
          '<li><span class="yes">✓</span> <strong>[MEDIDO]</strong>: sale de una medición sobre el HTML servido ' +
            'del sitio, verificable con los comandos que figuran en «Alcance de esta revisión».</li>' +
          '<li><span class="no">✗</span> <strong>[INFERIBLE]</strong>: es una estimación. El impacto real ' +
            'depende de tu operación, que este informe no ve.</li>' +
          '<li><span class="no">✗</span> <strong>[NO VERIFICADO]</strong>: no se pudo comprobar y por lo tanto ' +
            'no se afirma. Es el caso de LinkedIn, que responde con muro de registro.</li>' +
        '</ul>'));

      // --- 02 Diagnóstico
      openSheet();
      startOf.diagnostico = sheets.length;
      body.appendChild(secHead(NUM.diagnostico, 'Diagnóstico'));
      var nComp = Number(cfg.comparativos || 0);
      var diagLead = 'Se analizó el HTML servido de ' + esc(m.url || '') + ' el ' + esc(m.fecha || '') + '. ';
      if (nComp >= 2) {
        diagLead += 'Se comparó contra ' + nComp + ' referencias del mismo rubro, medidas el mismo día ' +
          'con la misma herramienta. ';
      } else if (nComp === 1) {
        diagLead += 'Se comparó contra una referencia del rubro, con la misma herramienta y el mismo día. ';
      }
      diagLead += 'Cada número de este informe es reproducible.';
      body.appendChild(el('p', 'sec-lead', diagLead));
      body.appendChild(el('div', 'sec-sub', 'Hallazgos'));
      flow(hallazgos.map(findingCard), 'Diagnóstico · continúa');
      var co = cfg.callout || {};
      place(callout(co.label || 'Costo de no hacer nada', [
        co.strong || ('Seguir así cuesta ' + (cfg.costoMensual || '') + ' por mes.'),
        co.note || ('Cálculo basado en ' + (cfg.baseCalculo || '') + ' · [INFERIBLE]')
      ]), 'Diagnóstico · continúa');

      // --- 03 Comparativo verificado (opcional: sólo si la config lo trae)
      var comp = cfg.comparativo || {};
      if (NUM.comparativo && (comp.filas || []).length) {
        openSheet();
        startOf.comparativo = sheets.length;
        body.appendChild(secHead(NUM.comparativo, 'Comparativo verificado'));
        if (comp.intro) body.appendChild(el('p', 'sec-lead', esc(comp.intro)));
        place(el('div', '', compareTable(comp)), 'Comparativo verificado · continúa');
        if (comp.nota) place(el('p', 'evsrc', esc(comp.nota)), 'Comparativo verificado · continúa');
        if (comp.medidoEl) {
          place(el('p', 'evsrc', 'Medición propia del ' + esc(comp.medidoEl) +
            ' · reproducible con: python scripts/medir.py --pares 00-auditoria/pares.txt'),
            'Comparativo verificado · continúa');
        }
      }

      // --- §4: acá NO va la propuesta ni la inversión. El informe es diagnóstico;
      // la solución, los precios y la aceptación viven en /propuesta/ y se enlazan
      // en la sección de cierre.


      // --- Alcance de esta revisión
      openSheet();
      startOf.alcance = sheets.length;
      body.appendChild(secHead(NUM.alcance, 'Alcance de esta revisión'));
      // El alcance sale de la config: qué se midió (✓) y qué no se pudo (✗).
      var alcance = cfg.alcance || [];
      var alcanceHTML = alcance.length
        ? alcance.map(function (a) {
            var t = String(a).trim();
            var marca = t.charAt(0);
            var yes = marca === '✓';
            var resto = (marca === '✓' || marca === '✗') ? t.slice(1).trim() : t;
            return '<li><span class="' + (yes ? 'yes' : 'no') + '">' + (yes ? '✓' : '✗') +
                   '</span> ' + esc(resto) + '</li>';
          }).join('')
        : '<li><span class="yes">✓</span> Se midió el HTML servido de ' + esc(m.url || '') +
          ' el ' + esc(m.fecha || '') + '.</li>';
      body.appendChild(el('div', 'scope', '<ul>' + alcanceHTML + '</ul>'));

      // --- Cierre (§4.6): el informe es diagnóstico, no vende. Manda a la propuesta.
      openSheet();
      startOf.cierre = sheets.length;
      body.appendChild(secHead(NUM.cierre, 'Qué propongo hacer con esto'));
      body.appendChild(el('p', 'sec-lead',
        'Este documento es el diagnóstico: qué se midió y qué está costando. La solución, ' +
        'con lo que incluye cada bloque y lo que cuesta, va en la propuesta.'));
      place(el('div', 'scope', '<ul>' +
        '<li><span class="yes">✓</span> Cada hallazgo de este informe tiene su bloque asociado ' +
          'en la propuesta: nada queda en el aire.</li>' +
        '<li><span class="yes">✓</span> Los precios, los escenarios y la aceptación están sólo en ' +
          'la propuesta, para que este informe no mezcle diagnóstico con venta.</li>' +
        '</ul>'), 'Cierre · continúa');
      place(el('div', 'cta-row',
        '<a class="btn btn-ink" href="../propuesta/">Ver la propuesta &rarr;</a> ' +
        '<a class="btn btn-light" href="../">Volver al inicio &rarr;</a>'), 'Cierre · continúa');

      // 4. Membrete y numeración en todas las hojas menos la portada.
      var total = sheets.length;
      sheets.forEach(function (sheet, i) {
        if (sheet.classList.contains('page--cover')) return;
        var meta = sheet.querySelector('.brand-footer-meta');
        if (meta) meta.textContent = meta.textContent + ' · Página ' + (i + 1) + ' de ' + total;
      });

      // 5. Índice, ya con las hojas resueltas.
      var tocList = el('ol', 'toc');
      SECTIONS.forEach(function (sec) {
        var n = startOf[sec.id];
        if (!n) return;
        tocList.appendChild(el('li', '',
          '<a href="#hoja-' + n + '"><span class="toc__item-name">' + esc(sec.title) +
          '</span><span class="toc__item-page">Página ' + n + '</span></a>'));
      });
      tocBody.appendChild(tocList);
      tocBody.appendChild(el('p', '',
        '<span style="font-size:9pt;color:var(--ink-muted)">El total de este informe es de ' +
        total + ' páginas.</span>'));

      // 6. Auto-verificación: ninguna hoja puede quedar con contenido cortado.
      //
      // Dos medidas, porque solas mienten:
      //   · scrollHeight cuenta los margenes de cierre, que no son contenido y no se
      //     recortan: una diferencia de pocos pixeles ahi es un falso positivo. Por eso
      //     se tolera un resto chico.
      //   · La prueba que manda es geometrica: ningún hijo puede cruzar el borde
      //     inferior real de la hoja. Eso es lo que efectivamente se cortaria al imprimir.
      var restoMarginal = 4;
      var desbordes = sheets.reduce(function (acc, sheet) {
        var b = sheet.querySelector('.page__body');
        if (!b) return acc;
        var bad = b.scrollHeight > b.clientHeight + restoMarginal;
        var limit = b.getBoundingClientRect().bottom;
        for (var i = 0; i < b.children.length && !bad; i++) {
          if (b.children[i].getBoundingClientRect().bottom > limit + 1) bad = true;
        }
        return acc + (bad ? 1 : 0);
      }, 0);

      document.body.dataset.hojas = String(total);
      document.body.dataset.desbordes = String(desbordes);

      // ?debug=1 escribe la geometría real en el título, para leerla con --dump-dom.
      if (params.get('debug') === '1') {
        document.title = 'DBG ' + sheets.map(function (s, i) {
          var b = s.querySelector('.page__body');
          if (!b) return (i + 1) + '=portada';
          var maxChild = 0;
          for (var k = 0; k < b.children.length; k++) {
            maxChild = Math.max(maxChild, b.children[k].getBoundingClientRect().bottom);
          }
          return (i + 1) + ': scrollH=' + b.scrollHeight + ' cliH=' + b.clientHeight +
            ' maxChildBot=' + Math.round(maxChild) +
            ' bodyBot=' + Math.round(b.getBoundingClientRect().bottom) +
            ' sheetBot=' + Math.round(s.getBoundingClientRect().bottom);
        }).join(' || ');
      }

      console.log('[print] ' + JSON.stringify({
        cliente: m.nombre, hojas: total, secciones: startOf,
        total: t.total, desbordes: desbordes
      }));
    } catch (err) {
      banner(String((err && err.message) || err));
      console.error('[print] FALLO', err);
    }
  }

  // ---------------- Arranque ----------------

  function run() {
    if (!cfg) {
      banner('No llegó la configuración del cliente (window.CLIENT_CONFIG).');
      return;
    }
    cfg.author = cfg.author || { nombre: 'Lisandro Cacciatore', email: 'lisandro@ejemplo.com' };
    // Sin las fuentes cargadas las alturas medidas no son las definitivas y las
    // tarjetas se reparten mal entre hojas.
    var go = function () { buildDocument(); };
    if (document.fonts && document.fonts.ready && document.fonts.ready.then) {
      document.fonts.ready.then(go).catch(go);
    } else {
      go();
    }
    // El diálogo de impresión NO se abre solo: lo dispara el botón de la barra.
    // Con ?auto=1 se abre automáticamente (como hacía el original).
    if (params.get('auto') === '1') {
      setTimeout(function () {
        requestAnimationFrame(function () { requestAnimationFrame(function () { window.print(); }); });
      }, 400);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
