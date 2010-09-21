var requests = {};

function showTooltip(x, y, contents) {
  $('<div id="tooltip">' + contents + '</div>').css( {
    position: 'absolute',
    display: 'none',
    top: y + 5,
    left: x + 5,
    border: '1px solid #fdd',
    padding: '2px',
    'background-color': '#fee',
    opacity: 0.80
  }).appendTo("body").fadeIn(200);
}

function millis(date) {
  return new Date(date.replace(/-/g, '/')).getTime();
}

function chart(element, data, limit, choices) {
  data = $.csv()(data);
  data = $.transpose(data);
  var dates = data.shift();
  dates.shift();   // remove "date" label
  var color = 0;
  var datasets = {};
  for (var i=0; i < data.length; ++i) {
    var label = data[i].shift();
    if (label in choices) {
      data[i].pop();   // remove last, undefined element
      var values = [];
      for (var n=0; n < data[i].length; ++n) {
        values.push([millis(dates[n]), parseFloat(data[i][n])]);
      }
      datasets[label] = { label: label, data: values, color: color };
      color++;
    }
    if (label.match(/length$/)) {
      var id = element[0].parentNode.id;
      if (!(id in requests)) {
        requests[id] = {};
      }
      requests[id][label] = data[i];
    };
    if (label == "7d80") {
      if (parseInt(data[i][data[i].length - 1], 10) > limit) {
        element.parent().addClass("slow");
      }
    };
  };
  var options = {
    xaxis: { mode: "time", timeformat: "%b/%d" },
    yaxis: { tickFormatter: function(val, axis) { return val + 'ms' } },
    grid: { hoverable: true, markings: [{ color: '#fcc', yaxis: { from: limit }}] },
    series: { lines: { show: true }, points: { show: true } },
  };
  function plot() {
    var series = [];
    $('#choices').find('input:checked').each(function () {
      series.push(datasets[$(this).attr('name')]);
    });
    $.plot(element, series, options);
  }
  plot();
  $('#choices').find('input').click(plot);
};

function histogram(element, data, limit) {
  data = $.csv()(data);
  data = $.transpose(data);
  var dates = data.shift();
  var series = [];
  var values = [];
  for (var i=0; i < data.length; ++i) {
    var label = data[i].shift();
    if (label.match(/^7d[0-9]+0$/)) {
      data[i].pop();   // remove last, undefined element
      var current = parseFloat(data[i].pop());
      values.push([current, parseFloat(label.replace(/^7d/, ''))]);
    };
  };
  values.sort(function (a, b) {
    return a[1] - b[1];
  });
  var p80 = values[values.length - 3][0];
  var p100 = values[values.length - 1][0];
  if (p100 < limit) {
    values.push([limit, 200]);  // fill the graph up to the limit
  }
  series.push({ label: 'max: ' + p100, data: values });
  $.plot(element, series, {
    grid: { markings: [
      { color: '#fcc', xaxis: { from: limit } },
      { color: '#0f0', xaxis: { from: p80, to: p80 } },
    ] },
    xaxis: {
      max: Math.max(limit * 1.05, p80 * 1.05),
      tickFormatter: function(val, axis) { return val + 'ms' },
    },
    yaxis: {
      max: 100,
      tickFormatter: function(val, axis) { return val + '%' },
    },
    series: { lines: { show: true, fill: true } },
    legend: { position: 'se' },
  });
};

function plot(element, url, limit, choices) {
  $.get(url, function(data) {
    limit = parseInt(limit, 10);
    chart(element.find('.chart'), data, limit, choices);
    histogram(element.find('.histogram'), data, limit);
    var previousPoint = null;
    element.find('.chart').bind("plothover", function (event, pos, item) {
      if (item) {
        if (previousPoint != item.datapoint) {
            previousPoint = item.datapoint;
          $("#tooltip").remove();
          var label = item.series.label.substr(0, 2) + 'length';
          var length = requests[this.parentNode.id][label][item.dataIndex];
          showTooltip(item.pageX, item.pageY, length + " request(s)");
        }
      } else {
          $("#tooltip").remove();
          previousPoint = null;
      }
    });
  });
};

function plotall(url) {
  $.get(url, function(data) {
    var choices = {};
    $('#choices').find('input').each(function () {
      choices[$(this).attr('name')] = true;
    });
    var list = $.csv()(data);
    for (var i=1; i < list.length; ++i) {
        var item = {};
        for (var j=0; j < list[0].length; j++) {
            item[list[0][j]] = list[i][j];
        }
        if (item['section']) {
          html = '<div class="target" id="' + item['section'] + '">'
          html = html + '<h3>' + item['title'] + '</h3>'
          if (item['description']) {
            html = html + '<p>' + item['description'] + '</p>'
          }
          html = html + '<div class="chart"></div>'
          html = html + '<div class="histogram"></div>'
          html = html + '</div>'
          $('#stats').append(html);
          plot($('#stats #' + item['section']), item['section'] + '_stats.csv', item['limit'], choices);
        };
    };
  });
};

$(document).ready(function() {
  plotall('index.csv');
  $('#only-slow:checkbox').click(function(foo) {
    $('.target').not('.slow').toggleClass('hidden');
  });
  $('#show-charts:checkbox').click(function(foo) {
    $('.chart').toggleClass('hidden');
  });
  $('#show-histograms:checkbox').click(function(foo) {
    $('.histogram').toggleClass('hidden');
  });
});