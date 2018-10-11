"use strict";

async function chartClickedHandler(evt) {
  const chart = evt.target.chart;
  const element = chart.getElementsAtEvent(evt)[0];
  if (!element) return;

  const label = chart.data.labels[element._index];
  const ric = evt.target.id;
  const timestamp = Math.round(new Date(label).getTime() / 1000);
  const response = await fetch(`/predict/${ric}/${timestamp}`);
  const data = await response.json();

  const heading = document.querySelector('#heading');
  data.pop(); // take off "</s>" at the end
  heading.textContent = data.join('');
  const subheading = document.querySelector('#subheading');
  subheading.textContent = `${ric}, ${label}`;
}

async function datePickedHandler(formattedDate, date, inst) {
  if (!date) return;

  const timestamp = Math.round(date.getTime() / 1000);
  const response = await fetch(`/data_ts/${timestamp}`);
  const { start, end, data } = await response.json();

  Object.keys(data).forEach(ric => {
    const ricdata = data[ric];
    const ys = ricdata.ys.filter(Boolean);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const scale = maxY - minY;

    draw(start, end, ric, ricdata, minY - 0.1 * scale, maxY + 0.1 * scale);
  });
}

function draw(start, end, ric, data, minY, maxY) {
  const canvas = document.getElementById(ric);
  const ctx = canvas.getContext('2d');

  if (canvas.chart) canvas.chart.destroy();

  canvas.chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data['xs'].map(x => new Date(x * 1000)),
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
            const label = tooltipItem[0].xLabel;
            return moment(label).tz('Asia/Tokyo').format('YYYY-MM-DD HH:mm') + ' JST';
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
            min: moment(start * 1000),
            max: moment(end * 1000),
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
        text: `${ric} ${moment(start * 1000).format("YYYY-MM-DD")}`,
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
  $('#datepicker').datepicker({
    language: 'en',
    dateFormat: 'yyyy-mm-dd',
    minDate: minDate,
    maxDate: maxDate,
    onSelect: datePickedHandler,
  });

  $(document).on('click', 'canvas', chartClickedHandler);
});
