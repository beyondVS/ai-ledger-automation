<template>
  <div class="chart-container" style="position: relative; height: 300px; width: 100%;">
    <Bar :data="chartData" :options="options" />
  </div>
</template>

<script>
import { Bar } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale);

export default {
  name: 'BarChart',
  components: { Bar },
  props: {
    chartData: {
      type: Object,
      required: true
    },
    chartOptions: {
      type: Object,
      default: () => ({})
    }
  },
  computed: {
    options() {
      return {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#9CA3AF', // slate-400
              font: {
                family: 'Outfit, sans-serif'
              }
            }
          },
          y: {
            grid: {
              color: 'rgba(75, 85, 99, 0.2)' // slate-600 with opacity
            },
            ticks: {
              color: '#9CA3AF',
              font: {
                family: 'Outfit, sans-serif'
              },
              callback: function(value) {
                return (value / 10000).toLocaleString() + '만';
              }
            }
          }
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            padding: 12,
            backgroundColor: '#1F2937', // gray-800
            titleColor: '#F3F4F6', // gray-100
            bodyColor: '#F3F4F6',
            bodyFont: {
              family: 'Outfit, sans-serif'
            },
            callbacks: {
              label: function(context) {
                let label = context.dataset.label || '';
                if (label) {
                  label += ': ';
                }
                if (context.parsed.y !== undefined) {
                  label += new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW' }).format(context.parsed.y);
                }
                return label;
              }
            }
          }
        },
        ...this.chartOptions
      };
    }
  }
};
</script>
