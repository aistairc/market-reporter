function reset() {

  document.querySelectorAll('[name^="correctness"]').forEach(element => {
    element.checked = false;
  });

}

function draw(canvas, ric, data, minY, maxY) {

  let ctx = canvas.getContext('2d');
  let chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data['xs'],
      datasets: [{
        label: ric,
        borderColor: '#ff0039',
        backgroundColor: '#ff0039',
        lineTension: 0,
        fill: false,
        showLine: true,
        data: data['ys']
      }]
    },
    options: {
      tooltips: {
        callbacks: {
          title: (tooltipItem, data) => {
            const label = tooltipItem[0].xLabel.replace('GMT', 'Z');
            const m = moment(label, 'ddd, DD MMM YYYY HH:mm:ss Z');
            return m.tz('Asia/Tokyo').format('YYYY-MM-DD HH:mm') + ' JST';
          }
        }
      },
      scales: {
        xAxes: [{
          type: 'time',
          time: {
            displayFormats: {
              minute: 'HH:mm'
            }
          },
          distribution: 'series',
          bounds: 'data',
          ticks: {
            unit: 'minute',
            source: 'auto'
          }
        }],
        yAxes: [{
          ticks: {
            suggestedMin: minY,
            suggestedMax: maxY
          }
        }],
      },
      legend: {
        display: false
      },
      title: {
        text: data['title'],
        fontSize: 18,
        padding: 16,
        display: true
      },
      animation: {
        duration: 0
      },
      hover: {
        animationDuration: 0
      },
      responsiveAnimationDuration: 0
    }
  });
}


document.addEventListener('DOMContentLoaded', () => {

  let referrer = document.createElement('input');
  referrer.type = 'hidden';
  referrer.name = 'referrer';
  referrer.value = document.referrer;
  let form = document.getElementById('form');
  if (form != null) {
    form.appendChild(referrer);
  }

  const uri = window.location.href;
  const fragments = uri.split('/');
  const articleId = fragments[fragments.length - 1];

  let xhr = new XMLHttpRequest();
  const READY = 4;
  const OK = 200;

  xhr.onreadystatechange = () => {

    let tabIndex = document.getElementById('tab-index');
    let tabContent = document.getElementById('tab-content');

    if(xhr.readyState == READY && xhr.status == OK) {

      JSON.parse(xhr.responseText).forEach((response, i) => {

        const ric = response['ric'];

        let li = document.createElement('li');
        li.className = 'nav-item';
        let a = document.createElement('a');
        if (i == 0 && ric == '.N225') {
          a.className = 'nav-link active';
        }
        else {
          a.className = 'nav-link';
        }
        a.setAttribute('data-toggle', 'tab');
        a.href = '#tab-' + i.toString();
        a.textContent = ric + ' on the day';
        li.appendChild(a);
        tabIndex.appendChild(li);

        let liPrev = document.createElement('li');
        liPrev.className = 'nav-item';
        let aPrev = document.createElement('a');
        aPrev.className = 'nav-link';
        aPrev.setAttribute('data-toggle', 'tab');
        aPrev.href = '#tab-prev-' + i.toString();
        aPrev.textContent = ric + ' on the previous day';
        liPrev.appendChild(aPrev);
        tabIndex.appendChild(liPrev);

        const ys = response['chart']['ys'];
        let canvas = document.createElement('canvas');
        canvas.id = 'canvas-' + i.toString();

        const ysPrev = response['chart-prev']['ys'];
        let canvasPrev = document.createElement('canvas');
        canvasPrev.id = 'canvas-prev-' + i.toString();

        const minY = Math.min(Math.min(...ys.filter(Boolean).map(parseFloat)),
                              Math.min(...ysPrev.filter(Boolean).map(parseFloat)));
        const maxY = Math.max(Math.max(...ys.filter(Boolean).map(parseFloat)),
                              Math.max(...ysPrev.filter(Boolean).map(parseFloat)));
        const scale = maxY - minY;

        draw(canvas, ric, response['chart'], minY - 0.1 * scale, maxY + 0.1 * scale);
        draw(canvasPrev, ric, response['chart-prev'], minY - 0.1 * scale, maxY + 0.1 * scale);

        let tab = document.createElement('tab');
        tab.id = 'tab-' + i.toString();
        if (i == 0 && ric == '.N225') {
          tab.className = 'tab-pane fade show active';
        }
        else {
          tab.className = 'tab-pane fade';
        }

        let tabPrev = document.createElement('tab');
        tabPrev.id = 'tab-prev-' + i.toString();
        tabPrev.className = 'tab-pane fade';

        tab.appendChild(canvas);
        tabPrev.appendChild(canvasPrev);

        tabContent.appendChild(tab);
        tabContent.appendChild(tabPrev);

      });

      let liOthers = document.createElement('li');
      liOthers.className = 'nav-item';
      let aOthers = document.createElement('a');
      aOthers.className = 'nav-link';
      aOthers.setAttribute('data-toggle', 'tab');
      aOthers.href = '#tab-others'
      aOthers.textContent = 'Closing prices';
      liOthers.appendChild(aOthers);
      tabIndex.appendChild(liOthers);

    }
  };

  xhr.open('GET', '/data/' + articleId);
  xhr.send();

});
