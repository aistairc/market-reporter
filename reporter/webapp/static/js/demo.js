let selectedDate;

let chart;

function datePickedHandler(formattedDate, date, inst) {
  selectedDate = date;
  getChart();
}

async function chartClickedHandler(evt) {
  const element = chart.getElementsAtEvent(evt)[0];
  if (!element) return;

  const label = chart.data.labels[element._index];
  const ric = document.querySelector('#tab-index a.active').textContent;
  const timestamp = Math.round(new Date(label).getTime() / 1000);
  const response = await fetch(`/predict/${ric}/${timestamp}`);
  const data = await response.json();

  const heading = document.querySelector('#heading');
  data.pop(); // take off </s>
  heading.textContent = data.join('');
  const subheading = document.querySelector('#subheading');
  subheading.textContent = `${ric}, ${label}`;
}

async function getChart() {
  if (!selectedDate) return;

  const ric = document.querySelector('#tab-index a.active').textContent;

  const timestamp = Math.round(selectedDate.getTime() / 1000);
  const response = await fetch(`/data_ts/${ric}/${timestamp}`);
  const data = await response.json();

  const ys = data.ys.filter(Boolean).map(parseFloat);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const scale = maxY - minY;

  draw(canvas, ric, data, minY - 0.1 * scale, maxY + 0.1 * scale);
}

function draw(canvas, ric, data, minY, maxY) {
  if (chart) chart.destroy();

  chart = new Chart(ctx, {
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
      responsive: false,
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
            },
            min: moment(data.start * 1000),
            max: moment(data.end * 1000),
          },
          distribution: 'series',
          bounds: 'data',
          ticks: {
            unit: 'minute',
            source: 'auto',
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

$(() => {
  canvas = document.querySelector('#chart');
  ctx = canvas.getContext('2d');

  $('#datepicker').datepicker({
    language: 'en',
    dateFormat: 'yyyy-mm-dd',
    minDate: minDate,
    maxDate: maxDate,
    onSelect: datePickedHandler,
  });

  $('#tab-index').on('shown.bs.tab', 'a', evt => getChart());

  $(canvas).on('click', chartClickedHandler);
});
